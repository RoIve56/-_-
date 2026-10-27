# BioBrain — 한국인 생애주기 신체변화 대시보드

제공된 사이즈코리아 1·2·3·4·5·7·8차 공개용 Excel에서 정리한 84,121개 관측을 성별·연령·조사 시기·출생세대로 탐색하는 PC 브라우저용 소프트웨어입니다.

## 다운로드 및 Windows 실행

1. 이 저장소 상단의 **Code → Download ZIP**을 누릅니다.
2. 받은 ZIP을 폴더에 **완전히 압축 해제**합니다.
3. Windows에서는 **Python 3.12 64비트**를 설치한 뒤 폴더 안의 **run_windows.cmd**를 실행합니다.
4. 첫 실행에는 인터넷으로 패키지를 설치합니다. 준비되면 브라우저가 열립니다. 실행 창을 닫으면 서버가 종료됩니다.

Python 설치 시 ‘Add Python to PATH’를 선택하는 것을 권장합니다. 프로그램은 실제 측정자료를 기본으로 표시하며, 원본 Excel을 다시 업로드할 필요가 없습니다.

**[상세 사용 안내서](USER_GUIDE.md)**

## 주요 기능

- 성별·연령별 신체치수, 조사 기간별 비교와 공통 연령구간 표준화
- 출생세대별 기술통계, 신체비율·백분위·의류 치수 범위 커버율
- 외부 연도별 경제·식생활 지표 CSV 연결, 집단 통계·분석 조건 다운로드
- 모집단·측정방법 분리 및 원본 해시·열 연결·정제내역 확인

1979년은 개인별 연령이 없으며, 2024년은 휠체어 사용자·척수손상 조사로 일반 성인과 분리했습니다. 6차는 미제공입니다. 초기 체중 단위 및 조사 간 연령·측정 정의 대조는 남아 있습니다. 개인의 노화·출생세대·정책의 인과효과를 확정하지 않습니다. 자세한 해석 한계는 사용 안내서를 확인하세요.

## 개발·검증

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -r requirements.txt pytest==8.4.2
python -m pytest -q
python -m streamlit run app.py --server.address=127.0.0.1 --browser.gatherUsageStats=false
```

클라우드 Linux에서 통계·대시보드 테스트 9개 및 서버 응답을 검증했습니다. Windows 실행 스크립트는 실제 Windows에서는 미검증입니다. 원자료의 개인 ID·자유기술 사항은 통합 데이터에 포함하지 않았으며, 원본 Excel·PDF·DOCX는 이 저장소에 포함하지 않습니다.

## Windows 설치 오류 (NumPy / metadata-generation-failed)

최신 실행 파일은 Python **3.12 64비트**를 명시적으로 선택하고, `.venv-py312`라는 별도 환경을 만듭니다. 기존 `.venv`는 삭제하지 않습니다. pip를 업데이트한 뒤 사전 빌드된 wheel만 설치하여 NumPy 소스 빌드를 방지합니다.

기존 버전에서 설치가 실패했다면 GitHub에서 ZIP을 다시 받아 새 폴더에 압축을 풀어 실행하세요. [Python 3.12 64비트 공식 설치 파일](https://www.python.org/ftp/python/3.12.10/python-3.12.10-amd64.exe)을 설치할 때 Python launcher와 Add Python to PATH를 선택하세요. 다른 버전의 Python을 삭제할 필요는 없습니다.

Windows 패키지는 `requirements-windows.txt`를 사용합니다. Windows 실행 자체는 실제 PC에서 재확인이 필요합니다.
