"""Custom Christmas Lithophane Generator - STL export and ZIP bundle."""
from __future__ import annotations

import io
import zipfile
from dataclasses import dataclass
from typing import Dict

import numpy as np
import trimesh

from engine import GenerationResult
from printing_guide import guide_text

FILENAMES = {
    "main": "Christmas_Lithophane_Main_Ball.stl",
    "cap": "Christmas_Lithophane_Bottom_Cap.stl",
    "assembly": "Christmas_Lithophane_Complete_Assembly.stl",
    "tile": "Christmas_Lithophane_Test_Tile.stl",
    "zip": "Christmas_Lithophane_Ornament.zip",
    "guide": "Printing_Guide.txt",
}
PRODUCT_NAME = "Custom Christmas Lithophane Generator"


class ExportBlocked(RuntimeError):
    """Raised when validation failed; no broken STL is ever produced."""


def _drop_to_bed(m: trimesh.Trimesh) -> trimesh.Trimesh:
    m = m.copy()
    m.apply_translation([0, 0, -float(m.bounds[0][2])])
    return m


def body_print_orientation(r: GenerationResult) -> trimesh.Trimesh:
    return _drop_to_bed(r.body)                       # opening on the bed, loop up


def cap_print_orientation(r: GenerationResult) -> trimesh.Trimesh:
    m = r.cap.copy()
    m.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0]))  # proper rotation
    return _drop_to_bed(m)                            # collar + cradle tips on the bed, dome up


def stl_bytes(m: trimesh.Trimesh) -> bytes:
    out = m.export(file_type="stl")
    return out if isinstance(out, bytes) else out.encode()


def verify_stl(data: bytes, name: str) -> None:
    """Re-read what is about to be offered and re-check it."""
    m = trimesh.load(io.BytesIO(data), file_type="stl")
    if not (m.is_watertight and m.is_winding_consistent and m.volume > 0):
        raise ExportBlocked(f"{name} did not pass the final re-check after export.")


@dataclass
class ExportBundle:
    files: Dict[str, bytes]
    zip_bytes: bytes
    guide: str


def build_export_bundle(r: GenerationResult, include_tile: bool = True) -> ExportBundle:
    if not r.ok:
        raise ExportBlocked("Export blocked because validation failed:\n- " + "\n- ".join(r.errors))
    files = {
        FILENAMES["main"]: stl_bytes(body_print_orientation(r)),
        FILENAMES["cap"]: stl_bytes(cap_print_orientation(r)),
        FILENAMES["assembly"]: stl_bytes(_drop_to_bed(r.assembly())),
    }
    if include_tile:
        tile = r.test_tile()
        if not (tile.is_watertight and tile.volume > 0):
            raise ExportBlocked("The test tile failed validation.")
        files[FILENAMES["tile"]] = stl_bytes(tile)
    for name in (FILENAMES["main"], FILENAMES["cap"]):
        verify_stl(files[name], name)
    guide = guide_text(PRODUCT_NAME, r.settings, r.stats, part_sizes(r))
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for n, b in files.items():
            z.writestr(n, b)
        z.writestr(FILENAMES["guide"], guide)
    return ExportBundle(files, buf.getvalue(), guide)


def part_sizes(r: GenerationResult) -> dict:
    """Width x depth x height (mm) of each printable part in print orientation."""
    out = {
        "Main Ball": tuple(float(v) for v in body_print_orientation(r).extents),
        "Bottom Cap": tuple(float(v) for v in cap_print_orientation(r).extents),
        "Test Tile": tuple(float(v) for v in r.test_tile().extents),
    }
    return out
