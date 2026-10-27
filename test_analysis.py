import pandas as pd
from analysis import prepare, summarize, demo_data


def test_units_missing_and_invalid():
    raw = pd.DataFrame({"year": [2024, 2024, None, 2024], "age": [30, 40, 20, 35.5], "sex": [1, 2, 1, 2], "height": [1700, 0, 1600, 1600], "weight": [68, 50, 50, 50]})
    data, quality, dropped = prepare(raw, {k: k for k in raw.columns}, {"1": "남성", "2": "여성"}, {"height": "mm"})
    assert dropped == 2
    assert data.iloc[0].height == 170
    assert abs(data.iloc[0].bmi - 68 / 1.7 ** 2) < 1e-8
    assert pd.isna(data.iloc[1].bmi)
    assert data.iloc[0].birth_year == 1994


def test_summary_counts_missing_and_ci():
    frame = pd.DataFrame({"sex": ["남성"] * 31, "height": list(range(30)) + [None]})
    stats = summarize(frame, "height", ["sex"])
    assert stats.iloc[0]["n"] == 30
    assert stats.iloc[0]["mean"] == 14.5
    assert stats.iloc[0].ci95 > 0
    assert pd.isna(summarize(frame.head(3), "height", ["sex"]).iloc[0].ci95)


def test_dashboard_demo():
    from streamlit.testing.v1 import AppTest
    app = AppTest.from_file("app.py").run(timeout=30)
    assert not app.exception
    app.sidebar.radio[0].set_value("가상 데이터 시연").run()
    assert len(app.tabs) == 5
    assert app.metric[0].value == "6,000"
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
    assert any("該当" in w.value or "해당" in w.value for w in app.warning)


def test_report_aggregates_and_view():
    from streamlit.testing.v1 import AppTest
    data = pd.read_csv("data/survey5_summary.csv")
    assert len(data) == 176
    assert not data.duplicated(["sex", "age_label", "metric"]).any()
    assert (data.n > 0).all()
    assert (data.p5 <= data.p50).all() and (data.p50 <= data.p95).all()
    cell = data[(data.sex == "남성") & (data.metric == "height") & (data.age_label == "20~24세")].iloc[0]
    assert cell["mean"] == 173.8 and cell.n == 344
    app = AppTest.from_file("app.py").run(timeout=30)
    assert not app.exception
    app.sidebar.radio[0].set_value("실제 보고서 집계 (5차)").run()
    app.sidebar.radio[1].set_value("성인 (20세 이상)").run()
    assert not app.exception
    app.sidebar.multiselect[0].set_value([]).run()
    assert not app.exception
