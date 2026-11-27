r"""전국 행정동(읍면동) 경계 파일에서 '동 이름 + 중심 좌표' 목록(data/dongs.csv)을 만드는 도구.

경계 자료: vuski/admdongkor (행정안전부 행정동 경계를 GeoJSON으로 정리한 공개 자료)
사용법: .\.venv\Scripts\python.exe make_dongs.py <HangJeongDong_verXXXX.geojson 경로>

중심 좌표는 '면적 가중 중심(centroid)'으로 계산해요. 동 모양이 초승달처럼 휘면 중심이 동 밖에 찍힐 수 있지만,
날씨·쉼터·열지도의 기준점으로 쓰기에는 충분히 가까워요.
"""
import csv
import json
import sys
from pathlib import Path


def ring_centroid(ring):
    """다각형 꼭짓점 목록으로 넓이와 중심을 구한다 (신발끈 공식)."""
    a = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    a /= 2
    if a == 0:
        return 0.0, ring[0][0], ring[0][1]
    return abs(a), cx / (6 * a), cy / (6 * a)


def feature_centroid(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    total = sx = sy = 0.0
    for poly in polys:
        area, x, y = ring_centroid([tuple(p[:2]) for p in poly[0]])  # 바깥 테두리만
        total += area
        sx += x * area
        sy += y * area
    return sx / total, sy / total


def main(src):
    gj = json.loads(Path(src).read_text(encoding="utf-8"))
    rows = []
    for f in gj["features"]:
        p = f["properties"]
        full = p["adm_nm"].split()  # 예: '서울특별시 종로구 사직동'
        sido, dong = full[0], full[-1]
        sigungu = " ".join(full[1:-1]) or sido  # 세종시는 시군구가 없어요
        lon, lat = feature_centroid(f["geometry"])
        rows.append({"시도": sido, "시군구": sigungu, "읍면동": dong, "코드": p["adm_cd2"],
                     "시군구코드": p["sgg"], "위도": round(lat, 5), "경도": round(lon, 5)})
    rows.sort(key=lambda r: r["코드"])
    out = Path(__file__).parent / "data" / "dongs.csv"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", newline="", encoding="utf-8-sig") as fp:
        w = csv.DictWriter(fp, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(len(rows), "dongs ->", out)


if __name__ == "__main__":
    main(sys.argv[1])
