"""Custom Christmas Lithophane Generator - image loading, tone processing and spherical sampling.

No mesh code and no UI code in here.
"""
from __future__ import annotations

import io
import math
from dataclasses import dataclass
from typing import Union

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps, ImageDraw, ImageFont, UnidentifiedImageError

from settings import ImageSettings, OrnamentSettings, Preset, WrapMode

MAX_UPLOAD_BYTES = 25 * 1024 * 1024
MAX_PIXELS = 80_000_000
MIN_SIDE = 64
SUPPORTED_FORMATS = {"PNG", "JPEG", "WEBP"}

Image.MAX_IMAGE_PIXELS = MAX_PIXELS


class ImageError(ValueError):
    """Upload problem phrased for an ordinary user."""


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------
def load_image(data: bytes) -> Image.Image:
    if not data:
        raise ImageError("No image data was received.")
    if len(data) > MAX_UPLOAD_BYTES:
        raise ImageError(f"That file is {len(data) / 1e6:.1f} MB. Please upload an image smaller than "
                         f"{MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    try:
        probe = Image.open(io.BytesIO(data))
        fmt = (probe.format or "").upper()
        if fmt not in SUPPORTED_FORMATS:
            raise ImageError("Unsupported file type. Please upload a PNG, JPG or WEBP image.")
        w, h = probe.size
        if w * h > MAX_PIXELS:
            raise ImageError(f"That image is {w}x{h} pixels, which is too large. Please resize it below "
                             f"{MAX_PIXELS // 1_000_000} megapixels.")
        probe.load()
        img = ImageOps.exif_transpose(probe)
    except ImageError:
        raise
    except (UnidentifiedImageError, OSError, ValueError, SyntaxError, EOFError,
            Image.DecompressionBombError) as exc:
        raise ImageError("That file could not be read as an image. It may be damaged, or not a real "
                         "PNG / JPG / WEBP file.") from exc
    if min(img.size) < MIN_SIDE:
        raise ImageError(f"That image is only {img.size[0]}x{img.size[1]} pixels. Please use one that is "
                         f"at least {MIN_SIDE} pixels on each side.")
    return _flatten_to_rgb(img)


def _flatten_to_rgb(img: Image.Image) -> Image.Image:
    if img.mode in ("I;16", "I;16L", "I;16B", "I", "F"):
        a = np.asarray(img, dtype=np.float64)
        span = float(a.max() - a.min())
        a = (a - a.min()) / (span if span > 0 else 1.0) * 255.0
        return Image.fromarray(a.astype(np.uint8), "L").convert("RGB")
    if img.mode in ("RGBA", "LA", "PA") or "transparency" in img.info:
        rgba = img.convert("RGBA")
        bg = Image.new("RGBA", rgba.size, (255, 255, 255, 255))  # transparent -> white -> thin wall
        bg.alpha_composite(rgba)
        return bg.convert("RGB")
    return img.convert("RGB")


def to_gray(rgb: Image.Image, method: str) -> Image.Image:
    if method == "luminosity":
        return rgb.convert("L")
    a = np.asarray(rgb, dtype=np.float64)
    if method == "average":
        g = a.mean(axis=2)
    else:
        g = a[:, :, {"red": 0, "green": 1, "blue": 2}[method]]
    return Image.fromarray(np.clip(g + 0.5, 0, 255).astype(np.uint8), "L")


# ---------------------------------------------------------------------------
# Presets / tone processing
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Recipe:
    autocontrast_cutoff: float
    contrast: float
    sharpness: float
    smoothing_px: float
    gamma: float
    sigmoid_gain: float


RECIPES = {
    Preset.PHOTO: Recipe(1.0, 1.10, 1.4, 0.5, 1.0, 0.0),
    Preset.HIGH_CONTRAST: Recipe(2.0, 1.45, 1.2, 0.5, 1.0, 5.5),
    Preset.SILHOUETTE: Recipe(0.0, 1.0, 1.0, 1.0, 1.0, 16.0),
}


def _otsu(g: np.ndarray) -> float:
    hist, _ = np.histogram(g, bins=256, range=(0, 1))
    p = hist / max(hist.sum(), 1)
    omega = np.cumsum(p)
    mu = np.cumsum(p * np.arange(256))
    mu_t = mu[-1]
    denom = omega * (1 - omega)
    denom[denom == 0] = np.nan
    sigma = (mu_t * omega - mu) ** 2 / denom
    return float(np.nanargmax(sigma)) / 255.0 if np.isfinite(sigma).any() else 0.5


def _u8(a: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(a * 255.0 + 0.5, 0, 255).astype(np.uint8), "L")


def adjust_tonal(arr: np.ndarray, s: ImageSettings) -> np.ndarray:
    rec = RECIPES[s.preset]
    im = _u8(arr)
    if rec.autocontrast_cutoff > 0:
        im = ImageOps.autocontrast(im, cutoff=rec.autocontrast_cutoff)
    im = ImageEnhance.Brightness(im).enhance(s.brightness)
    im = ImageEnhance.Contrast(im).enhance(rec.contrast * s.contrast)
    g = np.asarray(im, dtype=np.float64) / 255.0
    if rec.sigmoid_gain > 0:
        c = _otsu(g) if s.preset == Preset.SILHOUETTE else 0.5
        k = rec.sigmoid_gain
        sig = lambda x: 1.0 / (1.0 + np.exp(-k * (x - c)))
        lo, hi = sig(0.0), sig(1.0)
        g = (sig(g) - lo) / (hi - lo)
    if rec.gamma != 1.0:
        g = np.clip(g, 0, 1) ** rec.gamma
    im = _u8(g)
    sharp = rec.sharpness * s.sharpness
    if abs(sharp - 1.0) > 1e-6:
        im = ImageEnhance.Sharpness(im).enhance(sharp)
    blur = rec.smoothing_px + s.smoothing_px
    if blur > 0.05:
        im = im.filter(ImageFilter.GaussianBlur(radius=blur))
    g = np.asarray(im, dtype=np.float64) / 255.0
    return 1.0 - g if s.invert else g


def make_tileable(g: np.ndarray, blend_frac: float) -> np.ndarray:
    """Cross-fade the right edge into the left so the image wraps without a visible seam."""
    h, w = g.shape
    b = int(round(w * blend_frac))
    if b < 2:
        return g
    p = w - b
    out = g[:, :p].copy()
    x = np.arange(b) / b
    alpha = (0.5 - 0.5 * np.cos(np.pi * x))[None, :]
    out[:, :b] = alpha * g[:, :b] + (1 - alpha) * g[:, p:p + b]
    return out


# ---------------------------------------------------------------------------
# Spherical sampling
# ---------------------------------------------------------------------------
def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def _bilinear(a: np.ndarray, x: np.ndarray, y: np.ndarray, wrap_x: bool) -> np.ndarray:
    h, w = a.shape
    x = np.mod(x, w) if wrap_x else np.clip(x, 0, w - 1)
    y = np.clip(y, 0, h - 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx, fy = x - x0, y - y0
    x1 = (x0 + 1) % w if wrap_x else np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    top = a[y0, x0] * (1 - fx) + a[y0, x1] * fx
    bot = a[y1, x0] * (1 - fx) + a[y1, x1] * fx
    return top * (1 - fy) + bot * fy


class WrappedMap:
    """Maps (longitude, latitude) in degrees to a gray value in [0, 1]."""

    def __init__(self, tile: np.ndarray, mode: WrapMode, copies: int, mirror: bool,
                 seam_position_deg: float, polar_fade_deg: float, crop_aspect: float):
        self.tile = np.asarray(tile, dtype=np.float64)
        self.h, self.w = self.tile.shape
        self.mode = mode
        self.copies = copies if mode == WrapMode.PRESERVE_ASPECT else 1
        self.mirror = bool(mirror and mode == WrapMode.PRESERVE_ASPECT and self.copies % 2 == 0)
        self.seam = seam_position_deg
        self.polar_fade = polar_fade_deg
        if mode == WrapMode.FULL_SPHERE:
            self.span = 180.0
        else:
            self.span = min(180.0, (360.0 / self.copies) / crop_aspect)
        self.top_fill = float(self.tile[0].mean())
        self.bot_fill = float(self.tile[-1].mean())

    def sample(self, lon_deg, lat_deg):
        lon = np.asarray(lon_deg, dtype=np.float64)
        lat = np.asarray(lat_deg, dtype=np.float64)
        delta = 360.0 / self.copies
        x = np.mod(lon - self.seam, 360.0)
        c = np.floor(x / delta)
        u = (x - c * delta) / delta
        if self.mirror:
            u = np.where(c % 2 == 1, 1.0 - u, u)
        v = 0.5 - lat / self.span
        g = _bilinear(self.tile, u * self.w - 0.5, v * self.h - 0.5, wrap_x=not self.mirror)
        if self.span < 180.0 - 1e-6:
            d = np.abs(lat) - self.span / 2
            fade = max(1.0, min(self.polar_fade, 90.0 - self.span / 2))
            wgt = _smoothstep(d / fade)
            fill = np.where(lat > 0, self.top_fill, self.bot_fill)
            g = g + wgt * (fill - g)
        return np.clip(g, 0.0, 1.0)

    def equirect(self, width: int = 720) -> np.ndarray:
        """The full 360 x 180 map exactly as the sphere will receive it."""
        lon = (np.arange(width) + 0.5) / width * 360.0
        lat = 90.0 - (np.arange(width // 2) + 0.5) / (width // 2) * 180.0
        L, A = np.meshgrid(lon, lat)
        return self.sample(L, A)


@dataclass
class PreparedMap:
    wrapped: WrappedMap
    tile: np.ndarray
    notes: list


def _crop_box(w, h, aspect, zoom, pan_x, pan_y):
    if w / h > aspect:
        ch, cw = float(h), h * aspect
    else:
        cw, ch = float(w), w / aspect
    cw, ch = cw / zoom, ch / zoom
    cx = w / 2 + pan_x * (w - cw) / 2
    cy = h / 2 + pan_y * (h - ch) / 2
    return (cx - cw / 2, cy - ch / 2, cx + cw / 2, cy + ch / 2)


def prepare_map(image: Union[Image.Image, bytes], s: OrnamentSettings, columns: int) -> PreparedMap:
    rgb = load_image(image) if isinstance(image, (bytes, bytearray)) else _flatten_to_rgb(image)
    gray = to_gray(rgb, s.image.grayscale_method)
    notes = []
    if abs(s.image.rotation_deg) > 1e-6:
        fill = int(np.asarray(gray).mean())
        gray = gray.rotate(s.image.rotation_deg, resample=Image.BICUBIC, expand=True, fillcolor=fill)
    w, h = gray.size
    wr = s.wrap
    if wr.mode == WrapMode.FULL_SPHERE:
        n, aspect = 1, 2.0
    else:
        n = int(wr.copies)
        aspect = max(w / h, 2.0 / n)
        if w / h < 2.0 / n - 1e-9:
            notes.append("Image is tall for this many repeats; top and bottom were cropped so it fits the sphere.")
    mirror_eff = bool(wr.mirror and wr.mode == WrapMode.PRESERVE_ASPECT and n % 2 == 0)
    if wr.mirror and wr.mode == WrapMode.PRESERVE_ASPECT and n % 2 == 1:
        notes.append("Mirroring needs an even number of repeats; a cross-fade seam is used instead.")
    box = _crop_box(w, h, aspect, s.image.zoom, s.image.pan_x, s.image.pan_y)
    wt = max(64, columns // n)
    ht = max(32, int(round(wt / aspect)))
    im = gray.resize((wt, ht), Image.LANCZOS, box=box)
    g = adjust_tonal(np.asarray(im, dtype=np.float64) / 255.0, s.image)
    if not mirror_eff:
        g = make_tileable(g, wr.seam_blend)
    wm = WrappedMap(g, wr.mode, n, mirror_eff, wr.seam_position_deg, wr.polar_fade_deg, aspect)
    return PreparedMap(wrapped=wm, tile=g, notes=notes)


def sample_image(width: int = 1600) -> Image.Image:
    """Procedural demo picture so the app can be tried without an upload."""
    h = width // 2
    yy, xx = np.mgrid[0:h, 0:width]
    sky = 0.25 + 0.55 * (yy / h)
    img = Image.fromarray((sky * 255).astype(np.uint8), "L").convert("RGB")
    d = ImageDraw.Draw(img)
    rng = np.random.default_rng(7)
    for _ in range(220):
        x, y, r = rng.integers(0, width), rng.integers(0, int(h * 0.8)), int(rng.integers(2, 7))
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255))
    for cx in (width * 0.2, width * 0.5, width * 0.8):
        base = h * 0.92
        for k in range(4):
            top, half = base - (k + 1) * h * 0.16, h * (0.30 - k * 0.05)
            d.polygon([(cx, top), (cx - half, base - k * h * 0.12), (cx + half, base - k * h * 0.12)],
                      fill=(20, 20, 20))
        d.rectangle((cx - 18, base, cx + 18, h), fill=(40, 40, 40))
    d.rectangle((0, h * 0.94, width, h), fill=(235, 235, 235))
    try:
        font = ImageFont.load_default(size=max(24, width // 14))
        d.text((width // 2, h * 0.08), "Merry Christmas", fill=(10, 10, 10), anchor="mm", font=font)
    except TypeError:
        d.text((width // 2 - 60, h * 0.08), "Merry Christmas", fill=(10, 10, 10))
    return img
