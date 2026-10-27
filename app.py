import io
import pandas as pd
import plotly.express as px
import streamlit as st
from analysis import METRICS, demo_data, prepare, summarize
from reports import render_report
from surveys import render_surveys

st.set_page_config(page_title="BioBrain · 한국인 신체변화", page_icon="📊", layout="wide")
st.title("BioBrain | 한국인 생애주기 신체변화")
st.caption("성별 · 연령 · 조사 시기 · 출생세대로 탐색하는 신체치수 연구 대시보드")
with st.sidebar:
    st.header("자료 설정")
    mode = st.radio("데이터", ["실제 원자료 통합 분석", "실제 보고서 집계 (5차)", "가상 데이터 시연", "내 데이터 업로드"])
    st.caption("개인 식별정보를 제거한 개인별 원자료를 사용하세요. 집계표에는 표본수·가중치를 고려하는 별도 분석이 필요합니다.")

if mode == "실제 원자료 통합 분석":
    render_surveys()
    st.stop()
if mode == "실제 보고서 집계 (5차)":
    render_report()
    st.stop()
if mode == "가상 데이터 시연":
    raw = demo_data()
    st.warning("가상 데이터 시연 중 — 그래프와 수치는 연구 근거로 사용할 수 없습니다.")
else:
    uploads = st.sidebar.file_uploader("CSV / XLSX 파일 (여러 조사 통합 가능)", type=["csv", "xlsx"], accept_multiple_files=True)
    if not uploads:
        st.write("파일을 업로드하면 열 연결과 단위 확인 후 분석할 수 있습니다.")
        st.download_button("입력 양식 CSV", "year,age,sex,height,weight,waist\n2024,35,여성,162,57,73\n".encode("utf-8-sig"), "template.csv", "text/csv")
        st.stop()
    frames = []
    for upload in uploads:
        try:
            if upload.name.lower().endswith(".xlsx"):
                book = pd.ExcelFile(io.BytesIO(upload.getvalue()))
                sheet = st.sidebar.selectbox(f"{upload.name} 시트", book.sheet_names, key=upload.name)
                part = pd.read_excel(book, sheet_name=sheet)
            else:
                encoding = st.sidebar.selectbox(f"{upload.name} 인코딩", ["utf-8-sig", "cp949"], key=upload.name)
                part = pd.read_csv(io.BytesIO(upload.getvalue()), encoding=encoding)
            if part.columns.duplicated().any():
                st.error(f"{upload.name}: 중복 열 이름을 정리해 주세요.")
                st.stop()
            frames.append(part)
        except Exception as error:
            st.error(f"{upload.name} 읽기 실패: {error}")
            st.stop()
    raw = pd.concat(frames, ignore_index=True)
    st.caption("여러 파일은 같은 열 이름을 기준으로 합칩니다. 각 행에 조사연도·만 나이가 필요합니다.")

with st.expander("열 연결 · 단위 · 성별 코드 확인", expanded=mode != "가상 데이터 시연"):
    st.dataframe(raw.head(8), hide_index=True)
    names = {"year": "조사연도", "age": "만 나이", "sex": "성별", **METRICS}
    aliases = {"year": ["조사연도", "조사년도"], "age": ["나이", "연령", "만나이"], "sex": ["성별"], "height": ["키", "신장"], "weight": ["몸무게", "체중"], "waist": ["허리둘레"], "bmi": ["BMI"]}
    mapping = {}
    columns = [None] + list(raw.columns)
    layout = st.columns(4)
    for i, (key, label) in enumerate(names.items()):
        default = next((c for c in [key] + aliases[key] if c in raw.columns), None)
        mapping[key] = layout[i % 4].selectbox(label, columns, index=columns.index(default), format_func=lambda x: "선택 안 함" if x is None else str(x), key=key)
    if not all(mapping[k] for k in ["year", "age", "sex"]):
        st.warning("조사연도, 만 나이, 성별 열을 연결해 주세요.")
        st.stop()
    chosen = [c for c in mapping.values() if c]
    if len(chosen) != len(set(chosen)):
        st.error("각 항목에는 서로 다른 열을 연결하세요.")
        st.stop()
    units = {key: st.selectbox(f"{names[key]} 원자료 단위", ["cm", "mm"], key=f"unit_{key}") for key in ["height", "waist"] if mapping[key]}
    sex_values = {}
    for value in sorted(raw[mapping["sex"]].dropna().astype(str).str.strip().unique()):
        options = ["미분류", "남성", "여성"]
        guessed = "남성" if value in ["남성", "남", "M", "Male"] else "여성" if value in ["여성", "여", "F", "Female"] else "미분류"
        sex_values[value] = st.selectbox(f"성별 원자료 값 ‘{value}’", options, index=options.index(guessed), key=f"sex_{value}")

data, quality, dropped = prepare(raw, mapping, sex_values, units)
if data.empty:
    st.error("유효한 연도·나이 행이 없습니다. 연도는 1979–2100, 만 나이는 0–110의 정수여야 합니다.")
    st.stop()
with st.sidebar:
    st.header("비교 조건")
    sexes = st.multiselect("성별", sorted(data.sex.unique()), default=sorted(data.sex.unique()))
    years = st.multiselect("조사연도", sorted(data.year.astype(int).unique()), default=sorted(data.year.astype(int).unique()))
    ages = st.slider("만 나이 범위", 0, 110, (int(data.age.min()), int(data.age.max())))
    available = [k for k in METRICS if data[k].notna().any()]
    if not available:
        st.error("신체치수 열을 하나 이상 연결하세요.")
        st.stop()
    metric = st.selectbox("분석 치수", available, format_func=METRICS.get)
    min_n = st.number_input("그래프 표시 최소 표본수", 1, 1000, 30)
filtered = data[data.sex.isin(sexes) & data.year.isin(years) & data.age.between(*ages)]
if filtered.empty:
    st.warning("선택 조건에 해당하는 데이터가 없습니다.")
    st.stop()
a, b, c = st.columns(3)
a.metric("선택 대상 행 수", f"{len(filtered):,}")
b.metric("선택 치수 유효 표본수", f"{filtered[metric].count():,}")
c.metric("조사 시기 수", filtered.year.nunique())
st.caption("원자료의 한 행을 한 관측으로 취급합니다. 중복 참여자·표본설계·측정법 변경은 별도로 검토해야 합니다. 평균은 비가중 기술통계입니다.")
tabs = st.tabs(["연령·성별", "조사 시기 변화", "생애주기·출생세대", "가설·의류 적용", "자료 품질·내보내기"])

def chart(groups, x, color, line_group=None):
    table = summarize(filtered, metric, groups)
    visible = table[table.n >= min_n].copy()
    if visible.empty:
        st.warning("표시 기준을 충족하는 집단이 없습니다. 최소 표본수를 조정하세요.")
    else:
        for key in [color, line_group]:
            if key:
                visible[key] = visible[key].astype(str)
        fig = px.line(visible, x=x, y="mean", color=color, line_dash=line_group, markers=True, error_y="ci95", hover_data=["n", "sd", "median"], labels={"mean": METRICS[metric], "age_group": "연령대 시작 (5세 구간)", "year": "조사연도", "sex": "성별", "cohort": "추정 출생연대"})
        st.plotly_chart(fig, use_container_width=True)
    st.caption("오차막대: 독립 단순무작위표본을 가정한 근사 95% 평균 신뢰구간 (n≥30). 복합표본설계를 반영하지 않습니다. 연결선은 관측된 집단 평균을 잇습니다.")
    st.dataframe(table.drop(columns="se"), hide_index=True)
    return table

with tabs[0]:
    st.subheader("성별·연령대별 신체치수")
    st.caption("선택한 조사연도를 합친 분포입니다. 연도별 표본 구성에 따라 평균이 달라질 수 있습니다.")
    chart(["age_group", "sex"], "age_group", "sex")
with tabs[1]:
    st.subheader("동일 연령대의 조사 시기별 비교")
    group = st.selectbox("비교할 5세 연령대 시작", sorted(filtered.age_group.unique()))
    saved = filtered
    filtered = filtered[filtered.age_group == group]
    chart(["year", "sex"], "year", "sex")
    filtered = saved
    st.caption("조사마다 대상 범위·측정 정의가 같은지 확인해야 합니다. 표본이 없는 연도는 추정하지 않습니다.")
with tabs[2]:
    st.subheader("연령별 곡선과 추정 출생세대 비교")
    st.warning("반복 횡단면의 연령별 곡선은 개인의 성장·노화 궤적이 아닙니다. 출생연도 ≈ 조사연도 − 만 나이이므로 생일 기준에 따라 1년 오차가 가능합니다.")
    view = st.radio("비교 기준", ["조사연도", "추정 출생연대"], horizontal=True)
    dim = "year" if view == "조사연도" else "cohort"
    chart(["age_group", "sex", dim], "age_group", dim, "sex")
    st.info("연령 = 조사시기 − 출생세대의 선형 관계 때문에 세 효과를 제약 없이 독립 추정할 수 없습니다. 이 화면은 탐색용이며 노화·세대의 인과적 분해 결과가 아닙니다.")
with tabs[3]:
    st.subheader("연구 가설과 확인 가능한 범위")
    st.dataframe(pd.DataFrame([
        ["H1 · 젊은 세대의 신장 증가", "같은 연령·성별에서 조사연도별 신장 비교", "성장기 영양·소득 자료, 표본설계, 측정 정의"],
        ["H2 · 중장년 비만 지표 증가", "같은 연령대의 체중·BMI·허리둘레 추이", "식이·활동·도시화 노출 자료와 교란변수"],
        ["H3 · 고령층의 세대 차이", "고령층 출생연대별 신체치수 분포", "근육량·자세 측정, 종단자료, 생존·선택편향 검토"],
        ["H4 · 신체 비율·사이즈 변화", "같은 연령·성별의 시기별 치수 비교", "팔다리·몸통 치수, 사이즈 규격, 착의·동작 평가"],
    ], columns=["가설", "현재 도구", "추가 필요 자료"]), hide_index=True)
    st.write("경제성장·영양정책·학교급식 확대와의 관련성은 개인의 성장기 노출과 외부 연도별 지표를 연결한 후 분석해야 합니다. 현재 데이터만으로 정책 효과나 원인을 결론내리지 않습니다.")
    st.subheader("의류 설계를 위한 선택 치수 분포")
    q = filtered.groupby("sex")[metric].quantile([.05, .5, .95]).unstack()
    q.columns = ["5백분위", "중앙값", "95백분위"]
    st.dataframe(q)
    st.write("치수 분포는 사이즈 범위 검토의 출발점입니다. 고령자 의류에는 자세·관절가동성, 보호복에는 동작 여유량·다변량 적합성, 압박의류에는 조직 특성·압력 실측이 추가로 필요합니다. 이 백분위만으로 제품 사이즈나 압박 수준을 처방하지 않습니다.")
with tabs[4]:
    st.write(f"입력 {len(raw):,}행 · 연도/나이 오류로 제외 {dropped:,}행 · 성별 미분류 {(data.sex == '미분류').sum():,}행")
    st.dataframe(quality, hide_index=True)
    st.caption("범위 밖 측정값은 해당 치수에서만 결측 처리합니다. 범위는 넓은 입력 점검 기준이며 임상 정상범위가 아닙니다. BMI가 비어 있으면 체중(kg)/신장(m)²으로 계산합니다. 신장·체중 오류와 함께 계산된 BMI도 점검하세요.")
    output = summarize(filtered, metric, ["year", "age_group", "sex"])
    st.download_button("집단 통계 CSV 다운로드", output.to_csv(index=False).encode("utf-8-sig"), "biobrain_summary.csv", "text/csv")
    st.download_button("분석 조건 다운로드", f"자료: {mode}\n치수: {metric}\n연도: {years}\n성별: {sexes}\n나이: {ages}\n단위: {units}\n열 연결: {mapping}\n성별 연결: {sex_values}\n집계: 비가중 평균, 5세 구간\n".encode("utf-8-sig"), "analysis_conditions.txt")
