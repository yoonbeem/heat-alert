r"""우리 동네 폭염 알리미 — 화면 부분 (Streamlit).

실행: .\.venv\Scripts\streamlit run app.py
Streamlit은 이 파일을 위에서 아래로 한 번 실행해서 화면을 그리고,
사용자가 버튼이나 선택 상자를 바꿀 때마다 처음부터 다시 실행합니다.
화면 꾸미기(여름 느낌 색·카드)는 style.py에 모아 두었어요.
"""
from datetime import date
from pathlib import Path

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

import satellite
import shelters
import style
import weather

st.set_page_config(page_title="우리 동네 폭염 알리미", page_icon="🌞", layout="wide")
style.inject()

LEVEL = {  # 전체 알림 → (배지 글자, 색 이름, 행동 요령)
    "폭염경보": ("폭염경보", "danger", "낮 12시~5시 바깥 활동은 피하고, 물을 자주 마시고, 가까운 무더위쉼터를 이용하세요. 어르신과 아이를 한 번 더 살펴 주세요."),
    "폭염주의보": ("폭염주의보", "warn", "한낮 야외 활동을 줄이고, 갈증이 나기 전에 물을 마시고, 시원한 곳에서 자주 쉬세요."),
    "폭염 관심": ("폭염 관심", "watch", "더위가 시작돼요. 외출할 때 물과 모자, 양산을 챙기세요."),
    "폭염 걱정 없음": ("시원해요", "safe", "지금은 폭염 걱정이 없어요. 여름이 오면 이곳에서 우리 동네 더위를 미리 확인하세요."),
}
DAY_KIND = {"경보 수준": "danger", "주의보 수준": "warn", "관심": "watch", "안전": "safe"}
WEEKDAY = "월화수목금토일"


# ---------------- 자료 불러오기 (한 번 읽으면 기억해 두기) ----------------
@st.cache_data
def load_dongs():
    return pd.read_csv(Path(__file__).parent / "data" / "dongs.csv", dtype=str, encoding="utf-8-sig").astype({"위도": float, "경도": float})


@st.cache_data(ttl=1800)
def load_weather(lat, lon, start, end):
    return weather.fetch_hourly(lat, lon, start, end)


@st.cache_data(ttl=6 * 3600, show_spinner="전국 무더위쉼터 목록을 불러오는 중이에요...")
def load_all_shelters(api_key):
    return shelters.load_shelters(api_key)


@st.cache_data
def load_sat():
    return satellite.load_sgg_index(), satellite.load_dong_stats()


dongs = load_dongs()

# ---------------- 맨 위: 제목 배너 ----------------
style.hero()

# ---------------- 동네 고르기 (시도 → 시군구 → 읍면동) ----------------
with st.container(border=True):
    how = st.radio("위치를 어떻게 정할까요?", ["📍 동 이름으로 고르기", "✏️ 좌표 직접 입력"], horizontal=True,
                   label_visibility="collapsed")
    if how.startswith("📍"):
        c1, c2, c3, c4 = st.columns([1, 1, 1, 1.2])
        sidos = list(dict.fromkeys(dongs["시도"]))
        sido = c1.selectbox("시도", sidos, index=sidos.index("서울특별시") if "서울특별시" in sidos else 0)
        sub = dongs[dongs["시도"] == sido]
        sggs = list(dict.fromkeys(sub["시군구"]))
        sgg = c2.selectbox("시군구", sggs)
        sub = sub[sub["시군구"] == sgg]
        dong = c3.selectbox("읍면동", list(sub["읍면동"]))
        row = sub[sub["읍면동"] == dong].iloc[0]
        lat, lon, sgg_code, dong_code = row["위도"], row["경도"], row["시군구코드"], row["코드"]
        place = f"{sgg} {dong}" if sgg != sido else f"{sido} {dong}"
    else:
        c1, c4 = st.columns([3, 1.2])
        coords = c1.text_input("위도, 경도 (구글 지도에서 오른쪽 클릭하면 맨 위에 나와요)", "35.8714, 128.6014")
        try:
            lat, lon = (float(v) for v in coords.split(","))
        except ValueError:
            st.error("위도, 경도는 '35.87, 128.60'처럼 쉼표로 나눈 숫자 두 개로 적어 주세요.")
            st.stop()
        if not (33 <= lat <= 39 and 124 <= lon <= 132):
            st.warning("한국 밖 좌표 같아요. 위도와 경도 순서를 확인해 주세요.")
        # 가장 가까운 동을 찾아서 열지도·이름에 써요
        d2 = (dongs["위도"] - lat) ** 2 + ((dongs["경도"] - lon) * 0.8) ** 2
        row = dongs.loc[d2.idxmin()]
        sgg_code, dong_code = row["시군구코드"], row["코드"]
        place = f"{row['시군구']} {row['읍면동']} 근처"
    period = c4.selectbox("볼 기간", ["앞으로 4일 예보", "지난여름 (2025년 8월 첫 주)", "기간 직접 고르기"])

if period.startswith("앞으로"):
    start = end = None
elif period.startswith("지난여름"):
    start, end = date(2025, 8, 1), date(2025, 8, 7)
else:
    d1, d2_ = st.columns(2)
    start = d1.date_input("시작일", date(2025, 7, 20))
    end = d2_.date_input("종료일", date(2025, 7, 26))

# ---------------- 날씨 계산 ----------------
try:
    hourly = load_weather(lat, lon, start, end)
    daily = weather.daily_summary(hourly)
    if start is not None:
        daily = daily[(daily["날짜"] >= start) & (daily["날짜"] <= end)]
except Exception:
    # 날씨 서버가 잠깐 답이 없어도 지도·쉼터는 보여 주고, 날씨 부분만 안내해요
    hourly = daily = None

if daily is not None and len(daily):
    alert = weather.overall_alert(daily)
    badge, kind, tip = LEVEL[alert]
    # ---------------- 오늘의 폭염 카드 + 숫자 카드 ----------------
    left, right = st.columns([1.35, 1])
    with left:
        style.alert_card(place, badge, kind, tip, "예보" if start is None else f"{start:%m/%d}~{end:%m/%d}")
    with right:
        style.stat_cards([
            ("🌡️", "최고 체감온도", f"{daily['최고 체감온도'].max():.1f}℃"),
            ("☀️", "최고 기온", f"{daily['최고기온'].max():.1f}℃"),
            ("🌙", "열대야", f"{int(daily['열대야'].fillna(False).sum())}일"),
        ])
    # ---------------- 날짜별 카드 ----------------
    days = [
        (f"{r['날짜'].month}/{r['날짜'].day}({WEEKDAY[r['날짜'].weekday()]})", DAY_KIND[r["단계"]],
         r["단계"].replace(" 수준", ""), f"{r['최고 체감온도']:.0f}℃", r["열대야"] == True)
        for _, r in daily.head(7).iterrows()
    ]
    style.day_strip(days)
else:
    st.warning("☁️ 날씨 서버가 지금 답이 늦어요. 잠시 뒤 새로고침해 주세요. 아래 열지도와 무더위쉼터는 그대로 볼 수 있어요.")
    if st.button("🔄 날씨 다시 불러오기"):
        load_weather.clear()
        st.rerun()

# ---------------- 무더위쉼터 ----------------
try:
    all_shelters, source = load_all_shelters(shelters.get_api_key(st.secrets))
    near = shelters.nearest(all_shelters, lat, lon, n=10)
except shelters.NoShelterData as e:
    near, source = None, str(e)

# ---------------- 탭: 지도 / 쉼터 / 그래프 / 표 ----------------
tab_map, tab_sh, tab_chart, tab_table = st.tabs(["🛰️ 우리 동네 열지도", "❄️ 가까운 무더위쉼터", "📈 시간별 온도", "📋 날짜별 표"])

with tab_map:
    sgg_index, dong_stats = load_sat()
    overlay = satellite.overlay_for(sgg_index, sgg_code)
    vmin, vmax = (sgg_index["vis"] if sgg_index else (25, 50))
    palette = sgg_index["palette"] if sgg_index else ["313695", "ffffbf", "a50026"]
    components.html(satellite.map_html(lat, lon, near, overlay, vmin, vmax, palette), height=575)
    if dong_stats is not None and dong_code in dong_stats.index:
        s = dong_stats.loc[dong_code]
        fmt = lambda v: f"{v:.1f}℃" if pd.notna(v) else "-"
        style.stat_cards([
            ("🏠", "동 중심 (반경 300m)", fmt(s["중심"])),
            ("🔥", "뜨거운 곳 (주변 1km 상위 10%)", fmt(s["p90"])),
            ("🌳", "시원한 곳 (주변 1km 하위 10%)", fmt(s["p10"])),
        ], horizontal=True)
    y0, y1 = sgg_index["years"] if sgg_index else (2021, 2025)
    st.caption(
        f"Landsat 8·9 위성의 지표면온도(땅 표면 온도), {y0}–{y1}년 6–8월 구름 없는 사진의 중앙값이에요. "
        "위성이 오전 11시쯤 지나갈 때 잰 값이고, 공기 온도가 아니라 땅이 달궈진 정도라서 기온보다 훨씬 높게 나와요. "
        "빨간 곳은 아스팔트·지붕·공장이 많은 곳, 파란 곳은 숲·강·논이에요. 지도 안 슬라이더로 열지도 투명도를 바꿀 수 있어요. "
        "자료: NASA·USGS Landsat (Google Earth Engine으로 계산), 배경 영상: Esri World Imagery, 행정동 경계: vuski/admdongkor"
    )

with tab_sh:
    if near is None:
        st.info(source)
    else:
        st.dataframe(
            near.fillna("-")[["이름", "거리(km)", "주소", "평일운영", "야간개방", "주말개방", "에어컨", "이용가능인원"]],
            hide_index=True, use_container_width=True,
        )
        st.caption(f"쉼터 자료: {source}. 지도 탭의 ❄ 표시가 이 쉼터들이에요.")

with tab_chart:
    if hourly is None:
        st.info("날씨 자료를 아직 받지 못했어요.")
    else:
        chart = hourly.set_index("시각")[["기온", "체감온도"]]
        if start is not None:
            chart = chart[(chart.index.date >= start) & (chart.index.date <= end)]
        chart["주의보 기준(33℃)"] = weather.WATCH_C
        st.line_chart(chart, color=["#ffb347", "#ff5e57", "#16c1c8"])

with tab_table:
    if daily is None:
        st.info("날씨 자료를 아직 받지 못했어요.")
    else:
        table = daily.copy()
        table["열대야"] = table["열대야"].map({True: "예", False: "아니오"}).fillna("-")
        st.dataframe(table, hide_index=True, use_container_width=True)

st.caption("날씨: Open-Meteo (기상 모델·재분석). 체감온도와 폭염특보 기준은 기상청 방식을 따랐어요.")
