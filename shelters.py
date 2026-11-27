"""무더위쉼터 자료를 불러와서 '내 동네에서 가까운 순'으로 정리하는 부분.

자료는 두 군데에서 올 수 있어요.
1) 공공데이터포털 API: 인증키를 .streamlit/secrets.toml 에 적어 두면 사용
2) CSV 파일: data/shelters.csv 가 있으면 사용 (키 승인이 늦을 때 대신 쓰는 길)

어느 쪽이든 마지막에는 같은 모양의 표(이름, 주소, 위도, 경도, 이용가능인원)로 맞춥니다.
그래서 app.py는 자료가 어디서 왔는지 몰라도 됩니다.
"""
import math
import time
from pathlib import Path

import pandas as pd
import requests

CSV_PATH = Path(__file__).parent / "data" / "shelters.csv"

# 기관마다 열 이름이 조금씩 달라서, 흔히 쓰는 이름들을 우리 표의 이름으로 바꿔 준다.
COLUMN_ALIASES = {
    "이름": ["이름", "쉼터명칭", "쉼터명", "시설명", "RSTR_NM", "restNm"],
    "주소": ["주소", "도로명주소", "상세주소", "소재지도로명주소", "RN_DTL_ADRES", "DTL_ADRES"],
    "위도": ["위도", "LA", "lat", "LAT"],
    "경도": ["경도", "LO", "lon", "LOT", "LNG"],
    "이용가능인원": ["이용가능인원", "USE_PSBL_NMPR", "수용인원"],
    "평일운영": ["평일운영"],
    "야간개방": ["야간개방"],
    "주말개방": ["주말개방"],
    "에어컨": ["에어컨"],
}


class NoShelterData(Exception):
    """키도 CSV도 아직 없을 때."""


def get_api_key(secrets) -> str | None:
    """Streamlit secrets에서 키를 꺼낸다. 비어 있으면 None."""
    try:
        key = secrets.get("SHELTER_API_KEY", "")
    except Exception:  # secrets.toml 파일이 아예 없을 때
        return None
    return key.strip() or None


API_URL = "https://www.safetydata.go.kr/V2/api/DSSP-IF-10942"  # 재난안전데이터공유플랫폼 무더위쉼터
API_CACHE = Path(__file__).parent / "data" / "shelters_api.csv"
PAGE_SIZE = 1000


def fetch_from_api(api_key: str) -> pd.DataFrame:
    """재난안전데이터공유플랫폼(행정안전부_무더위쉼터) API에서 전국 쉼터를 받아 온다.

    전국에 6만 곳이 넘어서 한 번에 1000곳씩 여러 쪽(page)으로 나눠 받아요(30초쯤).
    자료는 하루에 한 번 갱신되므로, 받은 결과를 data/shelters_api.csv 에 저장해 두고
    하루 안에는 그 파일을 다시 씁니다. 매번 6만 곳을 새로 받으면 느리고 서버에도 부담이에요.
    """
    if API_CACHE.exists() and time.time() - API_CACHE.stat().st_mtime < 24 * 3600:
        return pd.read_csv(API_CACHE, encoding="utf-8-sig")

    rows, page = [], 1
    while True:
        resp = requests.get(
            API_URL,
            params={"serviceKey": api_key, "returnType": "json", "pageNo": page, "numOfRows": PAGE_SIZE},
            timeout=60,
        )
        resp.raise_for_status()
        data = resp.json()
        if data.get("header", {}).get("resultCode") != "00":
            raise NoShelterData(f"쉼터 API 오류: {data.get('header')}")
        body = data.get("body") or []
        rows.extend(body)
        if len(body) < PAGE_SIZE or len(rows) >= data.get("totalCount", 0):
            break
        page += 1

    raw = pd.DataFrame(rows)
    raw["야간개방"] = raw["CHCK_MATTER_NIGHT_OPN_AT"].map({"Y": "예", "N": "아니오"})
    raw["주말개방"] = raw["CHCK_MATTER_WKEND_HDAY_OPN_AT"].map({"Y": "예", "N": "아니오"})
    raw["에어컨"] = raw["COLR_HOLD_ARCNDTN"]
    raw["평일운영"] = [hours(a, b) for a, b in zip(raw["WKDAY_OPER_BEGIN_TIME"], raw["WKDAY_OPER_END_TIME"])]
    API_CACHE.parent.mkdir(exist_ok=True)
    raw.to_csv(API_CACHE, index=False, encoding="utf-8-sig")
    return raw


def hours(begin, end) -> str:
    """'0900', '1800' → '09:00~18:00'. 값이 없으면 '-'."""
    def fmt(v):
        v = str(v).split(".")[0].zfill(4) if pd.notna(v) and str(v).strip() else ""
        return f"{v[:2]}:{v[2:]}" if len(v) == 4 else ""
    b, e = fmt(begin), fmt(end)
    return f"{b}~{e}" if b and e else "-"


def load_csv(path: Path = CSV_PATH) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp949"):  # 공공데이터 CSV는 한글 윈도우 인코딩(cp949)인 경우가 많다
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError:
            continue
    raise NoShelterData(f"{path.name} 파일의 글자 인코딩을 읽지 못했어요.")


def standardize(raw: pd.DataFrame) -> pd.DataFrame:
    """열 이름을 통일하고, 위치가 없는 줄은 버린다."""
    out = pd.DataFrame()
    for ours, candidates in COLUMN_ALIASES.items():
        found = next((c for c in candidates if c in raw.columns), None)
        out[ours] = raw[found] if found else None
    out["위도"] = pd.to_numeric(out["위도"], errors="coerce")
    out["경도"] = pd.to_numeric(out["경도"], errors="coerce")
    return out.dropna(subset=["위도", "경도"])


def load_shelters(api_key: str | None) -> tuple[pd.DataFrame, str]:
    """쉼터 표와 '어디서 왔는지' 설명을 함께 돌려준다."""
    api_error = None
    if api_key:
        try:
            return standardize(fetch_from_api(api_key)), "재난안전데이터공유플랫폼 API (행정안전부_무더위쉼터)"
        except Exception as e:  # 인터넷 서버(해외)에서 막히는 경우 등: 앱 전체가 멈추지 않게 한다
            api_error = e
    if CSV_PATH.exists():
        date_file = CSV_PATH.parent / "shelters_date.txt"
        when = date_file.read_text(encoding="utf-8").strip() if date_file.exists() else "날짜 모름"
        return standardize(load_csv()), f"행정안전부_무더위쉼터 (재난안전데이터공유플랫폼, {when} 기준 저장본)"
    if api_error is not None:
        raise NoShelterData(f"무더위쉼터 API에 연결하지 못했어요: {api_error}")
    raise NoShelterData("무더위쉼터 인증키(SHELTER_API_KEY)가 설정되지 않았어요.")


def distance_km(lat1, lon1, lat2, lon2) -> float:
    """두 지점 사이 거리(km). 지구를 공으로 보고 계산하는 하버사인 공식."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def nearest(shelters: pd.DataFrame, lat: float, lon: float, n: int = 10) -> pd.DataFrame:
    df = shelters.copy()
    df["거리(km)"] = [round(distance_km(lat, lon, a, b), 2) for a, b in zip(df["위도"], df["경도"])]
    return df.sort_values("거리(km)").head(n)
