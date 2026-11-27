# 우리 동네 폭염 알리미

동네를 고르면 앞으로 4일(또는 지난 날짜)의 기온·체감온도를 보고 폭염·열대야 위험을 알려 주는 Streamlit 앱.

## 실행 방법 (PowerShell, 이 폴더에서)

```powershell
.\.venv\Scripts\streamlit.exe run app.py
```

브라우저에서 http://localhost:8501 이 열립니다. 끌 때는 PowerShell 창에서 Ctrl+C.

## 파일 구성

| 파일 | 하는 일 |
|---|---|
| `weather.py` | 인터넷에서 날씨를 받아 오고, 체감온도·폭염·열대야를 계산 (계산 담당) |
| `app.py` | 선택 상자, 그래프, 표, 지도를 그림 (화면 담당) |
| `shelters.py` | 무더위쉼터 자료(API 또는 `data\shelters.csv`)를 읽고 가까운 순으로 정렬 |
| `.streamlit\secrets.toml` | 인증키를 두는 비밀 파일 (GitHub에 올리지 않음) |
| `.venv\` | 이 앱만 쓰는 Python 패키지 상자 (가상환경) |

## 판정 기준 (기상청 방식)

- 체감온도: 기상청 여름철 체감온도 공식(기온 + 습도). 여름(5~9월)용 공식이라 겨울에는 기온보다 조금 높게 나올 수 있어요.
- 폭염주의보: 일 최고 체감온도 33℃ 이상이 2일 이상
- 폭염경보: 일 최고 체감온도 35℃ 이상이 2일 이상
- 열대야: 그날 18시 ~ 다음날 9시 최저기온 25℃ 이상

## 무더위쉼터 자료

- 재난안전데이터공유플랫폼(safetydata.go.kr) `행정안전부_무더위쉼터` API (`DSSP-IF-10942`)
- 인증키는 `.streamlit\secrets.toml`의 `SHELTER_API_KEY`에 넣어요.
- 전국 약 6만 2천 곳을 처음 한 번 받는 데 30초쯤 걸리고, `data\shelters_api.csv`에 저장해 하루 동안 다시 씁니다.
- 이 API는 국내(등록된) IP에서만 응답해서 해외 서버인 Streamlit Cloud에서는 `UNREGISTERED IP ERROR`가 나요.
  그래서 PC에서 `make_snapshot.py`로 만든 `data\shelters.csv`(저장본)를 GitHub에 같이 올리고, 클라우드 앱은 그 파일을 읽어요.
  쉼터 목록을 새로 고치려면 PC에서 `.\.venv\Scripts\python.exe make_snapshot.py` 실행 후 `data` 폴더를 다시 올리면 돼요.

## 다음 단계

- 자료 출처를 기상청 단기예보 API로 바꾸기
- 인터넷에 올려 휴대폰으로 보기 (Streamlit Community Cloud)
