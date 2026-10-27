"""Normalize selected public Size Korea columns; never infer age from an ID.

Usage: python scripts/import_surveys.py /workspace/attachments --output data
Original identifiers, comments, dates of birth and other fields are not retained.
"""
import argparse
import hashlib
import json
import re
from pathlib import Path
import numpy as np
import openpyxl
import pandas as pd

FIELDS = {"height": ["키", "신장"], "weight": ["몸무게", "체중"], "waist": ["허리둘레"], "hip": ["엉덩이둘레"], "chest": ["가슴둘레"], "leg": ["샅높이"], "sitting": ["앉은키"], "arm": ["팔길이"], "bmi_source": ["BMI"]}
BOUNDS = {"height": (30, 250), "weight": (1, 350), "waist": (15, 250), "hip": (15, 250), "chest": (15, 250), "leg": (10, 150), "sitting": (15, 150), "arm": (5, 120), "bmi_source": (5, 100)}
SEX = {"남": "남성", "남자": "남성", "남성": "남성", "M": "남성", "여": "여성", "여자": "여성", "여성": "여성", "F": "여성"}


def clean_name(value):
    return re.sub(r"^(?:기타)?\d+\.\s*", "", str(value or "").strip())


def clean_measurements(frame):
    frame = frame.copy()
    audit = {}
    for field, bounds in BOUNDS.items():
        values = pd.to_numeric(frame[field], errors="coerce")
        bad = values.notna() & ~values.between(*bounds)
        audit[field] = {"out_of_bounds": int(bad.sum()), "missing_input": int(values.isna().sum())}
        frame[field] = values.mask(bad)
    # A consistent derived BMI is used across surveys, retaining supplied BMI separately.
    bmi = frame.weight / (frame.height / 100) ** 2
    frame["bmi"] = bmi.where(bmi.between(5, 100))
    for key, numerator, denominator, bounds in [("whr", "waist", "hip", (.3, 2)), ("leg_ratio", "leg", "height", (.2, .7)), ("sitting_ratio", "sitting", "height", (.3, .8))]:
        values = frame[numerator] / frame[denominator]
        frame[key] = values.where(values.between(*bounds))
    return frame, audit


def import_sheet(sheet, wave, filename):
    iterator = sheet.iter_rows(values_only=True)
    prefix = []
    header_index = None
    for number, row in enumerate(iterator, 1):
        prefix.append(row)
        if any(str(v).strip() == "성별" for v in row):
            header_index = number
            break
        if number >= 10:
            raise ValueError(f"Header not found: {sheet.title}")
    header = list(prefix[-1])
    names = [clean_name(v) for v in header]
    def index(aliases):
        return next((names.index(alias) for alias in aliases if alias in names), None)
    mapping = {key: index(aliases) for key, aliases in FIELDS.items()}
    sex_index, age_index, iso_index = index(["성별"]), index(["나이", "연령"]), index(["ISO나이"])
    rows = []
    excluded_rows = []
    for source_row, row in enumerate(iterator, header_index + 1):
        if not any(v is not None for v in row):
            continue
        def get(j):
            return row[j] if j is not None and j < len(row) else None
        record = {key: get(j) for key, j in mapping.items()}
        if get(sex_index) is None and get(age_index) is None and all(v is None for v in record.values()):
            excluded_rows.append(source_row)
            continue
        # Do not retain individual IDs; workbook row and source hash allow audit.
        record.update(sex=SEX.get(str(get(sex_index)).strip(), "미분류"), age_recorded=get(age_index), age_iso=get(iso_index), source_row=source_row)
        rows.append(record)
    frame = pd.DataFrame(rows)
    mass_scale = 10 if wave <= 4 else 1
    for field in FIELDS:
        frame[field] = pd.to_numeric(frame[field], errors="coerce") / (mass_scale if field == "weight" else 1 if field == "bmi_source" else 10)
    frame["age_recorded"] = pd.to_numeric(frame.age_recorded, errors="coerce")
    frame["age_iso"] = pd.to_numeric(frame.age_iso, errors="coerce")
    iso = frame.age_iso.where(frame.age_iso.between(0, 110))
    frame["age"] = np.floor(iso) if iso_index is not None else frame.age_recorded
    frame["age"] = frame.age.where(frame.age.between(0, 110) & (frame.age % 1 == 0))
    frame["age_basis"] = "ISO나이 내림" if iso_index is not None else "원자료 나이 (산정법 확인 필요)" if age_index is not None else "연령 없음"
    start, end = {1: (1979, 1979), 2: (1986, 1986), 3: (1992, 1992), 4: (1997, 1997), 5: (2003, 2004), 7: (2015, 2015), 8: (2020, 2021)}[wave]
    population = "일반"
    if wave == 8:
        if "3차년도" in sheet.title:
            start = end = 2022
            population = "고령자 별도조사"
        elif "4차년도" in sheet.title:
            start = end = 2023
            population = "아동청소년 (3D 참여자 직접측정)"
        elif "5차년도" in sheet.title:
            start = end = 2024
            population = "휠체어 사용자·척수손상"
    frame["wave"] = wave
    frame["period"] = str(start) if start == end else f"{start}–{end}"
    frame["year_start"], frame["year_end"] = start, end
    frame["population"] = population
    frame["survey"] = f"{wave}차 · {frame.period.iloc[0]} · {population}"
    frame["sheet"] = sheet.title
    frame["source"] = filename
    frame, audit = clean_measurements(frame)
    meta = {"file": filename, "sheet": sheet.title, "wave": wave, "rows": len(frame), "header_row": header_index, "population": population, "period": frame.period.iloc[0], "age_basis": frame.age_basis.iloc[0], "missing_age": int(frame.age.isna().sum()), "unmapped_sex": int((frame.sex == "미분류").sum()), "weight_divisor": mass_scale, "length_divisor": 10, "column_mapping": {key: {"column_1based": j + 1, "original": str(header[j])} if j is not None else None for key, j in mapping.items()}, "quality": audit}
    meta["non_observation_rows_excluded"] = excluded_rows
    return frame, meta


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--output", type=Path, default=Path("data"))
    args = parser.parse_args()
    frames, metadata, excluded = [], [], []
    files = sorted(args.input.rglob("*치수데이터*.xlsx"))
    seen = set()
    for path in files:
        match = re.match(r"([1-8])차", path.name)
        if not match:
            continue
        wave = int(match[1])
        if wave in seen:
            raise ValueError(f"Duplicate survey workbook: {wave}")
        seen.add(wave)
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
        for sheet in workbook:
            use = "3D" not in sheet.title and "3차원" not in sheet.title
            # For 2023 only take measured height/weight, not automatic geometry.
            child_direct = wave == 8 and "4차년도" in sheet.title and "직접측정 및 계산식" in sheet.title
            if not use and not child_direct:
                excluded.append({"file": path.name, "sheet": sheet.title, "reason": "3D 자동/별도 측정: 직접측정과 혼합하지 않음"})
                continue
            frame, meta = import_sheet(sheet, wave, path.name)
            meta["sha256"] = digest
            frames.append(frame)
            metadata.append(meta)
            print(meta["wave"], meta["sheet"], meta["rows"], flush=True)
        workbook.close()
    if seen != {1, 2, 3, 4, 5, 7, 8}:
        raise ValueError(f"Expected supplied surveys 1–5, 7–8; found {seen}")
    args.output.mkdir(parents=True, exist_ok=True)
    data = pd.concat(frames, ignore_index=True)
    data.to_csv(args.output / "surveys.csv.gz", index=False, compression={"method": "gzip", "mtime": 0})
    (args.output / "survey_manifest.json").write_text(json.dumps({"sources": metadata, "excluded_sheets": excluded, "notes": ["6차 미제공 (문서의 제외 지시를 사용자 요청으로 간주하지 않음)", "1차 연령 없음: 연령별·코호트 분석 제외", "1–4차 체중 /10: 제공 분석문서 및 값 분포 근거; 원 보고서 단위표 대조 미완료", "ISO나이 존재 시 내림; 기타 나이의 만 나이 여부 미확인", "2003–04 및 2020–21은 기간으로 보존, 개인별 조사일을 추정하지 않음", "자동측정과 직접측정 혼합 금지; 팔길이는 정확히 같은 원자료명만 사용, 대체항목 사용 안 함", "표본가중치·층화·집락 미반영; 모집단 대표 추론 불가"]}, ensure_ascii=False, indent=2))
    print("TOTAL", len(data), flush=True)


if __name__ == "__main__":
    main()
