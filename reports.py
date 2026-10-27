"""Published report aggregates, kept separate from individual observations."""
from pathlib import Path
import pandas as pd
import plotly.express as px
import streamlit as st
from analysis import METRICS


def render_report():
    data = pd.read_csv(Path(__file__).parent / "data/survey5_summary.csv")
    st.subheader("제5차 보고서 · 실제 집계 통계")
    st.caption("2003–2004 조사 · 2004년 11월 최종보고서 · 직접측정 · 출처: 산업자원부 기술표준원, 대한인간공학회·한국의류학회·한국표준과학연구원")
    st.info("보고서의 집단 통계입니다. 개인별 관측으로 변환하거나 다른 조사와 합산하지 않습니다. 다른 조사 자료가 연결되기 전까지 조사 시기·출생세대 비교는 제공하지 않습니다.")
    with st.sidebar:
        metric = st.selectbox("보고서 측정 항목", ["height", "weight", "waist"], format_func=METRICS.get)
        sexes = st.multiselect("보고서 성별", ["남성", "여성"], default=["남성", "여성"])
        age_scope = st.radio("보고서 연령 범위", ["전체 (영아 포함)", "성인 (20세 이상)"])
    selected = data[(data.metric == metric) & data.sex.isin(sexes)].copy()
    if age_scope == "성인 (20세 이상)":
        selected = selected[selected.age_label.str.extract(r"^(\d+)")[0].astype(int).ge(20) & ~selected.age_label.str.contains("개월")]
    if selected.empty:
        st.warning("선택된 성별이 없습니다.")
        return
    order = selected.sort_values("age_order").age_label.drop_duplicates().tolist()
    fig = px.line(selected, x="age_label", y="mean", color="sex", markers=True, category_orders={"age_label": order}, hover_data=["n", "sd", "p5", "p50", "p95", "pdf_page"], labels={"age_label": "보고서 원래 연령구간", "mean": METRICS[metric], "sex": "성별"})
    st.plotly_chart(fig, use_container_width=True)
    st.caption("범주형 연령축입니다. 월령·단일연령·5세·10세·70세 이상 구간의 간격은 실제 시간 간격을 나타내지 않습니다. 선은 서로 다른 사람 집단의 평균을 연결하며 개인의 노화 경로가 아닙니다.")
    st.warning("보고서의 연령 구간은 그대로 보존했습니다. ‘0~3개월’ 같은 경계 정의 및 연령 산정법은 원문 조사설계 확인이 필요합니다. 집계 평균 신장과 평균 체중으로 평균 BMI를 계산하지 않습니다.")
    st.dataframe(selected[["sex", "age_label", "n", "mean", "sd", "p5", "p50", "p95", "unit", "pdf_page", "printed_page"]].rename(columns={"sex": "성별", "age_label": "연령구간", "n": "표본수", "mean": "평균", "sd": "표준편차", "pdf_page": "PDF 페이지", "printed_page": "책자 페이지"}), hide_index=True)
    st.download_button("선택한 실제 집계 통계 CSV", selected.to_csv(index=False).encode("utf-8-sig"), "survey5_report_summary.csv", "text/csv")
    with st.expander("자료 확인 현황과 출처"):
        st.write("5차_1.pdf PDF 113·230쪽(키), 143·260쪽(몸무게), 151·271쪽(허리둘레)에서 176개 집단-치수 행을 추출했습니다. 길이 평균·표준편차·백분위는 mm에서 cm로 변환했습니다. 남성 키 표는 원문 이미지와 대조했고, 전체 추출행은 숫자 개수·표본수·백분위 순서를 검사했습니다. 나머지 표의 전수 시각 대조는 남아 있습니다.")
        st.write("이 화면은 5차 보고서 집계표를 보존하는 별도 화면입니다. 이후 제공된 1·2·3·4·5·7·8차 Excel은 ‘실제 원자료 통합 분석’에서 비교할 수 있습니다. 보고서 집계표와 원자료 분석은 연령 산정·분류가 다를 수 있으므로 동일 결과라고 가정하지 않습니다. 6차 원자료는 미제공입니다.")
        st.write("추출한 표는 요약통계로 보존합니다. 조사 가중치·측정 정의·대상 모집단 비교가 끝나기 전까지 전국 대표 추정이나 인과 효과를 주장하지 않습니다.")
