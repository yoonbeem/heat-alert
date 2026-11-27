r"""전국 시군구마다 '여름 한낮 지표면온도' 위성 그림을 30m 칸으로 미리 만들어 data/lst_sgg/ 에 저장하는 도구.

동(읍면동)마다 그림을 따로 만들면 3,500장이 넘어서, 시군구(약 250곳)마다 한 장씩 만들고
앱에서는 고른 동이 속한 시군구 그림을 보여 줘요. 계산 방식은 make_lst.py와 같아요.

사용법 (heat_alert 폴더에서, Earth Engine이 설치된 climate 가상환경으로):
    ..\climate\.venv\Scripts\python.exe make_lst_sgg.py <행정동 geojson 경로> [시군구코드 ...]
이미 만든 시군구는 건너뛰어요. 중간에 끊겨도 다시 실행하면 이어서 만들어요.
"""
import io
import json
import math
import sys
import time
from pathlib import Path

import ee
import requests
from PIL import Image

from make_lst import PALETTE, PROJECT, RES_M, VIS_MAX, VIS_MIN, YEARS, landsat_lst

OUT = Path(__file__).parent / "data" / "lst_sgg"
PAD_KM = 0.5


def sgg_boxes(geojson_path):
    gj = json.loads(Path(geojson_path).read_text(encoding="utf-8"))
    boxes = {}
    for f in gj["features"]:
        code, name = f["properties"]["sgg"], f["properties"]["sggnm"] or f["properties"]["sidonm"]
        g = f["geometry"]
        polys = g["coordinates"] if g["type"] == "MultiPolygon" else [g["coordinates"]]
        xs = [p[0] for poly in polys for p in poly[0]]
        ys = [p[1] for poly in polys for p in poly[0]]
        b = boxes.setdefault(code, {"name": f"{f['properties']['sidonm']} {name}", "box": [999, 999, -999, -999]})
        b["box"] = [min(b["box"][0], min(xs)), min(b["box"][1], min(ys)), max(b["box"][2], max(xs)), max(b["box"][3], max(ys))]
    return boxes


def to_palette_png(png_bytes: bytes) -> bytes:
    """GEE가 준 RGBA 그림을 256색 팔레트 PNG로 바꿔 파일 크기를 줄인다 (색 11개 단계라 화질 차이 거의 없음)."""
    im = Image.open(io.BytesIO(png_bytes)).convert("RGBA")
    q = im.quantize(colors=255, method=Image.Quantize.FASTOCTREE)
    buf = io.BytesIO()
    q.save(buf, format="PNG", optimize=True, transparency=_transparent_index(im, q))
    return buf.getvalue()


def _transparent_index(rgba, q):
    # 구름 등으로 비어 있는(투명) 칸의 팔레트 번호를 찾아 투명으로 지정
    alpha = rgba.getchannel("A")
    if alpha.getextrema()[0] == 255:
        return None
    data = alpha.tobytes()
    i = data.find(b"\x00")
    return q.getpixel((i % rgba.width, i // rgba.width)) if i >= 0 else None


def main(geojson_path, only=None):
    ee.Initialize(project=PROJECT)
    OUT.mkdir(parents=True, exist_ok=True)
    index_file = OUT / "index.json"
    index = json.loads(index_file.read_text(encoding="utf-8")) if index_file.exists() else {
        "years": YEARS, "vis": [VIS_MIN, VIS_MAX], "palette": PALETTE, "res_m": RES_M, "sgg": {}}
    boxes = sgg_boxes(geojson_path)
    codes = only or sorted(boxes)
    for n, code in enumerate(codes, 1):
        if code in index["sgg"] and (OUT / index["sgg"][code]["file"]).exists():
            continue
        w, s, e, nb = boxes[code]["box"]
        lat0 = (s + nb) / 2
        dlat, dlon = PAD_KM / 111.0, PAD_KM / (111.0 * math.cos(math.radians(lat0)))
        w, s, e, nb = w - dlon, s - dlat, e + dlon, nb + dlat
        region = ee.Geometry.Rectangle([w, s, e, nb])
        width_m = (e - w) * 111_000 * math.cos(math.radians(lat0))
        height_m = (nb - s) * 111_000
        px_w, px_h = round(width_m / RES_M), round(height_m / RES_M)
        lst, scenes = landsat_lst(region)
        t = time.time()
        for attempt in range(3):
            try:
                url = lst.getThumbURL({"region": region, "dimensions": f"{px_w}x{px_h}", "crs": "EPSG:3857",
                                       "format": "png", "min": VIS_MIN, "max": VIS_MAX, "palette": PALETTE})
                raw = requests.get(url, timeout=600).content
                png = to_palette_png(raw)
                break
            except Exception as ex:  # 가끔 Earth Engine 시간 초과: 잠깐 쉬고 다시
                print("  retry", code, type(ex).__name__, str(ex)[:120])
                time.sleep(10)
        else:
            print("FAILED", code)
            continue
        # 시도별 하위 폴더(앞 두 자리 코드)로 나눠 저장: GitHub 웹 업로드는 한 번에 100개까지라서
        fname = f"{code[:2]}/{code}.png"
        (OUT / fname).parent.mkdir(exist_ok=True)
        (OUT / fname).write_bytes(png)
        index["sgg"][code] = {"name": boxes[code]["name"], "file": fname, "bounds": [w, s, e, nb],
                              "size": [px_w, px_h], "scenes": scenes.getInfo()}
        index_file.write_text(json.dumps(index, ensure_ascii=False, indent=0), encoding="utf-8")
        print(f"{n}/{len(codes)} {code} {px_w}x{px_h} {len(png)/1e6:.2f}MB {time.time()-t:.0f}s", flush=True)
    print("done", len(index["sgg"]))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:] or None)
