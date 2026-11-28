"""위성 지표면온도 그림을 위성사진(영상) 지도 위에 겹쳐 그리는 부분.

그림은 make_lst_sgg.py가 Earth Engine에서 시군구마다 미리 만든 PNG(data/lst_sgg/)예요.
- 지도 엔진: MapLibre GL (적응 영수증과 같은 웹 지도 라이브러리)
- 배경: '영상'(Esri World Imagery, 건물이 보이는 사진) 또는 '지도'(CARTO)
- 열지도: 30m 칸을 섞지 않고(nearest) 반투명으로 겹치고, 지도 안 투명도 슬라이더로 조절
Streamlit 안에 작은 웹페이지(HTML)를 넣는 st.components.v1.html 로 보여 줘요.
"""
import base64
import json
from html import escape
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parent
DATA = ROOT / "data"
SGG_DIR = DATA / "lst_sgg"
MAPLIBRE = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl"
# 열지도 파일을 나눠 올린 폴더(열지도_올리기_1·2·3)째로 올라간 경우에도 찾을 수 있게, data 폴더 후보를 여러 개 둬요
DATA_DIRS = [DATA] + sorted(p / "data" for p in ROOT.glob("열지도_올리기_*") if (p / "data").is_dir())


def _find(rel: str) -> Path | None:
    """여러 data 폴더 후보 가운데 rel 파일이 있는 곳 (나중에 올린 묶음을 먼저)."""
    for d in reversed(DATA_DIRS):
        if (d / rel).exists():
            return d / rel
    return None


def load_sgg_index() -> dict | None:
    f = _find("lst_sgg/index.json")
    return json.loads(f.read_text(encoding="utf-8")) if f else None


def load_dong_stats() -> pd.DataFrame | None:
    f = _find("dong_lst.csv")
    return pd.read_csv(f, dtype={"코드": str}, encoding="utf-8-sig").set_index("코드") if f else None


def overlay_for(index: dict | None, sgg_code: str) -> dict | None:
    """시군구 코드에 맞는 열지도 그림(글자로 바꾼 PNG)과 네 귀퉁이 좌표."""
    if not index or sgg_code not in index["sgg"]:
        return None
    info = index["sgg"][sgg_code]
    f = _find(f"lst_sgg/{info['file']}")
    if f is None:
        return None
    data = f.read_bytes()
    return {"uri": "data:image/png;base64," + base64.b64encode(data).decode(), "bounds": info["bounds"],
            "scenes": info.get("scenes")}


def _points(lat, lon, shelters: pd.DataFrame | None) -> list:
    pts = [{"kind": "me", "lon": lon, "lat": lat, "html": "<b>우리 동네</b>"}]
    if shelters is not None:
        for _, r in shelters.iterrows():
            info = f"<b>{escape(str(r['이름']))}</b><br>{r['거리(km)']} km · {escape(str(r.get('평일운영', '-')))}"
            pts.append({"kind": "shelter", "lon": float(r["경도"]), "lat": float(r["위도"]), "html": info})
    return pts


def map_html(lat: float, lon: float, shelters: pd.DataFrame | None, overlay: dict | None,
             vmin: float, vmax: float, palette: list[str], height: int = 560) -> str:
    cfg = {"center": [lon, lat], "points": _points(lat, lon, shelters), "overlay": None}
    if overlay:
        w, s, e, n = overlay["bounds"]
        cfg["overlay"] = {"url": overlay["uri"], "coordinates": [[w, n], [e, n], [e, s], [w, s]]}
    gradient = ", ".join(f"#{c}" for c in palette)
    legend_heat = (f'<div class="bar"></div><div class="row"><span>{vmin}℃↓</span><span>{vmax}℃↑</span></div>'
                   if overlay else '<div class="row">이 지역 열지도는 아직 없어요</div>')
    return f"""
<link href="{MAPLIBRE}.css" rel="stylesheet">
<script src="{MAPLIBRE}.js"></script>
<style>
  body {{ margin:0; font-family: 'Pretendard', 'Apple SD Gothic Neo', sans-serif; }}
  #wrap {{ position:relative; height:{height}px; border-radius:22px; overflow:hidden;
          box-shadow: 0 10px 30px rgba(255,140,50,.18); border: 3px solid #fff; }}
  #map {{ position:absolute; inset:0; }}
  .panel {{ position:absolute; z-index:2; background:rgba(255,255,255,.92); border-radius:999px;
           padding:4px; display:flex; gap:4px; align-items:center; box-shadow:0 2px 8px rgba(0,0,0,.15); font-size:13px; }}
  .panel button {{ border:0; background:transparent; padding:6px 14px; border-radius:999px; cursor:pointer; font-size:13px; color:#7a4a1d; }}
  .panel button.on {{ background:linear-gradient(135deg,#ff9f43,#ff6b6b); color:#fff; font-weight:700; }}
  #base {{ top:12px; left:12px; }}
  #op {{ top:12px; left:178px; padding:5px 14px; color:#7a4a1d; }}
  #op input {{ accent-color:#ff7a45; }}
  #legend {{ position:absolute; z-index:2; right:12px; bottom:32px; background:rgba(255,255,255,.94); border-radius:14px;
            padding:10px 12px; font-size:12px; width:200px; box-shadow:0 2px 8px rgba(0,0,0,.15); color:#5a3a1a; }}
  #legend .bar {{ height:10px; border-radius:5px; background:linear-gradient(to right, {gradient}); margin:6px 0 2px; }}
  #legend .row {{ display:flex; justify-content:space-between; }}
  .me {{ font-size:26px; line-height:26px; filter: drop-shadow(0 2px 2px rgba(0,0,0,.45)); cursor:pointer; }}
  .sh {{ width:26px; height:26px; border-radius:50%; background:#16c1c8; border:3px solid #fff; color:#fff; display:flex;
        align-items:center; justify-content:center; font-size:14px; box-shadow:0 2px 6px rgba(0,0,0,.35); cursor:pointer; }}
  .maplibregl-popup-content {{ border-radius:12px; font-size:13px; padding:8px 12px; }}
</style>
<div id="wrap">
  <div id="map"></div>
  <div id="base" class="panel"><button data-b="sat" class="on">🛰️ 영상</button><button data-b="map">🗺️ 지도</button></div>
  <div id="op" class="panel">🌡️ 열지도 <input id="opacity" type="range" min="0" max="100" value="55" style="width:110px"></div>
  <div id="legend"><b>여름 한낮 땅 표면 온도</b>{legend_heat}
    <div style="margin-top:6px">🏠 우리 동네 &nbsp; <span style="color:#16c1c8">●</span> 무더위쉼터</div>
  </div>
</div>
<script>
const C = {json.dumps(cfg, ensure_ascii=False)};
const sources = {{
  basemap: {{ type: "raster", tileSize: 256, attribution: "© OpenStreetMap © CARTO",
    tiles: ["https://a.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}.png",
            "https://b.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}.png"] }},
  sat: {{ type: "raster", tileSize: 256, attribution: "Esri World Imagery",
    tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}"] }}
}};
const layers = [
  {{ id: "basemap", type: "raster", source: "basemap", layout: {{ visibility: "none" }} }},
  {{ id: "sat", type: "raster", source: "sat" }}
];
if (C.overlay) {{
  sources.lst = {{ type: "image", url: C.overlay.url, coordinates: C.overlay.coordinates }};
  layers.push({{ id: "lst", type: "raster", source: "lst",
    paint: {{ "raster-opacity": 0.55, "raster-resampling": "nearest", "raster-fade-duration": 0 }} }});
}} else {{ document.getElementById("op").style.display = "none"; }}
const map = new maplibregl.Map({{ container: "map", center: C.center, zoom: 15, maxZoom: 18,
  attributionControl: {{compact: true}}, style: {{ version: 8, sources, layers }} }});
map.addControl(new maplibregl.NavigationControl({{showCompass: false}}), "top-right");
map.addControl(new maplibregl.ScaleControl({{maxWidth: 120, unit: "metric"}}), "bottom-left");
document.querySelectorAll("#base button").forEach(b => b.onclick = () => {{
  document.querySelectorAll("#base button").forEach(x => x.classList.toggle("on", x === b));
  map.setLayoutProperty("sat", "visibility", b.dataset.b === "sat" ? "visible" : "none");
  map.setLayoutProperty("basemap", "visibility", b.dataset.b === "map" ? "visible" : "none");
}});
document.getElementById("opacity").oninput = e => map.getLayer("lst") && map.setPaintProperty("lst", "raster-opacity", e.target.value / 100);
// 점은 HTML 표시(Marker)로 올려요. 누르면 이름이 나와요.
C.points.forEach(p => {{
  const el = document.createElement("div");
  if (p.kind === "me") {{ el.className = "me"; el.textContent = "🏠"; }} else {{ el.className = "sh"; el.textContent = "❄"; }}
  new maplibregl.Marker({{element: el}}).setLngLat([p.lon, p.lat])
    .setPopup(new maplibregl.Popup({{offset: 14, closeButton: false}}).setHTML(p.html)).addTo(map);
}});
</script>
"""
