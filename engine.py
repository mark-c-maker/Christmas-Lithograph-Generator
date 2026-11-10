"""Custom Christmas Lithophane Generator - generation engine (no UI dependency).

    from engine import generate
    result = generate(image_bytes, OrnamentSettings.from_dict(json_settings))

This is the single entry point a website backend would call.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Union

import numpy as np
import trimesh
from PIL import Image

from image_processor import PreparedMap, load_image, prepare_map
from mesh_validation import ValidationReport, validate_fit, validate_mesh, validate_opening, validate_wall
from settings import Derived, OrnamentSettings, Quality, grid_columns
from spherical_generator import GenerationError, build_ornament, build_test_tile

ProgressCB = Callable[[float, str], None]
PLA_DENSITY_G_CM3 = 1.24


@dataclass
class GenerationResult:
    body: trimesh.Trimesh
    cap: trimesh.Trimesh
    settings: OrnamentSettings
    derived: Derived
    quality: Quality
    prepared: PreparedMap
    reports: Dict[str, ValidationReport]
    stats: dict
    notes: List[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(r.ok for r in self.reports.values())

    @property
    def errors(self) -> List[str]:
        return [f"{r.name}: {e}" for r in self.reports.values() for e in r.errors]

    def assembly(self) -> trimesh.Trimesh:
        return trimesh.util.concatenate([self.body, self.cap])

    def test_tile(self) -> trimesh.Trimesh:
        return build_test_tile(self.prepared.tile, self.derived, self.settings.shell.tone_gamma)


def generate(image: Union[bytes, Image.Image], settings: OrnamentSettings,
             quality: Optional[Quality] = None, progress: Optional[ProgressCB] = None) -> GenerationResult:
    cb = progress or (lambda f, m: None)
    q = quality or settings.quality
    cb(0.02, "Checking settings")
    d = settings.validate()
    cb(0.05, "Reading and preparing the photo")
    img = load_image(image) if isinstance(image, (bytes, bytearray)) else image
    prepared = prepare_map(img, settings, grid_columns(settings, q))
    meshes = build_ornament(prepared.wrapped, settings, d, q, cb)
    cb(0.80, "Validating the meshes")
    loop = settings.loop.enabled
    rb = validate_mesh(meshes.body, "Main ball", 0 if loop else 2, d.r_out)
    rc = validate_mesh(meshes.cap, "Bottom cap", 2, d.r_out)
    validate_opening(meshes.body, d, rb)
    validate_wall(meshes.t_min_actual, settings.shell.min_wall_mm, rb)
    validate_fit(meshes.body, meshes.cap, rc)
    stats = {
        "triangles": rb.stats.get("triangles", 0) + rc.stats.get("triangles", 0),
        "body_filament_g": round(float(meshes.body.volume) / 1000 * PLA_DENSITY_G_CM3, 1),
        "cap_filament_g": round(float(meshes.cap.volume) / 1000 * PLA_DENSITY_G_CM3, 1),
        "height_mm": round(float(meshes.body.bounds[1][2] - meshes.cap.bounds[0][2]), 1),
        "flange_overhang_mm": round(d.flange_overhang, 1),
    }
    cb(1.0, "Done")
    return GenerationResult(meshes.body, meshes.cap, settings, d, q, prepared,
                            {"body": rb, "cap": rc}, stats, list(prepared.notes))
