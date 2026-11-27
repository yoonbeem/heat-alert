"""날씨 자료를 받아 오고, 체감온도와 폭염·열대야를 판정하는 부분.

화면(app.py)과 계산(weather.py)을 나눠 두면, 나중에 자료 출처를
Open-Meteo에서 기상청 API로 바꿀 때 이 파일만 고치면 됩니다.
"""
import math
from datetime import date, timedelta

import pandas as pd
import requests

FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# 기상청 폭염특보 기준(2020년 개정): 일 최고 체감온도가 이틀 이상 이어질 때
WATCH_C = 33  # 폭염주의보
WARNING_C = 35  # 폭염경보
TROPICAL_NIGHT_C = 25  # 열대야: 밤(18시~다음날 9시) 최저기온 25℃ 이상


def fetch_hourly(lat: float, lon: float, start: date | None = None, end: date | None = None) -> pd.DataFrame:
    """시간별 기온(℃)과 상대습도(%)를 받아 표(DataFrame)로 돌려준다.

    start/end를 주지 않으면 앞으로 4일 예보, 주면 그 기간의 과거 관측(재분석) 자료.
    """
    params = {
        "latitude": lat,
        "longitude": lon,
        "hourly": "temperature_2m,relative_humidity_2m",
        "timezone": "Asia/Seoul",
    }
    if start is None:
        url = FORECAST_URL
        params["forecast_days"] = 4
    else:
        url = ARCHIVE_URL
        # 열대야는 다음날 아침 9시까지 봐야 하므로 하루 더 받는다
        params["start_date"] = start.isoformat()
        params["end_date"] = (end + timedelta(days=1)).isoformat()

    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    hourly = resp.json()["hourly"]
    df = pd.DataFrame(
        {
            "시각": pd.to_datetime(hourly["time"]),
            "기온": hourly["temperature_2m"],
            "습도": hourly["relative_humidity_2m"],
        }
    ).dropna()
    df["체감온도"] = [feels_like(t, rh) for t, rh in zip(df["기온"], df["습도"])]
    return df


def feels_like(ta: float, rh: float) -> float:
    """기상청 여름철 체감온도 공식 (기온 ta ℃, 상대습도 rh %).

    1단계: Stull(2011) 공식으로 습구온도 tw를 구한다 (습도가 높을수록 땀이 덜 마름).
    2단계: 기온과 습구온도를 섞어 사람이 느끼는 더위를 계산한다.
    """
    tw = (
        ta * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(ta + rh)
        - math.atan(rh - 1.67633)
        + 0.00391838 * rh**1.5 * math.atan(0.023101 * rh)
        - 4.686035
    )
    return round(-0.2442 + 0.55399 * tw + 0.45535 * ta - 0.0022 * tw**2 + 0.00278 * tw * ta + 3.0, 1)


def daily_summary(df: pd.DataFrame) -> pd.DataFrame:
    """시간별 표를 날짜별로 묶어 최고 체감온도, 밤 최저기온, 단계를 만든다."""
    df = df.copy()
    df["날짜"] = df["시각"].dt.date
    days = []
    for d, g in df.groupby("날짜"):
        night_start = pd.Timestamp(d) + pd.Timedelta(hours=18)
        night = df[(df["시각"] >= night_start) & (df["시각"] <= night_start + pd.Timedelta(hours=15))]
        # 다음날 아침 자료가 없으면(마지막 날) 열대야는 판정하지 않는다
        night_min = night["기온"].min() if len(night) >= 15 else None
        days.append(
            {
                "날짜": d,
                "최고기온": g["기온"].max(),
                "최고 체감온도": g["체감온도"].max(),
                "밤 최저기온": night_min,
            }
        )
    out = pd.DataFrame(days)
    out["단계"] = out["최고 체감온도"].apply(level_of)
    out["열대야"] = out["밤 최저기온"].apply(
        lambda v: None if v is None or pd.isna(v) else v >= TROPICAL_NIGHT_C
    )
    return out


def level_of(max_feels: float) -> str:
    if max_feels >= WARNING_C:
        return "경보 수준"
    if max_feels >= WATCH_C:
        return "주의보 수준"
    if max_feels >= 31:
        return "관심"
    return "안전"


def overall_alert(daily: pd.DataFrame) -> str:
    """기상청처럼 '이틀 이상 이어지는가'를 보고 전체 알림을 정한다."""
    feels = list(daily["최고 체감온도"])
    for limit, name in ((WARNING_C, "폭염경보"), (WATCH_C, "폭염주의보")):
        run = 0
        for v in feels:
            run = run + 1 if v >= limit else 0
            if run >= 2:
                return name
    if max(feels) >= 31:
        return "폭염 관심"
    return "폭염 걱정 없음"
