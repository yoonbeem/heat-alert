r"""우리 동네 폭염 알리미 — 화면 부분 (Streamlit).

실행: .\.venv\Scripts\streamlit run app.py
Streamlit은 이 파일을 위에서 아래로 한 번 실행해서 화면을 그리고,
사용자가 버튼이나 선택 상자를 바꿀 때마다 처음부터 다시 실행합니다.
"""
from datetime import date

import pandas as pd
import streamlit as st

import shelters
import weather

# 동네 목록: 이름 → (위도, 경도). 원하는 동네를 이 목록에 한 줄 추가하면 됩니다.
PLACES = {
    "서울 (종로)": (37.5730, 126.9794),
    "부산": (35.1796, 129.0756),
    "대구": (35.8714, 128.6014),
    "인천": (37.4563, 126.7052),
    "광주": (35.1595, 126.8526),
    "대전": (36.3504, 127.3845),
    "울산": (35.5384, 129.3114),
    "세종": (36.4800, 127.2890),
    "수원": (37.2636, 127.0286),
    "춘천": (37.8813, 127.7298),
    "강릉": (37.7519, 128.8761),
    "청주": (36.6424, 127.4890),
    "전주": (35.8242, 127.1480),
    "포항": (36.0190, 129.3435),
    "안동": (36.5684, 128.7294),
    "의성": (36.3527, 128.6970),
    "창원": (35.2280, 128.6811),
    "제주": (33.4996, 126.5312),
}

LEVEL_COLOR = {"폭염경보": "🔴", "폭염주의보": "🟠", "폭염 관심": "🟡", "폭염 걱정 없음": "🟢"}
TIPS = {
    "폭염경보": "낮 12시~5시 바깥 활동은 피하고, 물을 자주 마시고, 가까운 무더위쉼터를 이용하세요. 어르신과 아이를 한 번 더 살펴 주세요.",
    "폭염주의보": "한낮 야외 활동을 줄이고, 갈증이 나기 전에 물을 마시고, 시원한 곳에서 자주 쉬세요.",
    "폭염 관심": "더위가 시작돼요. 외출할 때 물과 모자를 챙기세요.",
    "폭염 걱정 없음": "지금은 폭염 걱정이 없어요.",
}

st.set_page_config(page_title="우리 동네 폭염 알리미", page_icon="🌡️")
st.title("🌡️ 우리 동네 폭염 알리미")

# ---- 왼쪽 옆 막대: 사용자가 고르는 곳 ----
with st.sidebar:
    place = st.selectbox("동네", list(PLACES) + ["직접 입력"])
    if place == "직접 입력":
        # 구글 지도에서 원하는 곳을 오른쪽 클릭하면 맨 위에 '위도, 경도' 숫자가 나와요
        st.caption("구글 지도에서 우리 집 근처를 오른쪽 클릭 → 맨 위 숫자를 복사해 붙여 넣으세요.")
        coords = st.text_input("위도, 경도", "35.8714, 128.6014")
        place_name = st.text_input("이름", "우리 동네")
    mode = st.radio("볼 기간", ["앞으로 4일 예보", "지난 날짜 다시 보기"])
    if mode == "지난 날짜 다시 보기":
        start = st.date_input("시작일", date(2025, 8, 1))
        end = st.date_input("종료일", date(2025, 8, 7))
    else:
        start = end = None
    st.caption("자료: Open-Meteo (기상 모델·재분석). 체감온도와 특보 기준은 기상청 방식을 따랐어요.")

if place == "직접 입력":
    try:
        lat, lon = (float(v) for v in coords.split(","))
    except ValueError:
        st.error("위도, 경도는 '35.87, 128.60'처럼 쉼표로 나눈 숫자 두 개로 적어 주세요.")
        st.stop()
    if not (33 <= lat <= 39 and 124 <= lon <= 132):
        st.warning("한국 밖 좌표 같아요. 위도와 경도 순서를 확인해 주세요.")
    place = place_name
else:
    lat, lon = PLACES[place]


# 같은 동네·기간을 다시 볼 때 인터넷에서 또 받지 않도록 30분 동안 기억해 둔다
@st.cache_data(ttl=1800)
def load(lat, lon, start, end):
    return weather.fetch_hourly(lat, lon, start, end)


try:
    hourly = load(lat, lon, start, end)
except Exception as e:
    st.error(f"날씨 자료를 받지 못했어요: {e}")
    st.stop()

daily = weather.daily_summary(hourly)
if start is not None:
    daily = daily[(daily["날짜"] >= start) & (daily["날짜"] <= end)]
alert = weather.overall_alert(daily)

# ---- 한눈에 보는 결과 ----
st.subheader(f"{LEVEL_COLOR[alert]} {place}: {alert}")
st.write(TIPS[alert])

c1, c2, c3 = st.columns(3)
c1.metric("가장 높은 체감온도", f"{daily['최고 체감온도'].max():.1f} ℃")
c2.metric("가장 높은 기온", f"{daily['최고기온'].max():.1f} ℃")
c3.metric("열대야", f"{int(daily['열대야'].fillna(False).sum())} 일")

# ---- 날짜별 카드: 하루하루를 신호등 색으로 ----
DAY_ICON = {"경보 수준": "🔴", "주의보 수준": "🟠", "관심": "🟡", "안전": "🟢"}
WEEKDAY = "월화수목금토일"
cards = daily.head(7)  # 화면이 좁아지지 않게 최대 7일까지만 카드로
for col, (_, row) in zip(st.columns(len(cards)), cards.iterrows()):
    d = row["날짜"]
    night = "🌙 열대야" if row["열대야"] == True else ""
    col.markdown(
        f"**{d.month}/{d.day}({WEEKDAY[d.weekday()]})**  \n"
        f"{DAY_ICON[row['단계']]} {row['단계'].replace(' 수준', '')}  \n"
        f"체감 {row['최고 체감온도']:.0f}℃  \n{night}"
    )

# ---- 시간별 그래프 ----
st.markdown("#### 시간별 기온과 체감온도")
chart = hourly.set_index("시각")[["기온", "체감온도"]]
if start is not None:
    chart = chart[(chart.index.date >= start) & (chart.index.date <= end)]
chart["주의보 기준(33℃)"] = weather.WATCH_C
st.line_chart(chart)

# ---- 날짜별 표 ----
st.markdown("#### 날짜별 요약")
table = daily.copy()
table["열대야"] = table["열대야"].map({True: "예", False: "아니오"}).fillna("-")
st.dataframe(table, hide_index=True, use_container_width=True)

# ---- 지도: 내 동네(빨간 점) + 가까운 무더위쉼터(파란 점) ----
st.markdown("#### 가까운 무더위쉼터")
me = pd.DataFrame({"lat": [lat], "lon": [lon], "color": ["#e03131"], "size": [120]})
@st.cache_data(ttl=6 * 3600, show_spinner="전국 무더위쉼터 목록을 받는 중이에요 (처음 한 번은 30초쯤 걸려요)...")
def load_all_shelters(api_key):
    return shelters.load_shelters(api_key)


try:
    all_shelters, source = load_all_shelters(shelters.get_api_key(st.secrets))
    near = shelters.nearest(all_shelters, lat, lon, n=10)
    pins = pd.DataFrame(
        {"lat": near["위도"], "lon": near["경도"], "color": "#1c7ed6", "size": 60}
    )
    st.map(pd.concat([me, pins]), color="color", size="size", zoom=14)
    st.dataframe(
        near.fillna("-")[["이름", "거리(km)", "주소", "평일운영", "야간개방", "주말개방", "에어컨", "이용가능인원"]],
        hide_index=True,
        use_container_width=True,
    )
    st.caption(f"쉼터 자료: {source}")
except shelters.NoShelterData as e:
    st.map(me, color="color", size="size", zoom=10)
    st.info(str(e))
