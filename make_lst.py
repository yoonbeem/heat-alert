r"""동네마다 '여름 한낮 지표면온도' 위성 지도를 미리 만들어 data/lst/ 에 저장하는 도구.

위성: Landsat 8·9 (미국 NASA·USGS). 열적외선 센서로 땅 표면이 내는 열을 재서
30m 칸마다 지표면온도(LST)를 계산한 자료(Collection 2 Level-2, ST_B10)를 써요.
- 기온(공기 온도)과 달리 '땅이 얼마나 달궈졌나'라서, 아스팔트·지붕은 50℃ 넘게, 숲·강은 훨씬 낮게 나와요.
- 위성은 한국 오전 11시쯤 지나가요. 그래서 '여름 한낮 오전 무렵'의 모습이에요.
- 구름 낀 칸은 빼고, 여러 해 여름(6~8월) 사진의 중앙값을 써서 한 장으로 만들어요.

Earth Engine은 PC의 climate 가상환경에 설치돼 있어서 그쪽 Python으로 실행해요 (heat_alert 폴더에서):
    ..\climate\.venv\Scripts\python.exe make_lst.py
클라우드 앱에서는 Earth Engine 로그인을 할 수 없어서, 이렇게 미리 만든 그림 파일을 같이 올립니다.
"""
import json
from pathlib import Path

import ee
import requests

from places import PLACES

PROJECT = "climate-2026"
YEARS = (2021, 2025)  # 2021~2025년 여름 (Landsat 9 발사 이후 포함)
HALF_KM = 7  # 동네 중심에서 위아래·좌우 7km (14km 네모)
VIS_MIN, VIS_MAX = 25, 50  # 색 범위(℃). 모든 동네를 같은 색 범위로 그려야 서로 비교할 수 있어요
PALETTE = ["313695", "4575b4", "74add1", "abd9e9", "e0f3f8", "ffffbf", "fee090", "fdae61", "f46d43", "d73027", "a50026"]
OUT = Path(__file__).parent / "data" / "lst"


def landsat_lst(region):
    def prep(img):
        qa = img.select("QA_PIXEL")
        clear = qa.bitwiseAnd(1 << 3).eq(0).And(qa.bitwiseAnd(1 << 4).eq(0))  # 구름·구름그림자 빼기
        lst = img.select("ST_B10").multiply(0.00341802).add(149.0).subtract(273.15)  # 켈빈 → ℃
        return lst.updateMask(clear).rename("LST")

    col = (
        ee.ImageCollection("LANDSAT/LC08/C02/T1_L2")
        .merge(ee.ImageCollection("LANDSAT/LC09/C02/T1_L2"))
        .filterBounds(region)
        .filter(ee.Filter.calendarRange(YEARS[0], YEARS[1], "year"))
        .filter(ee.Filter.calendarRange(6, 8, "month"))
        .filter(ee.Filter.lt("CLOUD_COVER", 70))
    )
    return col.map(prep).median().clip(region), col.size()


def main():
    ee.Initialize(project=PROJECT)
    OUT.mkdir(parents=True, exist_ok=True)
    index = {}
    for i, (name, (lat, lon)) in enumerate(PLACES.items()):
        dlat, dlon = HALF_KM / 111.0, HALF_KM / (111.0 * __import__("math").cos(__import__("math").radians(lat)))
        west, south, east, north = lon - dlon, lat - dlat, lon + dlon, lat + dlat
        region = ee.Geometry.Rectangle([west, south, east, north])
        lst, n = landsat_lst(region)

        stats = lst.reduceRegion(
            reducer=ee.Reducer.percentile([10, 50, 90]).combine(ee.Reducer.max(), sharedInputs=True),
            geometry=region, scale=90, maxPixels=1e8,
        ).getInfo()
        center = lst.reduceRegion(ee.Reducer.mean(), ee.Geometry.Point([lon, lat]).buffer(300), 30).getInfo()

        url = lst.getThumbURL({
            "region": region, "dimensions": 600, "format": "png",
            "min": VIS_MIN, "max": VIS_MAX, "palette": PALETTE,
        })
        png = OUT / f"lst_{i:02d}.png"
        png.write_bytes(requests.get(url, timeout=120).content)

        index[name] = {
            "file": png.name,
            "bounds": [west, south, east, north],
            "scenes": n.getInfo(),
            "p10": round(stats["LST_p10"], 1),
            "median": round(stats["LST_p50"], 1),
            "p90": round(stats["LST_p90"], 1),
            "max": round(stats["LST_max"], 1),
            "center": round(center["LST"], 1) if center.get("LST") is not None else None,
        }
        print(ascii(name), index[name])

    meta = {"years": YEARS, "vis": [VIS_MIN, VIS_MAX], "palette": PALETTE, "places": index}
    (OUT / "index.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1), encoding="utf-8")
    print("done", len(index))


if __name__ == "__main__":
    main()
