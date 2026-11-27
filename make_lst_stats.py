r"""동(읍면동)마다 여름 한낮 지표면온도 숫자를 계산해 data/dong_lst.csv 로 저장하는 도구.

- 중심: 동 중심점 반경 300m 평균
- 뜨거운 곳 / 시원한 곳: 동 중심 반경 1km 안 칸들의 상위 10% / 하위 10%
계산 방식(위성, 기간, 구름 빼기)은 make_lst.py와 같아요.

사용법: ..\climate\.venv\Scripts\python.exe make_lst_stats.py
"""
import csv
from pathlib import Path

import ee

from make_lst import PROJECT, landsat_lst

HERE = Path(__file__).parent
CHUNK = 300


def main():
    ee.Initialize(project=PROJECT)
    with open(HERE / "data" / "dongs.csv", encoding="utf-8-sig") as fp:
        dongs = list(csv.DictReader(fp))
    korea = ee.Geometry.Rectangle([124.5, 33.0, 131.0, 38.7])
    lst, _ = landsat_lst(korea)
    out = []
    for i in range(0, len(dongs), CHUNK):
        part = dongs[i:i + CHUNK]
        pts = [ee.Feature(ee.Geometry.Point([float(d["경도"]), float(d["위도"])]), {"code": d["코드"]}) for d in part]
        fc = ee.FeatureCollection(pts)
        center = lst.reduceRegions(fc.map(lambda f: f.buffer(300)), ee.Reducer.mean(), scale=30).getInfo()
        around = lst.reduceRegions(fc.map(lambda f: f.buffer(1000)), ee.Reducer.percentile([10, 90]), scale=30).getInfo()
        c = {f["properties"]["code"]: f["properties"].get("mean") for f in center["features"]}
        for f in around["features"]:
            p = f["properties"]
            r = lambda v: round(v, 1) if v is not None else ""
            out.append({"코드": p["code"], "중심": r(c.get(p["code"])), "p10": r(p.get("p10")), "p90": r(p.get("p90"))})
        print(f"{min(i + CHUNK, len(dongs))}/{len(dongs)}", flush=True)
    with open(HERE / "data" / "dong_lst.csv", "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=["코드", "중심", "p10", "p90"])
        w.writeheader()
        w.writerows(out)
    print("done", len(out))


if __name__ == "__main__":
    main()
