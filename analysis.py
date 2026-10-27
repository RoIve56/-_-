"""Descriptive analysis for repeated cross-sectional anthropometry data."""
import numpy as np
import pandas as pd

METRICS = {"height": "신장 (cm)", "weight": "체중 (kg)", "waist": "허리둘레 (cm)", "bmi": "BMI (kg/m²)"}


def prepare(frame, mapping, sex_values, units):
    data = pd.DataFrame(index=frame.index)
    for key, column in mapping.items():
        if column:
            data[key] = frame[column] if key == "sex" else pd.to_numeric(frame[column], errors="coerce")
    data["sex"] = data["sex"].astype(str).str.strip().map(sex_values).fillna("미분류")
    for key in ("height", "waist"):
        if key in data and units.get(key) == "mm":
            data[key] = data[key] / 10
    for key in METRICS:
        if key not in data:
            data[key] = np.nan
    # Broad screening bounds are data-quality flags, not clinical reference ranges.
    bounds = {"age": (0, 110), "year": (1979, 2100), "height": (30, 250), "weight": (1, 350), "waist": (15, 250), "bmi": (5, 100)}
    issues = []
    for key, (low, high) in bounds.items():
        invalid = data[key].notna() & ~data[key].between(low, high)
        issues.append({"항목": key, "범위 밖 값": int(invalid.sum()), "결측/제외": int((data[key].isna() | invalid).sum())})
        data.loc[invalid, key] = np.nan
    calculated = data.weight / (data.height / 100) ** 2
    data["bmi"] = data.bmi.fillna(calculated.where(calculated.between(5, 100)))
    valid = data.age.notna() & data.year.notna() & (data.age % 1 == 0) & (data.year % 1 == 0)
    dropped = int((~valid).sum())
    data = data.loc[valid].copy()
    data["birth_year"] = data.year - data.age
    data["age_group"] = (data.age // 5 * 5).astype(int)
    data["cohort"] = (data.birth_year // 10 * 10).astype(int)
    return data, pd.DataFrame(issues), dropped


def summarize(data, metric, groups):
    result = data.groupby(groups, observed=True)[metric].agg(n="count", mean="mean", sd="std", median="median").reset_index()
    result["se"] = result.sd / np.sqrt(result.n)
    # Approximate normal CI; deliberately omit it for small groups.
    result["ci95"] = (1.96 * result.se).where(result.n >= 30)
    return result


def demo_data():
    rng = np.random.default_rng(1979)
    n = 6000
    age = rng.integers(7, 90, n)
    year = rng.choice([1979, 1986, 1992, 1997, 2004, 2010, 2015, 2020, 2024], n)
    sex = rng.choice(["남성", "여성"], n)
    height = np.where(sex == "남성", 169, 157) + np.minimum(age - 20, 0) * 2.4 - np.maximum(age - 55, 0) * .13 + (year - 1979) * .08 + rng.normal(0, 5, n)
    bmi = 21 + np.minimum(age, 60) * .035 + (year - 1979) * .025 + rng.normal(0, 2, n)
    return pd.DataFrame({"year": year, "age": age, "sex": sex, "height": height, "weight": bmi * (height / 100) ** 2, "waist": bmi * 2.1 + 25 + rng.normal(0, 4, n)})
