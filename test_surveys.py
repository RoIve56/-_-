from pathlib import Path
import numpy as np
import pandas as pd
from survey_analysis import common_age_standardization, stable_cohorts
from scripts.import_surveys import clean_measurements, FIELDS


def test_standardization_equal_weights_not_sample_composition():
    frame = pd.DataFrame([
        {"survey": survey, "sex": "남성", "age": age, "height": value}
        for survey, age, n, value in [("A", 20, 100, 160), ("A", 30, 2, 180), ("B", 20, 2, 160), ("B", 30, 100, 180)]
        for _ in range(n)
    ])
    result, support = common_age_standardization(frame, "height", ["A", "B"], 2)
    assert result["mean"].tolist() == [170, 170]
    assert support.iloc[0].weight_per_bin == .5
    missing, _ = common_age_standardization(frame, "height", ["A", "B", "C"], 2)
    assert missing.empty


def test_cohort_period_uncertainty():
    frame = pd.DataFrame({"age": [25, 30, np.nan], "year_start": [2003, 2020, 1979], "year_end": [2004, 2021, 1979]})
    result = stable_cohorts(frame)
    assert result.iloc[0].cohort == 1970
    assert pd.isna(result.iloc[1].cohort)  # 1989–1991 crosses the decade boundary.
    assert len(result) == 2


def test_invalid_height_not_used_for_derived_indices():
    frame = pd.DataFrame({key: [None, None] for key in FIELDS})
    frame["height"] = [0, 170]
    frame["weight"] = [68, 68]
    frame["waist"] = [80, 80]
    frame["hip"] = [0, 100]
    result, _ = clean_measurements(frame)
    assert pd.isna(result.iloc[0].bmi) and pd.isna(result.iloc[0].whr)
    assert abs(result.iloc[1].bmi - 68/1.7**2) < 1e-8
    assert result.iloc[1].whr == .8


def test_actual_sources_have_expected_support():
    import json
    data = pd.read_csv("data/surveys.csv.gz", low_memory=False)
    manifest = json.loads(Path("data/survey_manifest.json").read_text(encoding="utf-8"))
    assert set(data.wave) == {1, 2, 3, 4, 5, 7, 8}
    assert data[data.wave == 1].age.isna().all()
    assert data[data.population == "휠체어 사용자·척수손상"].height.isna().all()
    assert data[(data.wave == 8) & (data.population == "일반")].period.unique().tolist() == ["2020–2021"]
    assert len(data) == sum(source["rows"] for source in manifest["sources"])
    assert len(data) == 84121
    assert "ID" not in data.columns
    assert not data.duplicated(["source", "sheet", "source_row"]).any()


def test_dashboard_filters_standardization_and_population():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file("app.py").run(timeout=30)
    assert not app.exception
    assert len(app.tabs) == 6
    assert app.sidebar.selectbox[0].value == "일반"
    next(w for w in app.radio if w.label == "비교 방식").set_value("공통 5세 구간으로 표준화").run()
    assert not app.exception
    assert any("공통으로" in w.value for w in app.warning)
    choices = app.sidebar.multiselect[0].value
    app.sidebar.multiselect[0].set_value([s for s in choices if not s.startswith("1차")]).run()
    assert not app.exception
    app.sidebar.selectbox[0].set_value("고령자 별도조사").run()
    app.sidebar.slider[0].set_value((70, 84)).run()
    assert not app.exception
    assert app.metric[1].value == "1,014"
    app.sidebar.selectbox[0].set_value("휠체어 사용자·척수손상").run()
    assert not app.exception


def test_loading_under_windows_legacy_default_encoding(monkeypatch):
    from pathlib import Path
    from surveys import load_surveys
    original_open = Path.open

    def windows_open(self, mode="r", buffering=-1, encoding=None, errors=None, newline=None):
        if "b" not in mode and encoding is None:
            encoding = "cp1252"
        return original_open(self, mode, buffering, encoding, errors, newline)

    # Reproduce the screenshot's default codepage rather than relying on Linux UTF-8.
    monkeypatch.setattr(Path, "open", windows_open)
    load_surveys.clear()
    data, manifest = load_surveys()
    assert len(data) == 84121
    assert "6차 미제공" in manifest["notes"][0]
    load_surveys.clear()
