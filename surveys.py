from pathlib import Path
import json
import pandas as pd
import plotly.express as px
import streamlit as st
from survey_analysis import MEASURES, group_stats, common_age_standardization, stable_cohorts

ROOT = Path(__file__).parent


@st.cache_data
def load_surveys():
    return pd.read_csv(ROOT / "data/surveys.csv.gz", low_memory=False), json.loads((ROOT / "data/survey_manifest.json").read_text())


def render_surveys():
    data, manifest = load_surveys()
    st.subheader("실제 원자료 · 조사 시기와 생애주기 탐색")
    st.caption("제공된 1·2·3·4·5·7·8차 공개용 Excel에서 직접 추출 · 6차 파일 미제공 · 기술통계")
    with st.sidebar:
        population = st.selectbox("모집단 (서로 합치지 않음)", data.population.drop_duplicates().tolist())
        pool = data[data.population == population]
        choices = pool.sort_values(["wave", "year_start"]).survey.drop_duplicates().tolist()
        surveys = st.multiselect("조사 차수·기간", choices, default=choices)
        sexes = st.multiselect("분석 성별", ["남성", "여성"], default=["남성", "여성"])
        metric = st.selectbox("분석 신체치수·비율", list(MEASURES), format_func=MEASURES.get)
        age_policy = st.selectbox("연령 처리 (5·7차 민감도 비교)", ["ISO나이 내림 우선", "원자료 나이 사용"])
        age_range = st.slider("분석 연령 범위", 0, 110, (20, 59))
        min_n = st.number_input("집단별 최소 유효 표본수", 1, 1000, 30)
    selected = pool[pool.survey.isin(surveys) & pool.sex.isin(sexes)].copy()
    if age_policy == "원자료 나이 사용":
        selected["age"] = selected.age_recorded.where(selected.age_recorded.between(0, 110) & (selected.age_recorded % 1 == 0))
    if selected.empty:
        st.warning("조사와 성별을 하나 이상 선택하세요.")
        return
    aged = selected[selected.age.between(*age_range)].copy()
    aged["age_group"] = (aged.age // 5 * 5).astype(int)
    order = [s for s in choices if s in surveys]
    n1, n2, n3 = st.columns(3)
    n1.metric("선택 조사 관측 수 (연령 제한 전)", f"{len(selected):,}")
    n2.metric("선택 연령의 관측 수", f"{len(aged):,}")
    n3.metric("선택 치수 유효 표본수", f"{aged[metric].count():,}")
    st.info(f"1979년 원자료에는 연령 열이 없어 연령·세대 분석에서 제외합니다. 현재 연령 처리: {age_policy}. ISO를 선택하면 5·7차 ISO나이를 내림하고, 나머지는 원자료 나이를 유지합니다. 만 나이와 동일한지 추가 확인이 필요합니다.")
    st.caption("길이는 mm→cm, 체중은 1–4차 /10→kg, 이후 kg를 적용했습니다. 초기 체중 단위는 제공 문서와 값 분포를 근거로 한 잠정 해석이며 원 보고서 단위표와의 대조가 남아 있습니다. 측정 정의·표본설계도 조사 간 완전한 동일성을 보장하지 않습니다.")
    tabs = st.tabs(["조사 시기 비교", "연령별 신체변화", "출생세대 탐색", "의류·사이즈 분포", "사회환경 관련성", "자료 품질·출처"])

    def show(table, x, color="sex", dash=None, category=None):
        if table.empty:
            st.warning("선택 조건에 유효한 집단이 없습니다.")
            return
        visible = table[table.n >= min_n].copy()
        if visible.empty:
            st.warning("최소 표본수를 충족하는 집단이 없습니다.")
        else:
            for field in [color, dash]:
                if field:
                    visible[field] = visible[field].astype(str)
            fig = px.line(visible, x=x, y="mean", color=color, line_dash=dash, markers=True, error_y="ci95" if "ci95" in visible else None, category_orders=category or {}, hover_data=["n"], labels={"mean": MEASURES[metric], "survey": "조사 차수·기간", "age_group": "5세 연령대 시작", "cohort": "추정 출생연대", "sex": "성별"})
            st.plotly_chart(fig, use_container_width=True)
        st.dataframe(table, hide_index=True)
        st.caption("선은 관찰 집단을 연결합니다. 미측정 기간을 추정하지 않습니다. 표본수가 적은 집단은 그래프에서 제외됩니다. 신뢰구간은 n≥30에서 단순 독립표본을 가정한 근사값이며 복합표본설계를 반영하지 않습니다.")

    with tabs[0]:
        approach = st.radio("비교 방식", ["동일 연령 범위의 관측 평균", "공통 5세 구간으로 표준화", "연령 제한 없는 전체 표본 (1979 포함)"])
        if approach.startswith("공통"):
            # Never silently drop an unsupported survey, e.g. 1979.
            result, support = common_age_standardization(aged, metric, surveys, min_n)
            st.caption("선택한 모든 조사에 유효 표본이 있는 공통 연령구간만 성별로 찾아 동일한 가중치를 부여합니다. 전국 인구 연령분포를 적용한 표준화가 아닙니다.")
            if result.empty:
                st.warning("모든 선택 조사에 공통으로 지원되는 연령구간이 없습니다. 연령 없는 1차를 선택 해제하거나 조사·연령·최소 표본수를 조정하세요.")
            else:
                st.dataframe(support, hide_index=True)
                show(result, "survey", category={"survey": order})
        else:
            base = selected if approach.startswith("연령 제한") else aged
            if approach.startswith("연령 제한"):
                st.warning("이 화면은 연령 필터를 적용하지 않습니다. 조사별 연령·성별·대상 구성이 달라 전체 평균 차이를 신체변화 효과로 해석할 수 없습니다. 특히 1979년 신장 결측률을 확인하세요.")
            show(group_stats(base, metric, ["survey", "sex"]), "survey", category={"survey": order})
        st.download_button("선택 연령의 집단 통계 CSV", group_stats(aged, metric, ["survey", "sex", "age_group"]).to_csv(index=False).encode("utf-8-sig"), "survey_age_summary.csv", "text/csv")
    with tabs[1]:
        show(group_stats(aged, metric, ["survey", "sex", "age_group"]), "age_group", "survey", "sex", {"survey": order})
        st.warning("각 연령대는 서로 다른 사람입니다. 연결된 곡선은 개인의 성장·노화 궤적이 아니며 선택한 연령 범위 밖은 표시하지 않습니다.")
    with tabs[2]:
        cohorts = stable_cohorts(aged)
        st.caption("출생연도 범위 = [조사 시작연도 − 나이 − 1, 조사 종료연도 − 나이]. 전체 범위가 하나의 10년 출생구간에 들어가는 관측만 배정합니다. 정확한 생년이 아니며 연령 산정법 차이의 영향이 남습니다.")
        st.write(f"출생연대 경계에 걸려 제외한 관측: {cohorts.cohort.isna().sum():,}건")
        cohort_view = st.radio("세대 탐색 방식", ["조사별 출생연대 비교", "출생연대별 연령 곡선"])
        if cohort_view == "조사별 출생연대 비교":
            show(group_stats(cohorts, metric, ["survey", "sex", "cohort"]), "cohort", "survey", "sex", {"survey": order})
        else:
            show(group_stats(cohorts, metric, ["cohort", "sex", "age_group"]), "age_group", "cohort", "sex")
            st.caption("선택한 조사를 합쳐 출생연대·성별·5세 구간별로 집계합니다. 동일인을 추적하지 않으며 시기효과·표본 구성·선택편향이 남습니다.")
        st.warning("연령·조사시기·출생세대는 선형 종속입니다. 이 화면은 같은 출생연대에 속하는 집단의 기술통계이며 세 효과를 독립 추정하거나 영양·정책의 원인 효과를 입증하지 않습니다.")
    with tabs[3]:
        st.write("연령·성별·조사별 5·50·95백분위는 분포 범위를 검토하는 출발점입니다. 치수 하나의 백분위가 다변량 의류 적합성을 보장하지 않습니다.")
        st.dataframe(group_stats(aged, metric, ["survey", "sex"]), hide_index=True)
        st.subheader("허리·엉덩이 치수 범위의 관측 커버율")
        col1, col2 = st.columns(2)
        waist_range = col1.slider("허리둘레 수용 범위 (cm)", 20, 200, (60, 95))
        hip_range = col2.slider("엉덩이둘레 수용 범위 (cm)", 20, 200, (80, 110))
        complete = aged.dropna(subset=["waist", "hip"]).copy()
        complete["covered"] = complete.waist.between(*waist_range) & complete.hip.between(*hip_range)
        coverage = complete.groupby(["survey", "sex"]).covered.agg(n="count", coverage="mean").reset_index()
        coverage["coverage_percent"] = coverage.pop("coverage") * 100
        st.dataframe(coverage, hide_index=True)
        st.caption(f"허리·엉덩이 중 하나라도 결측인 {len(aged)-len(complete):,}건은 커버율 분모에서 제외했습니다. 이는 실제 착의 적합률이 아닙니다. 고령자 의류에는 자세·동작, 보호복에는 여유량·안전 시험, 압박의류에는 압력 실측이 추가로 필요합니다.")
        st.caption("샅높이는 하지장 전체와 동일하지 않으며 팔길이를 위팔길이·소매길이로 대체하지 않았습니다. 항목명과 측정 정의를 출처 탭에서 확인하세요.")
    with tabs[4]:
        st.write("경제·식생활·정책과의 관계를 탐색하려면 검증된 연도별 외부 지표가 필요합니다. 첨부 분석 초안의 상관계수와 인과 해석은 이 앱의 검증 결과로 사용하지 않았습니다.")
        external = st.file_uploader("외부 연도별 지표 CSV: year,value,indicator,source", type="csv", key="macro_csv")
        st.download_button("외부 지표 입력 양식", b"year,value,indicator,source\n", "external_indicator_template.csv")
        if external is not None:
            try:
                ext = pd.read_csv(external)
                required = {"year", "value", "indicator", "source"}
                if not required.issubset(ext.columns):
                    raise ValueError("year,value,indicator,source 열이 모두 필요합니다.")
                ext["year"] = pd.to_numeric(ext.year, errors="coerce")
                ext["value"] = pd.to_numeric(ext.value, errors="coerce")
                ext = ext.dropna(subset=list(required))
                if ext.empty or not (ext.year % 1 == 0).all():
                    raise ValueError("유효한 정수 연도와 숫자 값이 필요합니다.")
                indicator = st.selectbox("외부 지표", ext.indicator.unique())
                ext = ext[ext.indicator == indicator]
                if ext.year.duplicated().any():
                    raise ValueError("동일 지표의 연도별 값은 하나여야 합니다. 출처별 중복을 먼저 정리하세요.")
                table = group_stats(aged, metric, ["survey", "sex"])
                periods = selected.groupby("survey")[["year_start", "year_end"]].first()
                table = table.merge(periods, on="survey")
                def annual_mean(row):
                    years = list(range(int(row.year_start), int(row.year_end) + 1))
                    subset = ext[ext.year.isin(years)]
                    return subset.value.mean() if len(subset) == len(years) else float("nan")
                table["external_value"] = table.apply(annual_mean, axis=1)
                st.caption("여러 해에 걸친 조사에는 해당 기간의 외부 연도별 값이 모두 있을 때만 산술평균을 연결합니다. 개인별 성장기 노출이 아닙니다. 표본 구성 차이는 조정하지 않았습니다.")
                st.dataframe(table, hide_index=True)
                visible = table.dropna(subset=["external_value", "mean"])
                visible = visible[visible.n >= min_n]
                if not visible.empty:
                    st.plotly_chart(px.scatter(visible, x="external_value", y="mean", color="sex", hover_data=["survey", "n"], labels={"external_value": str(indicator), "mean": MEASURES[metric]}), use_container_width=True)
                st.dataframe(ext[["year", "value", "source"]], hide_index=True)
            except Exception as error:
                st.error(f"외부 지표 읽기 실패: {error}")
        st.warning("소수 조사시점의 국가 집계 상관은 공통 시간추세·표본 구성에 영향을 받습니다. 인과검정·정책효과·개인 수준의 영양 효과로 해석하지 마세요. 이 화면은 가설 1–4의 확증 검정 결과를 제공하지 않습니다.")
    with tabs[5]:
        overview = data.groupby(["survey", "sex"], sort=False).agg(rows=("sex", "size"), age_n=("age", "count"), age_min=("age", "min"), age_max=("age", "max"), height_n=("height", "count"), weight_n=("weight", "count"), waist_n=("waist", "count")).reset_index()
        st.dataframe(overview, hide_index=True)
        st.write("아래 manifest에는 파일 SHA-256, 원래 시트·열 이름, 단위 변환, 제외된 3D 시트, 결측·범위 밖 값 수를 기록했습니다. 개인 ID·기타사항은 저장하지 않았습니다. 표본가중치·층화·집락을 반영하지 않으며 동일한 모집단 대표성을 보장하지 않습니다.")
        st.json(manifest)
        settings = {"population": population, "surveys": surveys, "sexes": sexes, "metric": metric, "age_range": age_range, "min_n": min_n, "weighting": "unweighted", "age_policy": age_policy, "manifest": manifest}
        st.download_button("출처·분석 조건 JSON", json.dumps(settings, ensure_ascii=False, indent=2).encode(), "analysis_provenance.json", "application/json")
