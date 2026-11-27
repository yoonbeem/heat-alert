"""미리 만들어 둔 위성 지표면온도 그림(data/lst/)을 지도 위에 겹쳐 그리는 부분.

그림은 make_lst.py가 Earth Engine에서 만들어 저장한 PNG예요.
여기서는 그 그림을 pydeck(지도 그리기 도구)의 BitmapLayer로 '지도 위 네모 칸'에 붙입니다.
"""
import base64
import json
from pathlib import Path

import pandas as pd
import pydeck as pdk

LST_DIR = Path(__file__).parent / "data" / "lst"


def load_index() -> dict | None:
    f = LST_DIR / "index.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


def png_data_uri(file_name: str) -> str:
    """그림 파일을 글자(base64)로 바꿔 지도에 바로 넣을 수 있게 한다."""
    data = (LST_DIR / file_name).read_bytes()
    return "data:image/png;base64," + base64.b64encode(data).decode()


def deck(info: dict, lat: float, lon: float, shelters: pd.DataFrame | None, opacity: float) -> pdk.Deck:
    west, south, east, north = info["bounds"]
    layers = [
        pdk.Layer(
            "BitmapLayer",
            # pdk.types.String으로 감싸야 pydeck이 '계산식'이 아니라 '글자 그대로'로 받아들여요
            image=pdk.types.String(png_data_uri(info["file"])),
            bounds=[[west, south], [west, north], [east, north], [east, south]],
            opacity=opacity,
        )
    ]
    if shelters is not None and len(shelters):
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=shelters.rename(columns={"위도": "lat", "경도": "lon"})[["lat", "lon", "이름"]],
                get_position="[lon, lat]",
                get_fill_color=[28, 126, 214],
                get_line_color=[255, 255, 255],
                stroked=True,
                line_width_min_pixels=1,
                radius_min_pixels=5,
                pickable=True,
            )
        )
    layers.append(
        pdk.Layer(
            "ScatterplotLayer",
            data=pd.DataFrame({"lat": [lat], "lon": [lon], "이름": ["우리 동네"]}),
            get_position="[lon, lat]",
            get_fill_color=[0, 0, 0],
            get_line_color=[255, 255, 255],
            stroked=True,
            line_width_min_pixels=2,
            radius_min_pixels=7,
            pickable=True,
        )
    )
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lon, zoom=11.3),
        tooltip={"text": "{이름}"},
        map_style="light",
    )


def legend_html(vmin: float, vmax: float, palette: list[str]) -> str:
    stops = ", ".join(f"#{c}" for c in palette)
    return (
        f'<div style="display:flex;align-items:center;gap:8px;font-size:0.85rem">'
        f"<span>{vmin}℃ 이하</span>"
        f'<div style="flex:1;height:12px;border-radius:6px;background:linear-gradient(to right, {stops})"></div>'
        f"<span>{vmax}℃ 이상</span></div>"
    )
