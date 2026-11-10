"""Visual theme: Christmas red and green, seasonal backdrop, motion. No app logic."""
from __future__ import annotations

import io
import math
import urllib.parse
from typing import List

import streamlit as st
from PIL import Image, ImageDraw

RED, RED_D, RED_L = "#c4283b", "#8f1b2b", "#e0495b"
GREEN, GREEN_D, GREEN_L = "#2f8f5b", "#1b5a3a", "#5fbb88"
CREAM, GOLD = "#f4ecdc", "#e6cf94"


def _uri(svg: str) -> str:
    return "data:image/svg+xml;utf8," + urllib.parse.quote(svg.replace("\n", ""), safe="/:=,;()' ")


# --------------------------------------------------------------------------- tree
def tree_svg() -> str:
    cx = 300
    tiers = [(130, 310, 105), (230, 440, 150), (350, 580, 195), (480, 730, 240), (630, 880, 280)]
    parts: List[str] = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 1000" preserveAspectRatio="xMidYMax meet">',
        '<defs>'
        '<linearGradient id="g" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2f7d51"/><stop offset="1" stop-color="#0f3a25"/></linearGradient>'
        '<linearGradient id="g2" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#000" stop-opacity=".35"/><stop offset=".5" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".35"/></linearGradient>'
        '<filter id="b" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="5"/></filter>'
        '<style>.t{animation:tw 3.2s ease-in-out infinite}.t1{animation-delay:.5s}.t2{animation-delay:1.1s}.t3{animation-delay:1.7s}.t4{animation-delay:2.3s}'
        '@keyframes tw{0%,100%{opacity:.35}50%{opacity:1}}</style></defs>',
        f'<rect x="{cx-22}" y="880" width="44" height="90" rx="4" fill="#3a2518"/>',
    ]
    for top, bot, hw in reversed(tiers):
        d = f"M{cx} {top} L{cx+hw} {bot} Q{cx} {bot+34} {cx-hw} {bot} Z"
        parts.append(f'<path d="{d}" fill="url(#g)"/><path d="{d}" fill="url(#g2)"/>')
        parts.append(f'<path d="{d}" fill="none" stroke="#7fd1a0" stroke-opacity=".18" stroke-width="2"/>')
    cols = [RED_L, GOLD, "#ffffff", GREEN_L, RED_L]
    n = 0
    for i, (top, bot, hw) in enumerate(tiers):
        y0, y1 = top + (bot - top) * 0.52, bot - 4
        wpt = lambda t: (cx - hw * (0.52 + 0.46 * t) * (1 - 2 * t * 0 ) , 0)
        # swag from left edge to right edge across the tier
        xl = cx - hw * 0.62; xr = cx + hw * 0.62
        yl = top + (bot - top) * 0.62; yc = bot + 18
        parts.append(f'<path d="M{xl} {yl} Q{cx} {yc+22} {xr} {yl}" fill="none" stroke="{RED}" stroke-opacity=".9" stroke-width="5" stroke-dasharray="0.1 10" stroke-linecap="round"/>')
        for k in range(1, 7):
            t = k / 7
            x = (1 - t) ** 2 * xl + 2 * t * (1 - t) * cx + t ** 2 * xr
            y = (1 - t) ** 2 * yl + 2 * t * (1 - t) * (yc + 22) + t ** 2 * yl
            c = cols[(n + k) % len(cols)]
            parts.append(f'<circle class="t t{(n+k)%5}" cx="{x:.0f}" cy="{y+7:.0f}" r="11" fill="{c}" filter="url(#b)"/>'
                         f'<circle class="t t{(n+k)%5}" cx="{x:.0f}" cy="{y+7:.0f}" r="4.5" fill="{c}"/>')
        n += 3
    for (x, y, c) in [(cx - 70, 560, RED), (cx + 118, 655, RED_D), (cx - 150, 800, RED), (cx + 60, 810, GOLD), (cx - 40, 440, GOLD), (cx + 90, 470, RED)]:
        parts.append(f'<circle cx="{x}" cy="{y}" r="15" fill="{c}"/><circle cx="{x-5}" cy="{y-5}" r="4" fill="#fff" fill-opacity=".55"/>')
    star = " ".join(f"{cx + (r)*math.sin(a*math.pi/5):.1f},{98 - (r)*math.cos(a*math.pi/5):.1f}" for a, r in [(i, 34 if i % 2 == 0 else 15) for i in range(10)])
    parts.append(f'<polygon points="{star}" fill="{GOLD}" filter="url(#b)" opacity=".7"/><polygon points="{star}" fill="{GOLD}"/>')
    parts.append("</svg>")
    return "".join(parts)


def garland_tile() -> str:
    w, h = 260, 70
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    path = f"M-2 8 Q{w/2} 62 {w+2} 8"
    p.append(f'<path d="{path}" fill="none" stroke="#0e3d26" stroke-width="16" stroke-linecap="round"/>')
    p.append(f'<path d="{path}" fill="none" stroke="#1d6b43" stroke-width="10" stroke-linecap="round"/>')
    p.append(f'<path d="{path}" fill="none" stroke="#3b9a68" stroke-width="3" stroke-linecap="round" stroke-dasharray="3 5"/>')
    for k in range(0, 27):
        t = k / 26
        x = t * (w + 4) - 2
        y = (1 - t) ** 2 * 8 + 2 * t * (1 - t) * 62 + t ** 2 * 8
        a = ((k * 47) % 60) - 30
        for s in (-1, 1):
            p.append(f'<line x1="{x:.1f}" y1="{y:.1f}" x2="{x+s*7:.1f}" y2="{y+9+ (k%3)*2:.1f}" stroke="#2c8458" stroke-width="2" stroke-linecap="round"/>')
    for t in (0.22, 0.5, 0.78):
        x = t * w; y = (1 - t) ** 2 * 8 + 2 * t * (1 - t) * 62 + t ** 2 * 8
        for dx, dy in ((0, 0), (6, 3), (-6, 3)):
            p.append(f'<circle cx="{x+dx:.1f}" cy="{y+dy+1:.1f}" r="3.4" fill="{RED}"/><circle cx="{x+dx-1:.1f}" cy="{y+dy:.1f}" r="1" fill="#fff" fill-opacity=".6"/>')
    p.append("</svg>")
    return "".join(p)


def lights_tile(group: int) -> str:
    """Bulbs hanging on the garland. group 0 / 1 are the two alternating sets."""
    w, h = 260, 70
    cols = [RED_L, GOLD, GREEN_L, "#ffffff", RED_L, GOLD]
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">',
         '<defs><filter id="b" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="4"/></filter></defs>']
    for k in range(6):
        if k % 2 != group:
            continue
        t = (k + 0.5) / 6
        x = t * w; y = (1 - t) ** 2 * 8 + 2 * t * (1 - t) * 62 + t ** 2 * 8 + 6
        c = cols[k]
        p.append(f'<line x1="{x:.1f}" y1="{y-5:.1f}" x2="{x:.1f}" y2="{y+4:.1f}" stroke="#0c2a1b" stroke-width="2"/>'
                 f'<circle cx="{x:.1f}" cy="{y+11:.1f}" r="12" fill="{c}" filter="url(#b)" opacity=".85"/>'
                 f'<ellipse cx="{x:.1f}" cy="{y+11:.1f}" rx="4.2" ry="6" fill="{c}"/>')
    p.append("</svg>")
    return "".join(p)


def snow_tile(size: int, n: int, seed: int) -> str:
    import random
    rnd = random.Random(seed)
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size}">']
    for _ in range(n):
        r = rnd.choice([1.2, 1.6, 2.0, 2.6])
        p.append(f'<circle cx="{rnd.uniform(0,size):.0f}" cy="{rnd.uniform(0,size):.0f}" r="{r}" fill="#fff" fill-opacity="{rnd.uniform(.35,.85):.2f}"/>')
    p.append("</svg>")
    return "".join(p)


def favicon() -> Image.Image:
    im = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((56, 8, 72, 26), fill=(230, 207, 148))
    d.ellipse((14, 100 - 80 + 20, 114, 120), fill=(196, 40, 59))
    d.ellipse((34, 44, 52, 62), fill=(255, 255, 255, 120))
    d.arc((30, 70, 98, 110), 200, 340, fill=(244, 236, 220), width=5)
    return im


# --------------------------------------------------------------------------- part icons (export cards)
def _defs(uid: str) -> str:
    return (f'<defs><radialGradient id="s{uid}" cx=".35" cy=".3" r=".9"><stop offset="0" stop-color="#fbf5e6"/>'
            f'<stop offset=".6" stop-color="#d9ceb4"/><stop offset="1" stop-color="#9c9378"/></radialGradient>'
            f'<linearGradient id="r{uid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{RED_L}"/><stop offset="1" stop-color="{RED_D}"/></linearGradient>'
            f'<linearGradient id="gr{uid}" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{GREEN_L}"/><stop offset="1" stop-color="{GREEN_D}"/></linearGradient></defs>')


def _mini_trees(x0, y0, sc=1.0, color="#35503f", op=".55") -> str:
    out = []
    for dx, h in ((-14, 22), (2, 28), (18, 20)):
        x = x0 + dx * sc
        out.append(f'<path d="M{x} {y0-h*sc} L{x+9*sc} {y0} L{x-9*sc} {y0} Z" fill="{color}" fill-opacity="{op}"/>')
    return "".join(out)


def icon(kind: str) -> str:
    u = kind
    head = f'<svg class="ico" viewBox="0 0 120 96" xmlns="http://www.w3.org/2000/svg">{_defs(u)}'
    if kind == "zip":
        body = (f'<rect x="26" y="40" width="68" height="44" rx="4" fill="url(#r{u})"/>'
                f'<rect x="22" y="30" width="76" height="16" rx="4" fill="{RED_L}"/>'
                f'<rect x="54" y="30" width="12" height="54" fill="{CREAM}" fill-opacity=".92"/>'
                f'<path d="M60 30 C40 6 22 22 46 30 Z" fill="url(#gr{u})"/><path d="M60 30 C80 6 98 22 74 30 Z" fill="url(#gr{u})"/>'
                f'<circle cx="60" cy="30" r="5" fill="{GREEN_D}"/>')
    elif kind == "ball":
        body = (f'<clipPath id="c{u}"><circle cx="60" cy="54" r="34"/></clipPath>'
                f'<circle cx="60" cy="54" r="34" fill="url(#s{u})"/><g clip-path="url(#c{u})">' + _mini_trees(60, 88, 1.2) + '</g>' +
                f'<path d="M38 36 Q52 24 70 28" fill="none" stroke="#fff" stroke-opacity=".6" stroke-width="3" stroke-linecap="round"/>'
                f'<rect x="54" y="14" width="12" height="8" rx="2" fill="{GOLD}"/>'
                f'<circle cx="60" cy="10" r="6.5" fill="none" stroke="{GOLD}" stroke-width="3"/>')
    elif kind == "cap":
        body = (f'<path d="M20 40 H100 C100 82 78 90 60 90 C42 90 20 82 20 40 Z" fill="url(#s{u})"/>'
                f'<rect x="14" y="32" width="92" height="9" rx="4" fill="#cfc4a8"/>'
                f'<rect x="34" y="22" width="52" height="11" rx="2" fill="#e9dfc6"/>'
                + "".join(f'<line x1="{x}" y1="22" x2="{x+5}" y2="33" stroke="#b3a98c" stroke-width="2"/>' for x in range(36, 84, 8)) +
                f'<ellipse cx="60" cy="36" rx="22" ry="4" fill="none" stroke="{GREEN}" stroke-width="2.5"/>')
    elif kind == "tile":
        body = (f'<rect x="18" y="20" width="84" height="56" rx="5" fill="#cfc4a8"/>'
                f'<rect x="24" y="26" width="72" height="44" rx="2" fill="url(#s{u})"/>' + _mini_trees(60, 66, 1.4, "#35503f", ".6") +
                f'<circle cx="82" cy="38" r="5" fill="#fff" fill-opacity=".8"/>')
    else:  # assembly
        body = (f'<clipPath id="c{u}"><circle cx="60" cy="42" r="30"/></clipPath>'
                f'<circle cx="60" cy="42" r="30" fill="url(#s{u})"/><g clip-path="url(#c{u})">' + _mini_trees(60, 74, 1.1) + '</g>' +
                f'<path d="M34 62 H86 C86 80 72 86 60 86 C48 86 34 80 34 62 Z" fill="#cfc4a8" fill-opacity=".0"/>'
                f'<path d="M36 66 Q60 76 84 66" fill="none" stroke="{RED}" stroke-width="2" stroke-dasharray="3 3"/>'
                f'<circle cx="60" cy="9" r="5.5" fill="none" stroke="{GOLD}" stroke-width="3"/>')
    return head + body + "</svg>"


# --------------------------------------------------------------------------- CSS
CSS = r"""
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;600;700&family=Inter:wght@400;500;600&display=swap');
:root{
  --red:#c4283b; --red-d:#8f1b2b; --red-l:#e0495b; --green:#2f8f5b; --green-d:#1b5a3a; --green-l:#5fbb88;
  --cream:#f4ecdc; --muted:#a9b9ae; --gold:#e6cf94; --line:rgba(244,236,220,.13);
  --panel:rgba(10,28,19,.86); --panel-2:rgba(18,44,31,.9);
  --ease:cubic-bezier(.22,.8,.24,1);
  --serif:'Playfair Display',Georgia,'Times New Roman',serif;
  --sans:'Inter',system-ui,-apple-system,'Segoe UI',Roboto,sans-serif;
}
html,body{background:#06110b !important}
.stApp,[data-testid="stAppViewContainer"],[data-testid="stMain"],[data-testid="stHeader"]{background:transparent !important}
.stApp{font-family:var(--sans);color:var(--cream)}
/* ---------- seasonal backdrop ---------- */
.stApp::before{content:"";position:fixed;inset:0;z-index:-3;pointer-events:none;
  background:
   radial-gradient(1100px 650px at 82% 4%,rgba(47,143,91,.20),transparent 62%),
   radial-gradient(900px 620px at -4% 108%,rgba(196,40,59,.30),transparent 60%),
   linear-gradient(180deg,#0c2017 0%,#06110b 70%);}
.stApp::after{content:"";position:fixed;right:-11vw;bottom:-2vh;width:min(42vw,600px);height:100vh;z-index:-2;pointer-events:none;
  background:url("__TREE__") no-repeat right bottom/contain;opacity:.5;
  -webkit-mask-image:linear-gradient(90deg,transparent 0%,#000 45%);mask-image:linear-gradient(90deg,transparent 0%,#000 45%);}
.xm-snow,.xm-snow2,.xm-hearth{position:fixed;pointer-events:none;z-index:-1}
.xm-snow{inset:0;background:url("__SNOW1__");background-size:320px 320px;opacity:.5;animation:snow1 22s linear infinite}
.xm-snow2{inset:0;background:url("__SNOW2__");background-size:520px 520px;opacity:.35;animation:snow2 38s linear infinite}
.xm-hearth{left:-12vw;bottom:-20vh;width:60vw;height:60vh;border-radius:50%;
  background:radial-gradient(closest-side,rgba(226,92,58,.20),rgba(196,40,59,.10) 55%,transparent 100%);
  animation:flicker 5.5s ease-in-out infinite;mix-blend-mode:screen}
@keyframes snow1{to{background-position:-60px 320px}}
@keyframes snow2{to{background-position:90px 520px}}
@keyframes flicker{0%,100%{opacity:.85;transform:scale(1)}18%{opacity:1;transform:scale(1.03)}37%{opacity:.78}58%{opacity:.98;transform:scale(1.015)}80%{opacity:.82}}

/* ---------- layout ---------- */
[data-testid="stMainBlockContainer"]{max-width:1160px;padding:0 2rem 5rem}
[data-testid="stHeader"]{height:2.5rem}
footer,[data-testid="stDecoration"],[data-testid="stToolbarActions"],[data-testid="stMainMenu"],.stAppDeployButton,[data-testid="stAppDeployButton"]{display:none !important}
[data-testid="stExpandSidebarButton"]{position:fixed !important;top:.8rem;left:.8rem;z-index:1000;width:2.6rem;height:2.6rem;border-radius:50% !important;display:grid !important;place-items:center;
  background:linear-gradient(145deg,var(--red-l),var(--red-d)) !important;border:2px solid rgba(255,255,255,.35);box-shadow:0 6px 18px rgba(196,40,59,.5);transition:transform .25s var(--ease),box-shadow .25s}
[data-testid="stExpandSidebarButton"]:hover{transform:scale(1.1);box-shadow:0 8px 24px rgba(224,73,91,.65)}
[data-testid="stExpandSidebarButton"] span,[data-testid="stExpandSidebarButton"] span span{color:#fff !important}
h1,h2,h3,h4,.hero h1,.page-title,.sec,.cta-t b,.stat b,.fitcard b{font-family:var(--serif) !important;letter-spacing:.2px}
h1,h2,h3,h4{color:var(--cream)}
p,label,li,span,div{font-family:var(--sans)}
[data-testid="stMarkdownContainer"] p{color:var(--cream)}
a{color:var(--green-l)}

/* ---------- hero ---------- */
.hero{margin:-1.2rem -2rem 0;padding:0 2rem 0;animation:rise .9s var(--ease) both}
.garland{position:relative;height:70px;margin:0 -2rem;background:url("__GARLAND__") repeat-x top left;filter:drop-shadow(0 6px 10px rgba(0,0,0,.35))}
.lights{position:absolute;inset:0;background-repeat:repeat-x;background-position:top left}
.lights.a{background-image:url("__LIGHTS0__");animation:bulb 3.4s ease-in-out infinite}
.lights.b{background-image:url("__LIGHTS1__");animation:bulb 3.4s ease-in-out infinite;animation-delay:1.7s}
@keyframes bulb{0%,100%{opacity:.35}50%{opacity:1}}
.hero h1{font-size:clamp(2rem,4.2vw,3.1rem);font-weight:600;line-height:1.1;margin:.9rem 0 .5rem;padding:0;
  background:linear-gradient(100deg,#fff6e6 0%,#f4ecdc 40%,#f0b9bf 100%);-webkit-background-clip:text;background-clip:text;color:transparent}
.hero p{max-width:640px;color:var(--muted);font-size:1.02rem;line-height:1.55;margin:0 0 1.2rem}
@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
@keyframes fade{from{opacity:0}to{opacity:1}}
@keyframes pop{from{opacity:0;transform:translateY(16px) scale(.97)}to{opacity:1;transform:none}}

/* ---------- sidebar ---------- */
[data-testid="stSidebar"]{background:linear-gradient(180deg,rgba(9,26,18,.94),rgba(6,17,11,.96)) !important;border-right:1px solid var(--line);backdrop-filter:blur(10px)}
[data-testid="stSidebar"] [data-testid="stSidebarHeader"]{height:1.5rem}
@media (min-width:901px){section[data-testid="stSidebar"]{min-width:23rem !important;width:23rem !important}}
.sec{display:flex;align-items:center;gap:.7rem;margin:1.5rem 0 .6rem;font-family:var(--serif);font-size:1.18rem;font-weight:600;color:var(--cream);animation:fade .6s var(--ease) both}
.sec i{font-style:normal;display:inline-grid;place-items:center;width:1.55rem;height:1.55rem;border-radius:50%;font-family:var(--sans);font-size:.78rem;font-weight:600;
  background:linear-gradient(145deg,var(--red-l),var(--red-d));box-shadow:0 2px 8px rgba(196,40,59,.45)}
.sec:nth-of-type(even) i{background:linear-gradient(145deg,var(--green-l),var(--green-d));box-shadow:0 2px 8px rgba(47,143,91,.45)}
.hint{color:var(--muted);font-size:.84rem;line-height:1.45;margin:-.2rem 0 .8rem}
[data-testid="stSidebar"] label p,[data-testid="stWidgetLabel"] p{font-size:.88rem;color:#dfe6dc}

/* ---------- inputs ---------- */
[data-testid="stSlider"] [data-rac][style*="translate(-50%"]>div:last-child,[data-testid="stSlider"] [data-rac][style*="translate(-50%"]{transition:transform .22s var(--ease),box-shadow .22s var(--ease) !important}
[data-testid="stSlider"] [data-rac][style*="translate(-50%"]:hover{filter:drop-shadow(0 0 7px rgba(196,40,59,.65))}
[data-testid="stSliderThumbValue"]{color:var(--cream) !important;font-weight:600;font-size:.8rem;transition:transform .2s var(--ease)}
[data-testid="stSliderTickBarMin"],[data-testid="stSliderTickBarMax"]{color:var(--muted)}
[data-testid="stSlider"] [data-baseweb="slider"]>div>div{transition:background .25s}
[data-testid="stWidgetLabel"]{transition:color .2s}
[data-testid="stFileUploaderDropzone"]{background:rgba(244,236,220,.04);border:1.5px dashed rgba(244,236,220,.28);border-radius:14px;transition:all .3s var(--ease)}
[data-testid="stFileUploaderDropzone"]:hover{border-color:var(--green-l);background:rgba(47,143,91,.10);transform:translateY(-1px);box-shadow:0 8px 24px rgba(0,0,0,.25)}
[data-testid="stNumberInput"] input,[data-baseweb="select"]>div{background:rgba(244,236,220,.05) !important;border-radius:10px;transition:box-shadow .25s,border-color .25s}
[data-testid="stExpander"]{border:1px solid var(--line);border-radius:14px;background:rgba(244,236,220,.03);transition:border-color .3s,background .3s}
[data-testid="stExpander"]:hover{border-color:rgba(95,187,136,.45);background:rgba(244,236,220,.05)}
[data-testid="stExpander"] summary{font-weight:500}
[data-testid="stCheckbox"] label{transition:opacity .2s}
[role="switch"],[data-baseweb="checkbox"] [role="checkbox"]{transition:background .3s var(--ease)}

/* ---------- buttons ---------- */
.stButton>button,[data-testid="stDownloadButton"]>button{font-family:var(--sans);font-weight:500;border-radius:12px;border:1px solid rgba(244,236,220,.22);
  background:rgba(244,236,220,.06);color:var(--cream);transition:transform .22s var(--ease),box-shadow .22s var(--ease),background .25s,border-color .25s}
.stButton>button:hover,[data-testid="stDownloadButton"]>button:hover{transform:translateY(-2px);border-color:var(--green-l);background:rgba(47,143,91,.16);box-shadow:0 10px 24px rgba(0,0,0,.32)}
.stButton>button:active,[data-testid="stDownloadButton"]>button:active{transform:translateY(0) scale(.98);transition-duration:.08s}
.stButton>button[kind="primary"],[data-testid="stBaseButton-primary"]{position:relative;overflow:hidden;border:0;color:#fff;font-weight:600;letter-spacing:.2px;padding:.7rem 1.6rem;
  background:linear-gradient(135deg,var(--red-l) 0%,var(--red) 45%,var(--red-d) 100%);box-shadow:0 8px 22px rgba(196,40,59,.4),inset 0 1px 0 rgba(255,255,255,.25)}
.stButton>button[kind="primary"]::after,[data-testid="stBaseButton-primary"]::after{content:"";position:absolute;top:0;left:-70%;width:45%;height:100%;
  background:linear-gradient(100deg,transparent,rgba(255,255,255,.35),transparent);transform:skewX(-20deg);animation:sheen 4.6s ease-in-out infinite}
.stButton>button[kind="primary"]:hover,[data-testid="stBaseButton-primary"]:hover{background:linear-gradient(135deg,#ee5a6c,var(--red) 50%,var(--red-d));box-shadow:0 14px 30px rgba(196,40,59,.5);transform:translateY(-2px)}
@keyframes sheen{0%,55%{left:-70%}100%{left:130%}}

/* ---------- segmented controls (one control style everywhere) ---------- */
[data-testid="stButtonGroup"]{background:transparent;border:0;padding:0}
[data-testid="stButtonGroup"] [role="radiogroup"],[data-testid="stButtonGroup"]>div:not([data-testid]){background:rgba(244,236,220,.06);border:1px solid var(--line);border-radius:14px;padding:4px;gap:2px;width:fit-content;max-width:100%;flex-wrap:wrap}
[data-testid="stButtonGroup"] button{border:0 !important;border-radius:10px !important;background:transparent !important;color:var(--muted) !important;font-weight:500;
  padding:.42rem .95rem;box-shadow:none !important;transition:background .35s var(--ease),color .25s,transform .2s var(--ease),box-shadow .35s var(--ease) !important}
[data-testid="stButtonGroup"] button:hover{color:var(--cream) !important;background:rgba(244,236,220,.09) !important}
[data-testid="stButtonGroup"] button[aria-checked="true"],[data-testid="stButtonGroup"] button[data-selected="true"],[data-testid="stButtonGroup"] button[kind="segmented_controlActive"]{
  background:linear-gradient(145deg,var(--green),var(--green-d)) !important;color:#fff !important;box-shadow:0 4px 14px rgba(27,90,58,.6),inset 0 1px 0 rgba(255,255,255,.2) !important}
[data-testid="stButtonGroup"] button:active{transform:scale(.95)}
.control-label{font-size:.7rem;letter-spacing:.12em;text-transform:uppercase;color:var(--muted);margin:0 0 .35rem .2rem}

/* ---------- navigation (tab bar) ---------- */
.st-key-nav{margin:.2rem 0 1.3rem;border-bottom:1px solid var(--line);padding-bottom:.9rem;animation:rise .8s .1s var(--ease) both}
.st-key-nav [data-testid="stButtonGroup"],.st-key-nav [data-testid="stElementContainer"]{width:100% !important}
.st-key-nav [data-testid="stButtonGroup"] [role="radiogroup"],.st-key-nav [data-testid="stButtonGroup"]>div:not([data-testid]){width:100% !important;background:transparent;border:0;padding:0;gap:.5rem;width:100%;flex-wrap:nowrap}
.st-key-nav [data-testid="stButtonGroup"] button{font-family:var(--serif);font-size:1.08rem;padding:.7rem 1.3rem;border-radius:12px !important;
  background:rgba(244,236,220,.05) !important;border:1px solid var(--line) !important;white-space:nowrap}
.st-key-nav [data-testid="stButtonGroup"] button:hover{border-color:rgba(95,187,136,.55) !important;transform:translateY(-2px)}
.st-key-nav [data-testid="stButtonGroup"] button[aria-checked="true"],.st-key-nav [data-testid="stButtonGroup"] button[data-selected="true"],.st-key-nav [data-testid="stButtonGroup"] button[kind="segmented_controlActive"]{
  background:linear-gradient(145deg,var(--green),var(--green-d)) !important;border-color:transparent !important}
.st-key-nav [data-testid="stButtonGroup"] button:last-child{margin-left:auto;color:#fff !important;font-weight:600;border-color:transparent !important;
  background:linear-gradient(135deg,var(--red-l),var(--red) 50%,var(--red-d)) !important;box-shadow:0 6px 18px rgba(196,40,59,.38);animation:glow 3.6s ease-in-out infinite}
.st-key-nav [data-testid="stButtonGroup"] button:last-child:hover{box-shadow:0 12px 26px rgba(196,40,59,.55)}
.st-key-nav [data-testid="stButtonGroup"] button:last-child[aria-checked="true"],.st-key-nav [data-testid="stButtonGroup"] button:last-child[data-selected="true"]{animation:none;box-shadow:0 0 0 2px rgba(255,255,255,.4),0 8px 22px rgba(196,40,59,.5) !important}
@keyframes glow{0%,100%{box-shadow:0 6px 18px rgba(196,40,59,.30)}50%{box-shadow:0 8px 30px rgba(224,73,91,.62)}}

/* ---------- pages ---------- */
[class*="st-key-page_"]{animation:pop .65s var(--ease) both}
.panel{background:var(--panel);border:1px solid var(--line);border-radius:18px;padding:1.2rem 1.4rem;backdrop-filter:blur(8px);box-shadow:0 14px 40px rgba(0,0,0,.28)}
.page-title{font-family:var(--serif);font-size:1.7rem;margin:0 0 .3rem}
.page-sub{color:var(--muted);margin:0 0 1.1rem;max-width:640px;line-height:1.55}
[class*="st-key-stage"]{border-radius:22px;border:1px solid var(--line);overflow:hidden;box-shadow:0 20px 50px rgba(0,0,0,.35);transition:background .6s var(--ease),border-color .4s}
.st-key-stage_lit{background:radial-gradient(70% 60% at 50% 42%,#10281c 0%,#07110c 75%)}
.st-key-stage_day{background:radial-gradient(70% 60% at 50% 42%,#e9eeea 0%,#b4c2b8 85%)}
[data-testid="stPlotlyChart"]{animation:fade .9s var(--ease) both}
[data-stale="true"]{transition:opacity .4s var(--ease)}
.stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:.8rem;margin:1rem 0 .4rem}
.stat{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:.8rem 1rem;animation:pop .7s var(--ease) both;transition:transform .3s var(--ease),border-color .3s}
.stat:nth-child(2){animation-delay:.06s}.stat:nth-child(3){animation-delay:.12s}.stat:nth-child(4){animation-delay:.18s}.stat:nth-child(5){animation-delay:.24s}
.stat:hover{transform:translateY(-3px);border-color:rgba(95,187,136,.5)}
.stat b{display:block;font-family:var(--serif);font-size:1.35rem;font-weight:600}
.stat span{font-size:.74rem;letter-spacing:.1em;text-transform:uppercase;color:var(--muted)}
.st-key-cta{margin-top:1.4rem;padding:1.1rem 1.4rem;border-radius:18px;border:1px solid rgba(196,40,59,.4);
  background:linear-gradient(120deg,rgba(143,27,43,.40),rgba(27,90,58,.30));animation:pop .8s .15s var(--ease) both}
.cta-t b{font-family:var(--serif);font-size:1.15rem;font-weight:600}
.cta-t span{color:var(--muted);font-size:.9rem}

/* ---------- progress: candy cane ---------- */
[data-testid="stProgress"] [role="progressbar"]{background:rgba(244,236,220,.1) !important;border-radius:999px;height:12px}
[data-testid="stProgress"] [role="progressbar"]>div{border-radius:999px;background:repeating-linear-gradient(-45deg,var(--red) 0 10px,#f7efe0 10px 20px) !important;background-size:28px 28px;animation:cane 1s linear infinite;transition:width .45s var(--ease)}
@keyframes cane{to{background-position:28px 0}}
[data-testid="stSpinner"] svg,.stSpinner svg{color:var(--red-l)}

/* ---------- export cards ---------- */
.chips{display:flex;flex-wrap:wrap;gap:.5rem;margin:.2rem 0 1rem}
.chip{padding:.28rem .8rem;border-radius:999px;border:1px solid var(--line);background:rgba(244,236,220,.06);font-size:.82rem;color:var(--cream)}
.xc{position:relative;display:flex;flex-direction:column;gap:.3rem;padding:1.1rem 1.2rem .5rem;min-height:236px}
.xc .ico{width:100%;height:96px;margin:1.6rem 0 .4rem;transition:transform .5s var(--ease)}
.xc .tag{position:absolute;top:.9rem;left:1rem;font-size:.68rem;letter-spacing:.1em;text-transform:uppercase;padding:.2rem .6rem;border-radius:999px;background:rgba(95,187,136,.16);color:var(--green-l);border:1px solid rgba(95,187,136,.35)}
.xc .tag.red{background:rgba(224,73,91,.16);color:#f1a0aa;border-color:rgba(224,73,91,.4)}
.xc .tag.dim{background:rgba(244,236,220,.08);color:var(--muted);border-color:var(--line)}
.xc h4{margin:.2rem 0 0;font-size:1.12rem}
.xc p{margin:0;color:var(--muted);font-size:.86rem;line-height:1.45}
.xc .meta{margin-top:.2rem;font-size:.78rem;color:#cfd8cd}
[class*="st-key-card_"]{position:relative;border-radius:18px;border:1px solid var(--line);background:var(--panel);backdrop-filter:blur(8px);
  transition:transform .4s var(--ease),border-color .3s,box-shadow .4s var(--ease);animation:pop .7s var(--ease) both;overflow:hidden}
[class*="st-key-card_"]:hover{transform:translateY(-6px);border-color:rgba(95,187,136,.6);box-shadow:0 22px 44px rgba(0,0,0,.42),0 0 0 1px rgba(95,187,136,.2)}
[class*="st-key-card_"]:hover .ico{transform:translateY(-3px) scale(1.05) rotate(-1.5deg)}
.st-key-card_zip{border-color:rgba(196,40,59,.5);background:linear-gradient(120deg,rgba(143,27,43,.42),rgba(18,44,31,.78) 70%)}
.st-key-card_zip:hover{border-color:rgba(224,73,91,.85);box-shadow:0 24px 50px rgba(0,0,0,.45),0 0 0 1px rgba(224,73,91,.35)}
.st-key-card_tile{animation-delay:.05s}.st-key-card_main{animation-delay:.1s}.st-key-card_cap{animation-delay:.15s}.st-key-card_assembly{animation-delay:.2s}
[class*="st-key-card_"] [data-testid="stDownloadButton"],[class*="st-key-card_"] .stButton,[class*="st-key-card_"] [data-testid="stElementContainer"]{position:static}
[class*="st-key-card_"] [data-testid="stElementContainer"],[class*="st-key-card_"] [data-testid="stDownloadButton"]{width:100% !important;padding:0 1.2rem 1.1rem}
[class*="st-key-card_"] [data-testid="stElementContainer"]:first-child{padding:0}
[class*="st-key-card_"] [data-testid="stDownloadButton"] button{position:static !important;width:100%;justify-content:center;padding:.6rem 1rem;font-weight:600;border:0;color:#fff;
  background:linear-gradient(145deg,var(--green),var(--green-d));box-shadow:0 6px 16px rgba(27,90,58,.5)}
[class*="st-key-card_"] [data-testid="stDownloadButton"] button:hover{background:linear-gradient(145deg,#3aa56c,var(--green-d));border:0}
.st-key-card_zip [data-testid="stDownloadButton"] button{background:linear-gradient(135deg,var(--red-l),var(--red) 50%,var(--red-d));box-shadow:0 8px 20px rgba(196,40,59,.45)}
.st-key-card_zip [data-testid="stDownloadButton"] button:hover{background:linear-gradient(135deg,#ee5a6c,var(--red) 50%,var(--red-d))}
.st-key-card_zip .xc{flex-direction:row;align-items:center;gap:1.8rem;min-height:150px;padding-top:2.8rem}
.st-key-card_zip .xc .ico{width:150px;flex:none;height:112px;margin:0}
.locked{padding:0 1.2rem 1rem;font-size:.8rem;color:var(--muted);font-style:italic}
.checks{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:.5rem 1.4rem;margin:.4rem 0 1.2rem}
.check{position:relative;padding-left:1.7rem;font-size:.9rem;color:var(--cream);animation:slide .5s var(--ease) both}
.check::before{content:"";position:absolute;left:.15rem;top:.3rem;width:.72rem;height:.38rem;border-left:2.5px solid var(--green-l);border-bottom:2.5px solid var(--green-l);transform:rotate(-45deg)}
.check.bad::before{border-color:var(--red-l)}
.check small{color:var(--muted)}
@keyframes slide{from{opacity:0;transform:translateX(-10px)}to{opacity:1;transform:none}}
.notice{border-radius:14px;padding:.8rem 1.1rem;margin:.6rem 0 1rem;border:1px solid rgba(230,207,148,.4);background:rgba(230,207,148,.08);color:var(--cream);animation:pop .5s var(--ease) both}

/* ---------- guide ---------- */
.gtable{width:100%;border-collapse:collapse;font-size:.92rem}
.gtable td{padding:.6rem .4rem;border-bottom:1px solid var(--line);vertical-align:top;color:var(--cream)}
.gtable td:first-child{width:28%;font-weight:600;color:var(--green-l)}
.fit{display:flex;gap:1rem;flex-wrap:wrap;margin:.6rem 0}
.fitcard{flex:1 1 220px;border-radius:14px;padding:.8rem 1rem;border:1px solid var(--line);background:var(--panel);animation:pop .6s var(--ease) both}
.fitcard.ok{border-color:rgba(95,187,136,.55)}.fitcard.no{border-color:rgba(224,73,91,.6)}
.fitcard b{font-family:var(--serif)}
.fitcard em{display:block;font-style:normal;font-size:.8rem;color:var(--muted);margin-top:.15rem}
.fitcard strong{font-size:.72rem;letter-spacing:.1em;text-transform:uppercase}
.fitcard.ok strong{color:var(--green-l)}.fitcard.no strong{color:var(--red-l)}
.legend{height:12px;border-radius:999px;background:linear-gradient(90deg,#fff,#000);border:1px solid var(--line);margin:.4rem 0 .2rem}
.legend-labels{display:flex;justify-content:space-between;font-size:.8rem;color:var(--muted)}
[data-testid="stImage"] img{border-radius:14px;border:1px solid var(--line);animation:fade .8s var(--ease) both}

@media (prefers-reduced-motion:reduce){*,*::before,*::after{animation:none !important;transition:none !important}}
@media (max-width:900px){.st-key-nav [data-testid="stButtonGroup"] [role="radiogroup"],.st-key-nav [data-testid="stButtonGroup"]>div:not([data-testid]){flex-wrap:wrap !important}.st-key-nav [data-testid="stButtonGroup"] button{font-size:.95rem;padding:.55rem .9rem}.hero h1{font-size:1.8rem}.stats{grid-template-columns:repeat(2,1fr)}.st-key-card_zip .xc{flex-direction:column;align-items:flex-start}.st-key-nav [data-testid="stButtonGroup"] button:last-child{margin-left:0}.stApp::after{opacity:.25}}
"""

BACKDROP_HTML = '<div class="xm-snow"></div><div class="xm-snow2"></div><div class="xm-hearth"></div>'

HERO_HTML = """
<div class="hero">
  <div class="garland"><div class="lights a"></div><div class="lights b"></div></div>
  <h1>Custom Christmas Lithophane Generator</h1>
  <p>Upload a photo and export STL files for a hollow ornament with your picture wrapped around the whole ball.
  Put an LED tea light inside and the photo appears in the walls.</p>
</div>
"""


def inject_theme() -> None:
    css = (CSS.replace("__TREE__", _uri(tree_svg())).replace("__GARLAND__", _uri(garland_tile()))
              .replace("__LIGHTS0__", _uri(lights_tile(0))).replace("__LIGHTS1__", _uri(lights_tile(1)))
              .replace("__SNOW1__", _uri(snow_tile(320, 34, 3))).replace("__SNOW2__", _uri(snow_tile(520, 26, 9))))
    st.markdown(f"<style>{css}</style>{BACKDROP_HTML}", unsafe_allow_html=True)


def hero() -> None:
    st.markdown(HERO_HTML, unsafe_allow_html=True)
