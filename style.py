"""화면 꾸미기: 여름 느낌 색과 카드 모양.

Streamlit 기본 모양 위에 CSS(웹 화면 꾸밈 규칙)를 덧씌워요.
색은 '햇살 주황 · 하늘 파랑 · 쉼터 민트'를 기본으로 했어요.
"""
from html import escape

import streamlit as st

COLORS = {
    "danger": ("#ff4d4f", "#fff1f0"),
    "warn": ("#ff8c1a", "#fff4e6"),
    "watch": ("#f5b700", "#fffbe6"),
    "safe": ("#12b886", "#e6fcf5"),
}

CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
html, body, [class*="st-"], .stMarkdown, button, input, select, textarea { font-family: 'Pretendard', sans-serif !important; }
.stApp { background: linear-gradient(180deg, #e8f7ff 0%, #fff9ec 38%, #fffdf7 100%); }
.block-container { padding-top: 1.2rem; max-width: 1180px; }
header[data-testid="stHeader"] { background: transparent; }

.hero { position: relative; overflow: hidden; border-radius: 28px; padding: 26px 30px; margin-bottom: 14px;
  background: linear-gradient(120deg, #4fc3f7 0%, #7fd8ff 35%, #ffd27a 75%, #ffb056 100%); color: #fff;
  box-shadow: 0 12px 30px rgba(255, 160, 60, .25); }
.hero h1 { margin: 0; font-size: 2.1rem; font-weight: 800; letter-spacing: -0.5px; color: #fff; text-shadow: 0 2px 8px rgba(0,0,0,.15); }
.hero p { margin: 6px 0 0; font-size: 1.02rem; opacity: .95; }
.hero .sun { position: absolute; right: 28px; top: -18px; font-size: 96px; filter: drop-shadow(0 0 24px #fff3b0); }
.hero .wave { position: absolute; left: 0; right: 0; bottom: -2px; height: 22px;
  background: radial-gradient(circle at 12px -6px, transparent 14px, rgba(255,255,255,.55) 15px) repeat-x; background-size: 24px 22px; }

div[data-testid="stVerticalBlockBorderWrapper"] { background: rgba(255,255,255,.85); border-radius: 20px !important;
  border: 1px solid #ffe2b8 !important; box-shadow: 0 4px 14px rgba(255,170,80,.12); }

.alert { border-radius: 24px; padding: 22px 24px; height: 100%; box-shadow: 0 6px 18px rgba(0,0,0,.06); }
.alert .where { font-size: .95rem; color: #6b5a48; }
.alert .badge { display: inline-block; margin: 8px 0 10px; padding: 6px 18px; border-radius: 999px; color: #fff;
  font-weight: 800; font-size: 1.6rem; letter-spacing: -0.5px; }
.alert .tip { font-size: 1rem; color: #3d3127; line-height: 1.55; }
.alert .when { float: right; font-size: .8rem; color: #8a7663; background: #fff; border-radius: 999px; padding: 3px 10px; }

.stats { display: grid; gap: 10px; }
.stats.v { grid-template-columns: 1fr; }
.stats.h { grid-template-columns: repeat(3, 1fr); margin-top: 12px; }
.stat { background: #fff; border-radius: 18px; padding: 12px 16px; display: flex; align-items: center; gap: 12px;
  box-shadow: 0 4px 12px rgba(255,170,80,.14); border: 1px solid #fff0dc; }
.stat .ic { font-size: 1.7rem; }
.stat .lb { font-size: .82rem; color: #8a7663; }
.stat .vl { font-size: 1.45rem; font-weight: 800; color: #3d3127; }

.days { display: flex; gap: 10px; overflow-x: auto; padding: 14px 2px 6px; }
.day { min-width: 108px; flex: 1; background: #fff; border-radius: 18px; padding: 10px 12px; text-align: center;
  border-top: 6px solid var(--c); box-shadow: 0 4px 12px rgba(0,0,0,.05); }
.day .d { font-weight: 700; color: #3d3127; }
.day .lv { margin: 6px auto; display: inline-block; padding: 2px 10px; border-radius: 999px; background: var(--bg); color: var(--c);
  font-weight: 700; font-size: .85rem; }
.day .t { font-size: 1.2rem; font-weight: 800; color: #3d3127; }
.day .n { font-size: .8rem; color: #5c6bc0; height: 1.1em; }

button[data-baseweb="tab"] { font-size: 1rem; }
button[data-baseweb="tab"][aria-selected="true"] { color: #ff7a1a; }
div[data-baseweb="tab-highlight"] { background-color: #ff7a1a; }
@media (max-width: 700px) {
  .hero h1 { font-size: 1.5rem; } .hero .sun { font-size: 64px; right: 10px; }
  .stats.h { grid-template-columns: 1fr; }
}
</style>
"""


def inject():
    st.markdown(CSS, unsafe_allow_html=True)


def hero():
    st.markdown(
        '<div class="hero"><div class="sun">🌞</div>'
        "<h1>우리 동네 폭염 알리미</h1>"
        "<p>우리 동네 더위를 미리 알고, 가까운 무더위쉼터로 시원하게 피해요 🍉</p>"
        '<div class="wave"></div></div>',
        unsafe_allow_html=True,
    )


def alert_card(place, badge, kind, tip, when):
    c, bg = COLORS[kind]
    st.markdown(
        f'<div class="alert" style="background:{bg}; border:2px solid {c}33">'
        f'<span class="when">{escape(when)}</span><div class="where">📍 {escape(place)}</div>'
        f'<div class="badge" style="background:{c}">{escape(badge)}</div>'
        f'<div class="tip">{escape(tip)}</div></div>',
        unsafe_allow_html=True,
    )


def stat_cards(items, horizontal=False):
    cells = "".join(
        f'<div class="stat"><div class="ic">{ic}</div><div><div class="lb">{escape(lb)}</div>'
        f'<div class="vl">{escape(vl)}</div></div></div>'
        for ic, lb, vl in items
    )
    st.markdown(f'<div class="stats {"h" if horizontal else "v"}">{cells}</div>', unsafe_allow_html=True)


def day_strip(days):
    cells = ""
    for label, kind, level, temp, tropical in days:
        c, bg = COLORS[kind]
        cells += (
            f'<div class="day" style="--c:{c};--bg:{bg}"><div class="d">{escape(label)}</div>'
            f'<div class="lv">{escape(level)}</div><div class="t">{escape(temp)}</div>'
            f'<div class="n">{"🌙 열대야" if tropical else ""}</div></div>'
        )
    st.markdown(f'<div class="days">{cells}</div>', unsafe_allow_html=True)
