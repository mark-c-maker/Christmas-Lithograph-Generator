"""Interactive Plotly preview and image/seam previews."""
from __future__ import annotations

import math
from typing import Tuple

import numpy as np
import plotly.graph_objects as go
from PIL import Image, ImageDraw

from engine import GenerationResult
from image_processor import PreparedMap

# Warm-white LED seen through PLA: dark where the wall is thick, ivory where it is thin.
GLOW = [[0.0, "#060908"], [0.22, "#2b2417"], [0.5, "#8d7646"], [0.78, "#e3cf9b"], [1.0, "#fff8e6"]]
DAY = [[0.0, "#59605b"], [0.5, "#a9aea6"], [1.0, "#f4efe3"]]

VIEWS = {
    "Front": (2.0, 0.0, 0.25),
    "Angle": (1.45, 1.35, 0.95),
    "Top": (0.02, 0.0, 2.45),
    "Bottom": (0.02, 0.0, -2.45),
}
STAGE = {"LED on": "#07110c", "Daylight": "#eef0ec"}


def preview_arrays(r: GenerationResult) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    m = r.assembly()
    t = np.clip(np.linalg.norm(m.vertices, axis=1) - r.derived.r_in, 0.0, r.derived.t_max)
    return m.vertices.astype(np.float32), m.faces.astype(np.int32), t.astype(np.float32)


def make_figure(verts, faces, thickness, t_min: float, t_max: float,
                lighting: str = "LED on", section: str = "Whole", view: str = "Front") -> go.Figure:
    cut = section == "Cut-away"
    if cut:
        faces = faces[verts[faces].mean(axis=1)[:, 1] < 0.0]
    lit = lighting == "LED on"
    if lit:
        alpha = math.log(1 / 0.12) / max(t_max - t_min, 1e-6)
        inten = np.exp(-alpha * np.clip(thickness - t_min, 0, None))
        light, cs = dict(ambient=1.0, diffuse=0.0, specular=0.0, roughness=1.0), GLOW
    else:
        inten = 0.97 - 0.42 * np.clip((thickness - t_min) / max(t_max - t_min, 1e-6), 0, 1)
        inten = np.where(thickness < 0.05, 0.55, inten)       # inner surfaces read as shaded plastic
        light, cs = dict(ambient=0.5, diffuse=0.8, specular=0.08, roughness=0.9, fresnel=0.05), DAY
    ex, ey, ez = VIEWS.get(view, VIEWS["Front"])
    if cut:                       # turn the camera to face the open side
        ex, ey = -ey, ex
    fig = go.Figure(go.Mesh3d(
        x=verts[:, 0], y=verts[:, 1], z=verts[:, 2], i=faces[:, 0], j=faces[:, 1], k=faces[:, 2],
        intensity=inten, intensitymode="vertex", colorscale=cs, cmin=0, cmax=1,
        showscale=False, flatshading=False, lighting=light,
        lightposition=dict(x=2500, y=1500, z=3500)))
    fig.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=620,
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        uirevision=f"{view}|{section}",     # keep the user's rotation while sliders change
        scene=dict(aspectmode="data", xaxis=dict(visible=False), yaxis=dict(visible=False),
                   zaxis=dict(visible=False), bgcolor="rgba(0,0,0,0)",
                   camera=dict(up=dict(x=0, y=0, z=1), eye=dict(x=ex, y=ey, z=ez))))
    return fig


def seam_preview_image(p: PreparedMap, seam_position_deg: float, width: int = 900) -> Image.Image:
    """Equirectangular map exactly as the sphere gets it, rolled so the seam is centred."""
    e = p.wrapped.equirect(width)
    e = np.roll(e, width // 2 - int(round(((seam_position_deg % 360) / 360) * width)), axis=1)
    img = Image.fromarray((e * 255).astype(np.uint8), "L").convert("RGB")
    ImageDraw.Draw(img).line([(width // 2, 0), (width // 2, img.height)], fill=(224, 73, 91), width=2)
    return img


def tile_image(p: PreparedMap) -> Image.Image:
    return Image.fromarray((p.tile * 255).astype(np.uint8), "L")
