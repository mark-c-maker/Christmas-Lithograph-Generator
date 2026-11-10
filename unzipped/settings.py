"""Custom Christmas Lithophane Generator - configuration objects.

Pure data + geometry-derivation. No UI, no image or mesh code, so the same
objects can be sent as JSON from a future website to the generation engine.
"""
from __future__ import annotations

import copy
import dataclasses
import math
import typing
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict


class SettingsError(ValueError):
    """A configuration problem phrased so it can be shown to an ordinary user."""


class WrapMode(str, Enum):
    FULL_SPHERE = "full_sphere"          # stretch a 2:1 crop over 360 x 180 degrees
    PRESERVE_ASPECT = "preserve_aspect"  # keep proportions, repeat N times around


class Preset(str, Enum):
    PHOTO = "photo"
    HIGH_CONTRAST = "high_contrast"
    SILHOUETTE = "silhouette"


class Quality(str, Enum):
    PREVIEW = "preview"
    DRAFT = "draft"
    STANDARD = "standard"
    HIGH = "high"


# Target surface sampling step at the equator (mm). Smaller = more detail, bigger STL.
QUALITY_RESOLUTION_MM = {
    Quality.PREVIEW: 1.3,
    Quality.DRAFT: 0.9,
    Quality.STANDARD: 0.6,
    Quality.HIGH: 0.4,
}


@dataclass
class ImageSettings:
    preset: Preset = Preset.PHOTO
    grayscale_method: str = "luminosity"   # luminosity | average | red | green | blue
    brightness: float = 1.0                # multiplier on top of the preset
    contrast: float = 1.0
    sharpness: float = 1.0
    smoothing_px: float = 0.0              # extra Gaussian blur, in grid cells
    invert: bool = False
    rotation_deg: float = 0.0
    zoom: float = 1.0                      # 1 = largest crop that fits
    pan_x: float = 0.0                     # -1..1 inside the available slack
    pan_y: float = 0.0


@dataclass
class WrapSettings:
    mode: WrapMode = WrapMode.FULL_SPHERE
    copies: int = 1                        # PRESERVE_ASPECT only: 1-4 repeats around
    mirror: bool = False                   # alternate copies mirrored (even copies only)
    seam_position_deg: float = 180.0       # longitude where image edges meet (0 = front)
    seam_blend: float = 0.12               # cross-fade width, fraction of image width
    polar_fade_deg: float = 20.0           # PRESERVE_ASPECT: fade to flat tone toward poles


@dataclass
class ShellSettings:
    diameter_mm: float = 100.0             # maximum outer diameter (black pixels)
    min_wall_mm: float = 1.0               # white
    max_wall_mm: float = 3.0               # black
    tone_gamma: float = 1.0                # 1 = linear brightness -> thickness


@dataclass
class LoopSettings:
    enabled: bool = True
    hole_diameter_mm: float = 8.0
    tube_diameter_mm: float = 4.0
    boss_radius_mm: float = 7.0            # neck that blends the loop into the shell


@dataclass
class LedSettings:
    diameter_mm: float = 38.0              # common LED tea light
    height_mm: float = 13.0                # informational (printing guide)
    clearance_mm: float = 0.8              # radial gap inside the cradle ring
    cradle_wall_mm: float = 1.6
    vent_count: int = 3
    vent_width_deg: float = 30.0
    vent_depth_mm: float = 6.0


@dataclass
class JointSettings:
    opening_lat_deg: float = 40.0          # latitude (south) where body and cap split
    thread_pitch_mm: float = 2.5
    thread_depth_mm: float = 1.0
    thread_length_mm: float = 8.0
    thread_clearance_mm: float = 0.35      # radial gap between male and female thread
    sleeve_wall_mm: float = 2.0
    collar_wall_mm: float = 1.6
    plate_mm: float = 2.4
    floor_mm: float = 2.0


@dataclass
class OrnamentSettings:
    image: ImageSettings = field(default_factory=ImageSettings)
    wrap: WrapSettings = field(default_factory=WrapSettings)
    shell: ShellSettings = field(default_factory=ShellSettings)
    loop: LoopSettings = field(default_factory=LoopSettings)
    led: LedSettings = field(default_factory=LedSettings)
    joint: JointSettings = field(default_factory=JointSettings)
    quality: Quality = Quality.STANDARD

    # -- (de)serialisation, for API use ---------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return _plain(dataclasses.asdict(self))

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OrnamentSettings":
        try:
            return _build(cls, data or {})
        except (ValueError, TypeError) as exc:
            raise SettingsError(f"Invalid settings: {exc}") from exc

    # -- validation -------------------------------------------------------
    def validate(self) -> "Derived":
        """Raise SettingsError with a plain-language message, else return geometry."""
        _range("Ball diameter", self.shell.diameter_mm, 60, 250, "mm")
        _range("Minimum wall", self.shell.min_wall_mm, 0.4, 5, "mm")
        _range("Maximum wall", self.shell.max_wall_mm, 0.6, 8, "mm")
        if self.shell.max_wall_mm <= self.shell.min_wall_mm + 0.1:
            raise SettingsError("Maximum wall thickness must be larger than the minimum wall thickness.")
        _range("Tone gamma", self.shell.tone_gamma, 0.3, 3.0)
        _range("Zoom", self.image.zoom, 1.0, 6.0)
        _range("Horizontal position", self.image.pan_x, -1, 1)
        _range("Vertical position", self.image.pan_y, -1, 1)
        _range("Rotation", self.image.rotation_deg, -180, 180, "degrees")
        _range("Brightness", self.image.brightness, 0.2, 3.0)
        _range("Contrast", self.image.contrast, 0.2, 3.0)
        _range("Sharpness", self.image.sharpness, 0.0, 4.0)
        _range("Smoothing", self.image.smoothing_px, 0.0, 6.0)
        _range("Seam blend", self.wrap.seam_blend, 0.0, 0.4)
        _range("Image repeats", self.wrap.copies, 1, 4)
        _range("Opening latitude", self.joint.opening_lat_deg, 25, 50, "degrees")
        _range("Thread clearance", self.joint.thread_clearance_mm, 0.1, 1.0, "mm")
        _range("LED diameter", self.led.diameter_mm, 15, 80, "mm")
        _range("Vent count", self.led.vent_count, 0, 8)
        if self.image.grayscale_method not in ("luminosity", "average", "red", "green", "blue"):
            raise SettingsError("Unknown grayscale method.")
        d = _compute(self)
        if d.r_ci - 0.8 < d.cr_out or d.rho_plate - 0.5 < d.cr_out:
            need = min_diameter_for_led(self)
            hint = (f" Increase the ball diameter to about {need:.0f} mm or more, or choose a smaller LED."
                    if need else " Choose a smaller LED.")
            raise SettingsError(
                f"A {self.led.diameter_mm:.0f} mm LED does not fit through the cap of a "
                f"{self.shell.diameter_mm:.0f} mm ball.{hint}")
        return d


@dataclass(frozen=True)
class Derived:
    """All radii / heights (mm) the generator needs, derived from settings."""
    r_out: float
    r_in: float
    t_min: float
    t_max: float
    t_pole: float
    r_pole: float
    z0: float            # flat split plane (negative: below sphere centre)
    rho_i0: float
    r_so: float          # sleeve outer radius
    r_fm: float          # female thread major radius (groove bottom)
    r_cc: float          # male thread crest radius
    r_root: float        # male thread root radius
    r_ci: float          # collar inner radius
    thread_len: float
    z_floor: float
    rho_floor: float
    z_plate: float
    rho_plate: float
    z_tip: float
    cr_in: float
    cr_out: float
    boss_r0: float
    phi_boss: float      # degrees; thickness is flat (t_pole) above this latitude
    phi_fade0: float
    z_boss_top: float
    r_boss_top: float
    flange_overhang: float


def _compute(s: OrnamentSettings) -> Derived:
    sh, j, lp, led = s.shell, s.joint, s.loop, s.led
    r_out = sh.diameter_mm / 2
    r_in = r_out - sh.max_wall_mm
    t_pole = (sh.min_wall_mm + sh.max_wall_mm) / 2
    r_pole = r_in + t_pole
    z0 = -r_out * math.sin(math.radians(j.opening_lat_deg))
    if r_in <= abs(z0) + 8:
        raise SettingsError("The bottom opening is too large for this ball. Lower the opening latitude or enlarge the ball.")
    rho_i0 = math.sqrt(r_in ** 2 - z0 ** 2)
    r_so = rho_i0 - 1.2
    r_fm = r_so - j.sleeve_wall_mm
    r_cc = r_fm - j.thread_clearance_mm
    r_root = r_cc - j.thread_depth_mm
    r_ci = r_root - j.collar_wall_mm
    if r_ci < 8:
        raise SettingsError("The ball is too small for the cap thread. Increase the diameter.")
    z_floor = z0 + j.floor_mm
    z_plate = z0 - j.plate_mm
    if abs(z_plate) >= r_in - 5:
        raise SettingsError("The cap plate does not fit inside the ball. Reduce the plate thickness or opening latitude.")
    rho_ro_min = math.sqrt((r_in + sh.min_wall_mm) ** 2 - z0 ** 2)
    if rho_ro_min - r_fm < 2.0:
        raise SettingsError("Not enough wall at the bottom opening to hold the cap. Increase the ball diameter or reduce the opening latitude.")
    boss_r0 = lp.boss_radius_mm if lp.enabled else 1.0
    if lp.enabled and not (4.5 <= boss_r0 <= 0.4 * r_out):
        raise SettingsError("The loop neck radius must be between 4.5 mm and 40% of the ball radius.")
    if lp.enabled and (lp.tube_diameter_mm < 2.5 or lp.hole_diameter_mm < 4):
        raise SettingsError("The hanging loop would be too thin or too small. Use a tube of at least 2.5 mm and a hole of at least 4 mm.")
    phi_boss = math.degrees(math.acos(boss_r0 / r_pole))
    cr_in = led.diameter_mm / 2 + led.clearance_mm
    return Derived(
        r_out=r_out, r_in=r_in, t_min=sh.min_wall_mm, t_max=sh.max_wall_mm,
        t_pole=t_pole, r_pole=r_pole, z0=z0, rho_i0=rho_i0, r_so=r_so, r_fm=r_fm,
        r_cc=r_cc, r_root=r_root, r_ci=r_ci, thread_len=j.thread_length_mm,
        z_floor=z_floor, rho_floor=math.sqrt(r_in ** 2 - z_floor ** 2),
        z_plate=z_plate, rho_plate=math.sqrt(r_in ** 2 - z_plate ** 2),
        z_tip=z0 + j.thread_length_mm, cr_in=cr_in, cr_out=cr_in + led.cradle_wall_mm,
        boss_r0=boss_r0, phi_boss=phi_boss, phi_fade0=phi_boss - 14.0,
        z_boss_top=r_pole + 4.0, r_boss_top=max(2.5, boss_r0 - 3.0),
        flange_overhang=math.sqrt(r_out ** 2 - z0 ** 2) - r_cc,
    )


def derive(s: OrnamentSettings) -> Derived:
    return s.validate()


def min_diameter_for_led(s: OrnamentSettings):
    t = copy.deepcopy(s)
    for dia in range(60, 301):
        t.shell.diameter_mm = float(dia)
        try:
            d = _compute(t)
        except SettingsError:
            continue
        if d.r_ci - 0.8 >= d.cr_out and d.rho_plate - 0.5 >= d.cr_out:
            return float(dia)
    return None


def grid_columns(s: OrnamentSettings, quality: Quality) -> int:
    """Number of longitude samples (multiple of 4)."""
    res = QUALITY_RESOLUTION_MM[quality]
    n = math.ceil(2 * math.pi * (s.shell.diameter_mm / 2) / res)
    n = int(math.ceil(n / 4) * 4)
    return max(160, min(n, 2400))


# ---------------------------------------------------------------------------
def _range(name: str, v: float, lo: float, hi: float, unit: str = "") -> None:
    if not (lo <= v <= hi):
        u = f" {unit}" if unit else ""
        raise SettingsError(f"{name} must be between {lo:g} and {hi:g}{u} (got {v:g}).")


def _plain(obj: Any) -> Any:
    if isinstance(obj, Enum):
        return obj.value
    if isinstance(obj, dict):
        return {k: _plain(v) for k, v in obj.items()}
    return obj


def _build(cls, data: Dict[str, Any]):
    hints = typing.get_type_hints(cls)
    kwargs = {}
    for f in dataclasses.fields(cls):
        if f.name not in data:
            continue
        v, t = data[f.name], hints[f.name]
        if dataclasses.is_dataclass(t):
            v = _build(t, v)
        elif isinstance(t, type) and issubclass(t, Enum):
            v = t(v)
        kwargs[f.name] = v
    return cls(**kwargs)
