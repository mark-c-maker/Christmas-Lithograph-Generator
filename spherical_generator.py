"""Custom Christmas Lithophane Generator - true spherical lithophane geometry.

Every part is built as a surface of revolution whose profile may vary with
longitude (that is how the lithophane relief, thread helix and LED vent slots
are expressed). Each part is one closed profile swept 360 degrees, so the
meshes are closed and manifold by construction. Only the hanging-loop eyelet
needs a boolean union (manifold3d).

Coordinates: millimetres, +Z up, sphere centre at the origin, assembled
orientation. The photo's centre faces +X; longitude increases toward +Y.
"""
from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass
from typing import Callable, Optional

import numpy as np
import trimesh

from image_processor import WrappedMap
from settings import (Derived, OrnamentSettings, Quality, QUALITY_RESOLUTION_MM,
                      grid_columns)


class GenerationError(RuntimeError):
    """Geometry problem phrased for an ordinary user."""


ProgressCB = Callable[[float, str], None]


def _smoothstep(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


# ---------------------------------------------------------------------------
# Brightness -> thickness
# ---------------------------------------------------------------------------
class ThicknessField:
    def __init__(self, wmap: WrappedMap, d: Derived, gamma: float, lon_shift: float = 0.0):
        self.wmap, self.d, self.gamma, self.lon_shift = wmap, d, gamma, lon_shift

    def thickness(self, lon_deg, lat_deg):
        d = self.d
        g = self.wmap.sample(np.asarray(lon_deg) - self.lon_shift, lat_deg)
        if self.gamma != 1.0:
            g = g ** self.gamma
        t = d.t_max - (d.t_max - d.t_min) * g            # black = thick, white = thin
        w = _smoothstep((np.abs(lat_deg) - d.phi_fade0) / (d.phi_boss - d.phi_fade0))
        return t + w * (d.t_pole - t)                     # flat, strong shell near the poles


@dataclass
class BuildContext:
    s: OrnamentSettings
    d: Derived
    field: ThicknessField
    T: int
    res: float
    theta: np.ndarray
    theta_deg: np.ndarray


def make_context(wmap: WrappedMap, s: OrnamentSettings, d: Derived, quality: Quality) -> BuildContext:
    T = grid_columns(s, quality)
    theta = np.arange(T) * (2 * math.pi / T)
    return BuildContext(s, d, ThicknessField(wmap, d, s.shell.tone_gamma), T,
                        QUALITY_RESOLUTION_MM[quality], theta, np.degrees(theta))


# ---------------------------------------------------------------------------
# Profile path + revolve
# ---------------------------------------------------------------------------
class Path:
    """Open profile polyline, one (rho, z) per longitude column per row.
    First and last rows are poles (rho == 0)."""

    def __init__(self, T: int):
        self.T = T
        self.R, self.Z = [], []
        self.cur = None

    def _b(self, v):
        return np.broadcast_to(np.asarray(v, dtype=np.float64), (self.T,)).copy()

    def start(self, rho, z):
        r, zz = self._b(rho), self._b(z)
        self.R.append(r[None]); self.Z.append(zz[None]); self.cur = (r, zz)

    def line_to(self, rho, z, step: float):
        r, zz = self._b(rho), self._b(z)
        r0, z0 = self.cur
        length = float(np.max(np.hypot(r - r0, zz - z0)))
        if length < 1e-9:
            return
        n = max(1, int(math.ceil(length / step)))
        s = np.linspace(0, 1, n + 1)[1:, None]
        self.R.append(r0 + s * (r - r0)); self.Z.append(z0 + s * (zz - z0))
        self.cur = (r, zz)

    def rows(self, R2, Z2):
        self.R.append(R2); self.Z.append(Z2)
        self.cur = (R2[-1].copy(), Z2[-1].copy())

    def arc(self, radius: float, b0: float, b1: float, step_deg: float = 3.0):
        """Points on a sphere of `radius`, polar angle b (from +Z) from b0 to b1, excluding b0."""
        n = max(1, int(math.ceil(abs(b1 - b0) / math.radians(step_deg))))
        b = np.linspace(b0, b1, n + 1)[1:]
        rho, z = radius * np.sin(b), radius * np.cos(b)
        if abs(rho[-1]) < 1e-9:
            rho[-1] = 0.0
        ones = np.ones((1, self.T))
        self.rows(rho[:, None] * ones, z[:, None] * ones)

    def arrays(self):
        return np.concatenate(self.R), np.concatenate(self.Z)


def revolve(rho: np.ndarray, z: np.ndarray, theta: np.ndarray) -> trimesh.Trimesh:
    n_rows, T = rho.shape
    pole = rho.max(axis=1) < 1e-9
    if pole[1:-1].any():
        raise GenerationError("Internal error: profile touches the axis mid-way.")
    verts, idx, n = [], [], 0
    for r in range(n_rows):
        if pole[r]:
            verts.append(np.array([[0.0, 0.0, z[r, 0]]]))
            idx.append(np.full(T, n)); n += 1
        else:
            verts.append(np.stack([rho[r] * np.cos(theta), rho[r] * np.sin(theta), z[r]], axis=1))
            idx.append(np.arange(n, n + T)); n += T
    faces = []
    for r in range(n_rows - 1):
        a, b = idx[r], idx[r + 1]
        a1, b1 = np.roll(a, -1), np.roll(b, -1)
        if pole[r]:
            faces.append(np.stack([a, b, b1], 1))
        elif pole[r + 1]:
            faces.append(np.stack([a, b, a1], 1))
        else:
            faces.append(np.stack([a, b, b1], 1))
            faces.append(np.stack([a, b1, a1], 1))
    mesh = trimesh.Trimesh(np.concatenate(verts), np.concatenate(faces), process=False)
    if mesh.volume < 0:
        mesh.invert()
    return mesh


# ---------------------------------------------------------------------------
# Thread (shared by cap collar and body sleeve so they always match)
# ---------------------------------------------------------------------------
_LEAD = 1.2


def _wave(x):
    x = np.mod(x, 1.0)
    return np.where(x < 0.1, 0.0,
           np.where(x < 0.5, (x - 0.1) / 0.4,
           np.where(x < 0.6, 1.0, (1.0 - x) / 0.4)))        # 45 degree flanks


def _phase(ctx: BuildContext, zp):
    return zp / ctx.s.joint.thread_pitch_mm - ctx.theta[None, :] / (2 * math.pi)


def male_rho(ctx: BuildContext, zp):
    d, j = ctx.d, ctx.s.joint
    ramp = np.clip((d.thread_len - zp) / _LEAD, 0, 1)         # lead-in taper at the tip
    return d.r_root + j.thread_depth_mm * _wave(_phase(ctx, zp)) * ramp


def female_rho(ctx: BuildContext, zp):
    d, j = ctx.d, ctx.s.joint
    ramp = np.clip(zp / _LEAD, 0, 1)                           # wide mouth
    return d.r_fm - j.thread_depth_mm * (1.0 - _wave(_phase(ctx, zp))) * ramp


def _thread_rows(ctx: BuildContext):
    L = ctx.d.thread_len
    nz = int(math.ceil(L / (ctx.s.joint.thread_pitch_mm / 16)))
    return np.linspace(0.0, L, nz + 1)[:, None]


# ---------------------------------------------------------------------------
# Outer lithophane rows + rim solution
# ---------------------------------------------------------------------------
@dataclass
class Rim:
    phi: np.ndarray    # radians, per column, latitude where outer surface meets plane z0
    rho: np.ndarray    # outer radius at that point


def solve_rim(ctx: BuildContext) -> Rim:
    d = ctx.d
    phi = np.full(ctx.T, math.asin(d.z0 / (d.r_in + d.t_pole)))
    for _ in range(8):
        t = ctx.field.thickness(ctx.theta_deg, np.degrees(phi))
        phi = np.arcsin(np.clip(d.z0 / (d.r_in + t), -1, 1))
    t = ctx.field.thickness(ctx.theta_deg, np.degrees(phi))
    ro = d.r_in + t
    return Rim(phi, np.sqrt(ro ** 2 - d.z0 ** 2))


def _outer_rows(ctx: BuildContext, phi_start, phi_end: np.ndarray, rim: Rim, side: str):
    d = ctx.d
    span = float(np.max(np.abs(phi_end - phi_start)))
    n = max(8, int(math.ceil(span * d.r_out / ctx.res)))
    s = np.linspace(0, 1, n + 1)[:, None]
    phi = phi_start + s * (phi_end[None, :] - phi_start)
    lon = np.broadcast_to(ctx.theta_deg[None, :], phi.shape)
    t = ctx.field.thickness(lon.ravel(), np.degrees(phi).ravel()).reshape(phi.shape)
    ro = d.r_in + t
    rho, z = ro * np.cos(phi), ro * np.sin(phi)
    # A sharp edge in the picture at the split line can push a point across the flat split plane.
    # Keep the ball above it and the cap below it, at the same radius, so the rim stays flat.
    z_c = np.maximum(z, d.z0) if side == "body" else np.minimum(z, d.z0)
    rho = np.sqrt(np.maximum(ro ** 2 - z_c ** 2, 0.0))
    z = z_c
    rho[-1], z[-1] = rim.rho, d.z0                         # exactly planar rim
    return rho, z, t


# ---------------------------------------------------------------------------
# Main body
# ---------------------------------------------------------------------------
def build_body(ctx: BuildContext, rim: Rim) -> tuple:
    d, s = ctx.d, ctx.s
    path = Path(ctx.T)
    phi0 = math.radians(d.phi_boss)
    rho, z, t = _outer_rows(ctx, phi0, rim.phi, rim, "body")
    if s.loop.enabled:
        path.start(0.0, d.z_boss_top)
        path.line_to(d.r_boss_top, d.z_boss_top, step=d.r_boss_top / 3)
        path.line_to(rho[0], z[0], step=1.0)               # conical neck down to the shell
    else:
        path.start(0.0, d.r_pole)
        path.line_to(rho[0], z[0], step=100.0)
    path.rows(rho[1:], z[1:])
    path.line_to(d.r_fm, d.z0, step=1.0)                   # flat bottom face (mates with cap flange)
    zp = _thread_rows(ctx)[1:]
    Rf = female_rho(ctx, zp)
    path.rows(Rf, d.z0 + zp + 0 * Rf)                      # internal thread
    path.line_to(d.r_so, d.z0 + d.thread_len, step=0.6)    # sleeve top
    path.line_to(d.r_so, d.z_floor, step=1.0)              # sleeve outside
    path.line_to(d.rho_floor, d.z_floor, step=1.0)
    path.arc(d.r_in, math.acos(d.z_floor / d.r_in), 0.0)   # smooth constant inner sphere
    R, Z = path.arrays()
    return revolve(R, Z, ctx.theta), float(t.min()), float(t.max())


# ---------------------------------------------------------------------------
# Bottom cap (dome continues the lithophane) with collar, plate and LED cradle
# ---------------------------------------------------------------------------
def _vent_mask(ctx: BuildContext) -> np.ndarray:
    led = ctx.s.led
    mask = np.zeros(ctx.T, dtype=bool)
    if led.vent_count <= 0:
        return mask
    ang = ctx.theta_deg
    for k in range(led.vent_count):
        c = 360.0 / led.vent_count * k + 90.0
        dist = np.abs(((ang - c + 180.0) % 360.0) - 180.0)
        mask |= dist <= led.vent_width_deg / 2
    return mask


def build_cap(ctx: BuildContext, rim: Rim) -> tuple:
    d, s = ctx.d, ctx.s
    T = ctx.T
    path = Path(T)
    path.start(0.0, -d.r_pole)
    phi_s = -math.acos(1.0 / d.r_pole)
    rho, z, t = _outer_rows(ctx, phi_s, rim.phi, rim, "cap")
    path.line_to(rho[0], z[0], step=100.0)
    path.rows(rho[1:], z[1:])
    zp_all = _thread_rows(ctx)
    path.line_to(male_rho(ctx, zp_all[:1])[0], d.z0, step=1.0)    # flange face
    zp = zp_all[1:]
    Rm = male_rho(ctx, zp)
    path.rows(Rm, d.z0 + zp + 0 * Rm)                             # external thread
    path.line_to(d.r_ci, d.z0 + d.thread_len, step=0.6)           # collar tip
    path.line_to(d.r_ci, d.z_plate, step=1.0)                     # collar inside
    path.line_to(d.rho_plate, d.z_plate, step=1.0)                # plate underside
    b_plate = math.acos(d.z_plate / d.r_in)
    b_cr_out = math.pi - math.asin(d.cr_out / d.r_in)
    b_cr_in = math.pi - math.asin(d.cr_in / d.r_in)
    path.arc(d.r_in, b_plate, b_cr_out)
    cradle_h = d.z_tip - d.r_in * math.cos(b_cr_out)
    depth = min(s.led.vent_depth_mm, 0.6 * cradle_h)
    z_tip = d.z_tip - depth * _vent_mask(ctx)
    path.line_to(d.cr_out, z_tip, step=1.0)                       # LED cradle ring (outside)
    path.line_to(d.cr_in, z_tip, step=0.6)
    path.line_to(d.cr_in, d.r_in * math.cos(b_cr_in), step=1.0)   # (inside)
    path.arc(d.r_in, b_cr_in, math.pi)
    R, Z = path.arrays()
    return revolve(R, Z, ctx.theta), float(t.min()), float(t.max())


# ---------------------------------------------------------------------------
# Hanging loop (eyelet) - the only boolean
# ---------------------------------------------------------------------------
def make_eyelet(d: Derived, s: OrnamentSettings) -> trimesh.Trimesh:
    lp = s.loop
    minor = lp.tube_diameter_mm / 2
    major = lp.hole_diameter_mm / 2 + minor
    zc = d.z_boss_top + major                       # tube bottom sits half-buried in the neck
    nu, nv = 120, 28
    u = np.linspace(0, 2 * math.pi, nu, endpoint=False)[:, None]
    v = np.linspace(0, 2 * math.pi, nv, endpoint=False)[None, :]
    rr = major + minor * np.cos(v)
    verts = np.stack([rr * np.cos(u), minor * np.sin(v) * np.ones_like(u), rr * np.sin(u) + zc], -1).reshape(-1, 3)
    idx = np.arange(nu * nv).reshape(nu, nv)
    b, dd = np.roll(idx, -1, 0), np.roll(idx, -1, 1)
    c = np.roll(b, -1, 1)
    faces = np.concatenate([np.stack([idx, b, c], -1).reshape(-1, 3), np.stack([idx, c, dd], -1).reshape(-1, 3)])
    m = trimesh.Trimesh(verts, faces, process=False)
    if m.volume < 0:
        m.invert()
    return m


def merge_loop(body: trimesh.Trimesh, d: Derived, s: OrnamentSettings) -> trimesh.Trimesh:
    try:
        out = trimesh.boolean.union([body, make_eyelet(d, s)], engine="manifold")
    except Exception as exc:  # noqa: BLE001 - surface any backend failure clearly
        raise GenerationError(
            "The hanging loop could not be merged into the ball. Make sure the 'manifold3d' package "
            f"is installed (pip install manifold3d). Details: {exc}") from exc
    if len(out.faces) == 0:
        raise GenerationError("Merging the hanging loop produced an empty model.")
    return out


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------
@dataclass
class OrnamentMeshes:
    body: trimesh.Trimesh
    cap: trimesh.Trimesh
    t_min_actual: float
    t_max_actual: float


def build_ornament(wmap: WrappedMap, s: OrnamentSettings, d: Derived, quality: Quality,
                   progress: Optional[ProgressCB] = None) -> OrnamentMeshes:
    cb = progress or (lambda f, m: None)
    ctx = make_context(wmap, s, d, quality)
    cb(0.25, "Solving the split line")
    rim = solve_rim(ctx)
    cb(0.35, "Building the lithophane shell")
    body, b0, b1 = build_body(ctx, rim)
    cb(0.55, "Building the bottom cap and LED cradle")
    # A printed cap stops slightly short of fully tight. Rotating the cap's picture by that angle
    # makes the cap and ball pictures line up at the snug position.
    cap_ctx = dataclasses.replace(ctx, field=ThicknessField(
        wmap, d, s.shell.tone_gamma, lon_shift=s.joint.cap_alignment_deg))
    cap, c0, c1 = build_cap(cap_ctx, solve_rim(cap_ctx))
    if s.loop.enabled:
        cb(0.70, "Merging the hanging loop")
        body = merge_loop(body, d, s)
    return OrnamentMeshes(body, cap, min(b0, c0), max(b1, c1))


def snug_cap(cap: trimesh.Trimesh, s: OrnamentSettings) -> trimesh.Trimesh:
    """The cap as it sits when screwed in until snug: turned back by the alignment angle
    and lowered by the matching thread travel."""
    a = s.joint.cap_alignment_deg
    m = cap.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(math.radians(-a), [0, 0, 1]))
    m.apply_translation([0, 0, -s.joint.thread_pitch_mm * a / 360.0])
    return m


# ---------------------------------------------------------------------------
# Flat test tile (check image quality before printing a whole ball)
# ---------------------------------------------------------------------------
def build_test_tile(gray: np.ndarray, d: Derived, gamma: float = 1.0,
                    width_mm: float = 70.0, step_mm: float = 0.5, frame_mm: float = 3.0) -> trimesh.Trimesh:
    from PIL import Image
    h0, w0 = gray.shape
    nx = int(round(width_mm / step_mm)) + 1
    ny = max(8, int(round(width_mm * h0 / w0 / step_mm)) + 1)
    g = np.asarray(Image.fromarray(np.clip(gray * 255 + .5, 0, 255).astype(np.uint8), "L")
                   .resize((nx, ny), Image.BILINEAR), dtype=np.float64) / 255.0
    g = g ** gamma
    top = d.t_max - (d.t_max - d.t_min) * g
    f = max(1, int(round(frame_mm / step_mm)))
    top[:f, :] = d.t_max; top[-f:, :] = d.t_max; top[:, :f] = d.t_max; top[:, -f:] = d.t_max
    xs, ys = np.arange(nx) * step_mm, np.arange(ny) * step_mm
    X, Y = np.meshgrid(xs, ys)
    vt = np.stack([X, Y, top], -1).reshape(-1, 3)
    vb = np.stack([X, Y, np.zeros_like(top)], -1).reshape(-1, 3)
    n = nx * ny
    vid = np.arange(n).reshape(ny, nx)
    v00, v01, v10, v11 = vid[:-1, :-1], vid[:-1, 1:], vid[1:, :-1], vid[1:, 1:]
    ft = np.concatenate([np.stack([v00, v01, v11], -1).reshape(-1, 3), np.stack([v00, v11, v10], -1).reshape(-1, 3)])
    fb = np.concatenate([np.stack([v00 + n, v11 + n, v01 + n], -1).reshape(-1, 3),
                         np.stack([v00 + n, v10 + n, v11 + n], -1).reshape(-1, 3)])
    ring = ([vid[0, j] for j in range(nx - 1)] + [vid[i, nx - 1] for i in range(ny - 1)] +
            [vid[ny - 1, j] for j in range(nx - 1, 0, -1)] + [vid[i, 0] for i in range(ny - 1, 0, -1)])
    sides = []
    for k, p in enumerate(ring):
        q = ring[(k + 1) % len(ring)]
        sides.append([q, p, p + n]); sides.append([q, p + n, q + n])
    faces = np.concatenate([ft, fb, np.array(sides)])
    m = trimesh.Trimesh(np.concatenate([vt, vb]), faces, process=False)
    if m.volume < 0:
        m.invert()
    return m
