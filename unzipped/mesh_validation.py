"""Custom Christmas Lithophane Generator - mesh validation. Reports problems instead of hiding them."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

import numpy as np
import trimesh

from settings import Derived


@dataclass
class ValidationReport:
    name: str
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    stats: dict = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return not self.errors

    def summary(self) -> str:
        if self.ok:
            return f"{self.name}: OK" + (f" ({len(self.warnings)} warning(s))" if self.warnings else "")
        return f"{self.name}: FAILED - " + "; ".join(self.errors)


def validate_mesh(mesh: trimesh.Trimesh, name: str, expected_euler: int,
                  max_xy_radius: Optional[float] = None) -> ValidationReport:
    r = ValidationReport(name)
    if len(mesh.faces) == 0:
        r.errors.append("The mesh is empty.")
        return r
    if not np.isfinite(mesh.vertices).all():
        r.errors.append("The mesh contains invalid (NaN/infinite) coordinates.")
        return r
    r.stats["triangles"] = int(len(mesh.faces))
    r.stats["volume_mm3"] = float(mesh.volume)
    r.stats["bounds_mm"] = mesh.bounds.round(3).tolist()
    if not mesh.is_watertight:
        r.errors.append("The mesh has holes or open edges (not watertight).")
    if not mesh.is_winding_consistent:
        r.errors.append("Some triangles face the wrong way (inconsistent winding).")
    if mesh.volume <= 0:
        r.errors.append("The mesh is inside-out (negative volume).")
    degenerate = int((mesh.area_faces < 1e-12).sum())
    r.stats["degenerate_triangles"] = degenerate
    if degenerate:
        r.errors.append(f"{degenerate} zero-area triangles found.")
    try:
        bodies = int(mesh.body_count)
    except Exception:  # noqa: BLE001
        bodies = -1
    r.stats["bodies"] = bodies
    if bodies > 1:
        r.errors.append(f"The model has {bodies} disconnected pieces (expected 1).")
    r.stats["euler_number"] = int(mesh.euler_number)
    if mesh.is_watertight and int(mesh.euler_number) != expected_euler:
        r.errors.append(f"Unexpected topology (Euler number {int(mesh.euler_number)}, expected {expected_euler}): "
                        "unwanted holes or handles in the surface.")
    if max_xy_radius is not None:
        ext = float(np.max(np.hypot(mesh.vertices[:, 0], mesh.vertices[:, 1])))
        r.stats["max_xy_radius_mm"] = ext
        if ext > max_xy_radius + 0.05:
            r.errors.append(f"The model is {ext * 2:.2f} mm wide, larger than the requested {max_xy_radius * 2:.1f} mm.")
    return r


def validate_opening(body: trimesh.Trimesh, d: Derived, hollow_report: ValidationReport) -> None:
    """The body must really be open at the bottom: nothing may cross the bore."""
    v = body.vertices
    z = v[:, 2]
    rho = np.hypot(v[:, 0], v[:, 1])
    sel = (z >= d.z0 - 1e-6) & (z <= d.z0 + d.thread_len + 1e-6)
    bore = float(rho[sel & (rho < d.r_so - 0.2)].min()) if (sel & (rho < d.r_so - 0.2)).any() else 0.0
    hollow_report.stats["bore_radius_mm"] = bore
    if bore < d.cr_out:
        hollow_report.errors.append("The bottom opening is too narrow to pass the LED cradle.")
    if body.bounds[0][2] < d.z0 - 1e-3:
        hollow_report.errors.append("The body extends below the split plane; the opening may be closed.")
    cavity = 4.0 / 3.0 * np.pi * d.r_in ** 3
    hollow_report.stats["inner_cavity_mm3"] = float(cavity)
    if body.volume > 0.5 * (4.0 / 3.0 * np.pi * d.r_out ** 3):
        hollow_report.errors.append("The ball is not hollow.")


def validate_wall(t_min_actual: float, min_wall: float, rep: ValidationReport) -> None:
    rep.stats["thinnest_wall_mm"] = t_min_actual
    if t_min_actual < min_wall - 1e-3:
        rep.errors.append(f"A wall is {t_min_actual:.2f} mm, thinner than the {min_wall:.2f} mm minimum.")


def validate_fit(body: trimesh.Trimesh, cap: trimesh.Trimesh, rep: ValidationReport) -> None:
    """Body and cap must not overlap anywhere when assembled (checks thread clearance)."""
    try:
        x = trimesh.boolean.intersection([body, cap], engine="manifold")
        vol = float(abs(x.volume)) if len(x.faces) else 0.0
    except Exception as exc:  # noqa: BLE001
        rep.warnings.append(f"Could not run the cap fit check ({exc}).")
        return
    rep.stats["cap_overlap_mm3"] = vol
    if vol > 0.5:
        rep.errors.append(f"The cap overlaps the ball by {vol:.1f} mm3; it would not fit.")
