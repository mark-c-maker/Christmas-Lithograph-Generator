"""Printing guidance shared by the app and the ZIP download. No UI code."""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple

# (brand, model, (x, y, z) build volume in mm)
PRINTERS: List[Tuple[str, str, Tuple[float, float, float]]] = [
    ("Bambu Lab", "A1 mini", (180, 180, 180)),
    ("Bambu Lab", "A1", (256, 256, 256)),
    ("Bambu Lab", "P1S / P1P", (256, 256, 256)),
    ("Bambu Lab", "P2S", (256, 256, 256)),
    ("Bambu Lab", "X1 Carbon / X1E", (256, 256, 256)),
    ("Bambu Lab", "A2L", (330, 320, 325)),
    ("Bambu Lab", "H2S", (340, 320, 340)),
    ("Bambu Lab", "H2D", (350, 320, 325)),
    ("Prusa", "MK4 / MK4S", (250, 210, 220)),
    ("Prusa", "MINI+", (180, 180, 180)),
    ("Creality", "Ender-3 V3 SE", (220, 220, 250)),
    ("Creality", "K1 / K1C", (220, 220, 250)),
    ("Creality", "K1 Max", (300, 300, 300)),
    ("Elegoo", "Neptune 4", (225, 225, 265)),
    ("Elegoo", "Neptune 4 Plus", (320, 320, 385)),
]
BED_MARGIN_MM = 5.0   # room for brim / skirt on each side


def printer_label(p) -> str:
    return f"{p[0]} {p[1]}  ({p[2][0]:.0f} x {p[2][1]:.0f} x {p[2][2]:.0f} mm)"


def fit_check(parts: Dict[str, Tuple[float, float, float]], volume: Tuple[float, float, float]):
    """parts: name -> (x, y, z) extents in print orientation. Returns list of (name, ok, text)."""
    out = []
    ux, uy, uz = volume[0] - 2 * BED_MARGIN_MM, volume[1] - 2 * BED_MARGIN_MM, volume[2]
    for name, (x, y, z) in parts.items():
        fx = (x <= ux and y <= uy) or (x <= uy and y <= ux)
        fz = z <= uz
        ok = fx and fz
        txt = f"{x:.0f} x {y:.0f} x {z:.0f} mm"
        if not fx:
            txt += " - too wide for this bed (after a 5 mm brim margin)"
        elif not fz:
            txt += " - too tall for this printer"
        out.append((name, ok, txt))
    return out


# --------------------------------------------------------------------------
UNIVERSAL: List[Tuple[str, str]] = [
    ("Filament", "Plain white or natural PLA. Silk, sparkle and translucent filaments scatter light unevenly and wash out detail."),
    ("Nozzle", "0.4 mm. A 0.2 mm nozzle gives finer detail but takes far longer."),
    ("Layer height", "0.12 mm. Use 0.08 mm for maximum detail or 0.16 mm for a faster draft."),
    ("Walls and infill", "100% infill, or enough wall loops to fill the full wall thickness. The walls are the picture; gaps show up as bright spots."),
    ("Supports", "None. The model is designed to print without supports."),
    ("Brim", "3 to 5 mm brim on the main ball and the cap."),
    ("Speed", "Outer wall 30 to 50 mm/s. Fast outer walls blur fine detail."),
    ("Cooling", "Part-cooling fan at 100% after the first few layers."),
    ("Seam", "Aligned or rear. Do not use random."),
    ("Temperature", "Your filament's normal PLA profile."),
]

SLICERS: Dict[str, List[Tuple[str, str]]] = {
    "Bambu Studio / OrcaSlicer / Creality Print / Elegoo Slicer": [
        ("Quality > Layer height", "0.12 mm (the 0.12 mm Fine profile is a good base)"),
        ("Strength > Sparse infill density", "100%"),
        ("Strength > Wall loops", "Leave at default; infill at 100% fills the rest"),
        ("Quality > Detect thin wall", "On"),
        ("Quality > Seam position", "Aligned or Back"),
        ("Quality > Elephant foot compensation", "0.1 to 0.2 mm if the cap sticks"),
        ("Support", "Off"),
        ("Others > Brim type / width", "Outer brim, 3 to 5 mm"),
        ("Speed > Outer wall", "30 to 50 mm/s"),
    ],
    "PrusaSlicer / SuperSlicer": [
        ("Layer height", "0.12 mm"),
        ("Infill > Fill density", "100%"),
        ("Layers and perimeters > Seam position", "Aligned or Rear"),
        ("Support material > Generate support material", "Off"),
        ("Skirt and brim > Brim width", "3 to 5 mm"),
        ("Advanced > Elephant foot compensation", "0.1 to 0.2 mm if the cap sticks"),
        ("Speed > External perimeters", "30 to 50 mm/s"),
    ],
    "UltiMaker Cura": [
        ("Layer Height", "0.12 mm"),
        ("Infill Density", "100%"),
        ("Z Seam Alignment", "Back or Sharpest Corner (not Random)"),
        ("Generate Support", "Off"),
        ("Build Plate Adhesion Type", "Brim, 3 to 5 mm"),
        ("Initial Layer Horizontal Expansion", "-0.1 to -0.2 mm if the cap sticks"),
        ("Outer Wall Speed", "30 to 50 mm/s"),
    ],
}

FAMILIES: Dict[str, List[str]] = {
    "Bambu Lab (A1 mini, A1, A2L)": [
        "Open-frame printers cool PLA well, which suits this model. Use the 0.12 mm Fine process with your PLA filament profile, then set sparse infill to 100%.",
        "The A1 mini (180 mm cube) fits the default 100 mm ornament, but larger ornaments will not.",
    ],
    "Bambu Lab (P1S, P2S, X1 Carbon, H2S, H2D)": [
        "Enclosed printers can heat the chamber enough to soften PLA on long prints. Open the front door or remove the top lid, and avoid chamber heating for this job.",
        "Use a clean textured or smooth PEI plate. The ring that touches the bed is narrow, so use a brim.",
    ],
    "Prusa (MK4 / MK4S, MINI+)": [
        "Use the 0.12 mm quality profile with Generic PLA, set fill density to 100%, and add a brim.",
        "The MINI+ build volume is tight for large ornaments; check the fit panel above.",
    ],
    "Creality (Ender-3 V3 SE, K1, K1C, K1 Max)": [
        "On bed-slingers, slow the outer wall and keep the fan at 100% for clean overhangs near the base of the ball.",
        "On the K1 series keep the lid open for PLA to avoid heat creep on a tall print.",
    ],
    "Elegoo (Neptune 4, Neptune 4 Plus)": [
        "Use a 0.12 mm layer height and a generic PLA profile in Elegoo Slicer or Orca. Add a brim and run the fan at 100%.",
    ],
    "Other printers": [
        "Any FDM printer with at least 130 x 130 x 105 mm of usable space can print the default 100 mm ornament. Use the settings above and print the test tile first.",
    ],
}

TROUBLESHOOTING: List[Tuple[str, str]] = [
    ("Bright spots or streaks in the picture", "Gaps between walls. Set infill to 100% or increase wall loops."),
    ("Ring marks across the ball", "Layers are too coarse or the filament is wet. Use 0.12 mm or less and dry the filament."),
    ("Underside of the cap flange sags", "The flange bridges a few millimetres. Slow the first bridge layers, add cooling, or enable supports for the cap only."),
    ("Cap too tight", "Raise the thread clearance by 0.1 mm in Advanced settings and export again."),
    ("Cap too loose", "Lower the thread clearance by 0.1 mm and export again."),
    ("Ball lifts at the edge", "Add a brim, clean the plate, and keep the first layer slow."),
]

ASSEMBLY = [
    "Remove the brims and clean any stringing from the cap thread and the LED ring.",
    "Switch the LED tea light on, then stand it inside the ring on the cap.",
    "Screw the cap into the ball by hand, turning clockwise. Do not force it.",
    "Hang the ornament by the loop with a hook or ribbon. The loop is for the ornament only.",
    "Use battery LED tea lights only. Never use a real flame.",
]


def guide_text(name: str, settings, stats: dict, parts: Optional[dict] = None) -> str:
    s = settings
    L: List[str] = []
    add = L.append
    add(name.upper())
    add("PRINTING GUIDE")
    add("=" * 60)
    add(f"Ornament: {s.shell.diameter_mm:.0f} mm, wall {s.shell.min_wall_mm:.1f} mm (light areas) to {s.shell.max_wall_mm:.1f} mm (dark areas)")
    add(f"Estimated PLA: main ball about {stats.get('body_filament_g', '?')} g, cap about {stats.get('cap_filament_g', '?')} g")
    add("")
    add("FILES (already oriented for printing, units in millimetres)")
    add("  Main Ball        Opening faces the bed, loop points up. Print as is.")
    add("  Bottom Cap       Prints upside down: collar and LED ring on the bed, dome up. Print as is.")
    add("  Test Tile        Flat panel from your image. Print this first to judge detail and brightness.")
    add("  Complete Assembly  Fit check only. Do not print.")
    add("")
    add("The geometry passes mesh checks (closed, manifold, correct orientation) and the thread was")
    add("checked for interference in software. It has not been verified on every printer, so print the")
    add("test tile first and adjust the thread clearance if the cap is too tight or loose.")
    add("")
    add("RECOMMENDED SETTINGS (any printer)")
    for k, v in UNIVERSAL:
        add(f"  {k:<17}{v}")
    add("")
    add("SLICER SETTING NAMES")
    for slicer, rows in SLICERS.items():
        add(f"  {slicer}")
        for k, v in rows:
            add(f"    {k}: {v}")
        add("")
    add("BY PRINTER")
    for fam, notes in FAMILIES.items():
        add(f"  {fam}")
        for n in notes:
            add(f"    - {n}")
    add("")
    add("BUILD VOLUMES (check that the parts fit)")
    for p in PRINTERS:
        add(f"  {printer_label(p)}")
    if parts:
        add("")
        add("PART SIZES AT THIS DESIGN")
        for n, (x, y, z) in parts.items():
            add(f"  {n}: {x:.0f} x {y:.0f} x {z:.0f} mm")
    add("")
    add("ASSEMBLY AND LIGHTING")
    for i, step in enumerate(ASSEMBLY, 1):
        add(f"  {i}. {step}")
    add("")
    add("TROUBLESHOOTING")
    for k, v in TROUBLESHOOTING:
        add(f"  {k}: {v}")
    add("")
    return "\n".join(L)
