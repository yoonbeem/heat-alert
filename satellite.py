"""미리 만들어 둔 위성 지표면온도 그림(data/lst/)을 지도 위에 겹쳐 그리는 부분.

그림은 make_lst.py가 Earth Engine에서 만들어 저장한 PNG예요.
적응 영수증과 같은 방식으로 그립니다.
- 지도 엔진: MapLibre GL (웹 지도 라이브러리)
- 배경: '일반지도'(CARTO) 또는 '영상'(Esri World Imagery, 건물이 보이는 항공·위성 사진)
- 열지도: 30m 칸을 섞지 않고(nearest) 반투명으로 겹치고, 투명도 슬라이더로 조절
Streamlit 안에 작은 웹페이지(HTML)를 넣는 st.components.v1.html 로 보여 줘요.
"""
import base64
import json
from pathlib import Path

import pandas as pd

LST_DIR = Path(__file__).parent / "data" / "lst"
MAPLIBRE = "https://unpkg.com/maplibre-gl@4.7.1/dist/maplibre-gl"


def load_index() -> dict | None:
    f = LST_DIR / "index.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def png_data_uri(file_name: str) -> str:
    """그림 파일을 글자(base64)로 바꿔 지도에 바로 넣을 수 있게 한다."""
    data = (LST_DIR / file_name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def _points(lat, lon, shelters: pd.DataFrame | None) -> dict:
    feats = [{"type": "Feature", "geometry": {"type": "Point", "coordinates": [lon, lat]},
              "properties": {"kind": "me", "name": "우리 동네"}}]
    if shelters is not None:
        for _, r in shelters.iterrows():
            feats.append({"type": "Feature", "geometry": {"type": "Point", "coordinates": [float(r["경도"]), float(r["위도"])]},
                          "properties": {"kind": "shelter", "name": str(r["이름"])}})
    return {"type": "FeatureCollection", "features": feats}


def map_html(info: dict, lat: float, lon: float, shelters: pd.DataFrame | None,
             vmin: float, vmax: float, palette: list[str], height: int = 520) -> str:
    west, south, east, north = info["bounds"]
    cfg = {
        "center": [lon, lat],
        "image": png_data_uri(info["file"]),
        # 그림의 네 귀퉁이: 왼쪽 위, 오른쪽 위, 오른쪽 아래, 왼쪽 아래
        "corners": [[west, north], [east, north], [east, south], [west, south]],
        "points": _points(lat, lon, shelters),
    }
    gradient = ", ".join(f"#{c}" for c in palette)
    return f"""
<link href="{MAPLIBRE}.css" rel="stylesheet">
<script src="{MAPLIBRE}.js"></script>
<style>
  body {{ margin:0; font-family: sans-serif; }}
  #wrap {{ position:relative; height:{height}px; border-radius:12px; overflow:hidden; }}
  #map {{ position:absolute; inset:0; }}
  .panel {{ position:absolute; z-index:2; background:rgba(255,255,255,.9); border-radius:999px;
           padding:4px; display:flex; gap:4px; align-items:center; box-shadow:0 1px 4px rgba(0,0,0,.2); font-size:13px; }}
  .panel button {{ border:0; background:transparent; padding:5px 12px; border-radius:999px; cursor:pointer; font-size:13px; }}
  .panel button.on {{ background:#2f5d50; color:#fff; }}
  #base {{ top:10px; left:10px; }}
  #op {{ top:10px; left:170px; padding:4px 12px; }}
  #legend {{ position:absolute; z-index:2; right:10px; bottom:30px; background:rgba(255,255,255,.9); border-radius:10px;
            padding:8px 10px; font-size:12px; width:190px; box-shadow:0 1px 4px rgba(0,0,0,.2); }}
  #legend .bar {{ height:10px; border-radius:5px; background:linear-gradient(to right, {gradient}); margin:4px 0; }}
  #legend .row {{ display:flex; justify-content:space-between; }}
  .dot {{ display:inline-block; width:9px; height:9px; border-radius:50%; margin-right:4px; vertical-align:middle; }}
</style>
<div id="wrap">
  <div id="map"></div>
  <div id="base" class="panel"><button data-b="map">지도</button><button data-b="sat" class="on">영상</button></div>
  <div id="op" class="panel">투명도 <input id="opacity" type="range" min="0" max="100" value="60" style="width:110px"></div>
  <div id="legend"><b>여름 한낮 지표면온도</b>
    <div class="bar"></div><div class="row"><span>{vmin}℃↓</span><span>{vmax}℃↑</span></div>
    <div><span class="dot" style="background:#111"></span>우리 동네 <span class="dot" style="background:#1c7ed6;margin-left:8px"></span>무더위쉼터</div>
  </div>
</div>
<script>
const C = {json.dumps(cfg, ensure_ascii=False)};
const map = new maplibregl.Map({{
  container: "map", center: C.center, zoom: 15, maxZoom: 18, attributionControl: {{compact: true}},
  style: {{
    version: 8,
    sources: {{
      basemap: {{ type: "raster", tileSize: 256, attribution: "© OpenStreetMap © CARTO",
        tiles: ["https://a.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}.png",
                "https://b.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}.png"] }},
      sat: {{ type: "raster", tileSize: 256, attribution: "Esri World Imagery",
        tiles: ["https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{{z}}/{{y}}/{{x}}"] }},
      lst: {{ type: "image", url: C.image, coordinates: C.corners }}
    }},
    layers: [
      {{ id: "basemap", type: "raster", source: "basemap", layout: {{ visibility: "none" }} }},
      {{ id: "sat", type: "raster", source: "sat" }},
      {{ id: "lst", type: "raster", source: "lst",
         paint: {{ "raster-opacity": 0.6, "raster-resampling": "nearest", "raster-fade-duration": 0 }} }}
    ]
  }}
}});
map.addControl(new maplibregl.NavigationControl({{showCompass: false}}), "top-right");
map.addControl(new maplibregl.ScaleControl({{maxWidth: 120, unit: "metric"}}), "bottom-left");
document.querySelectorAll("#base button").forEach(b => b.onclick = () => {{
  document.querySelectorAll("#base button").forEach(x => x.classList.toggle("on", x === b));
  map.setLayoutProperty("sat", "visibility", b.dataset.b === "sat" ? "visible" : "none");
  map.setLayoutProperty("basemap", "visibility", b.dataset.b === "map" ? "visible" : "none");
}});
document.getElementById("opacity").oninput = e => map.setPaintProperty("lst", "raster-opacity", e.target.value / 100);
// 점(우리 동네, 쉼터)은 HTML 표시(Marker)로 올려요. 누르면 이름이 나와요.
C.points.features.forEach(f => {{
  const me = f.properties.kind === "me";
  const el = document.createElement("div");
  el.style.cssText = `width:${{me ? 16 : 12}}px;height:${{me ? 16 : 12}}px;border-radius:50%;` +
    `background:${{me ? "#111" : "#1c7ed6"}};border:2px solid #fff;box-shadow:0 0 3px rgba(0,0,0,.5);cursor:pointer`;
  new maplibregl.Marker({{element: el}}).setLngLat(f.geometry.coordinates)
    .setPopup(new maplibregl.Popup({{offset: 10, closeButton: false}}).setText(f.properties.name)).addTo(map);
}});
</script>
"""
