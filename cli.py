"""Headless use:  python cli.py photo.jpg --out out [--quality draft] [--settings s.json]"""
import argparse
import json
import pathlib
import sys

from engine import generate
from exporter import build_export_bundle, ExportBlocked
from image_processor import ImageError
from settings import OrnamentSettings, Quality, SettingsError
from spherical_generator import GenerationError


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("image")
    ap.add_argument("--out", default="out")
    ap.add_argument("--quality", choices=[q.value for q in Quality], default="standard")
    ap.add_argument("--settings", help="JSON file with settings overrides")
    a = ap.parse_args()
    try:
        s = OrnamentSettings.from_dict(json.load(open(a.settings))) if a.settings else OrnamentSettings()
        r = generate(pathlib.Path(a.image).read_bytes(), s, Quality(a.quality),
                     progress=lambda f, m: print(f"[{f:4.0%}] {m}"))
        for rep in r.reports.values():
            print(rep.summary())
        b = build_export_bundle(r)
    except (ImageError, SettingsError, GenerationError, ExportBlocked, OSError) as exc:
        print("ERROR:", exc)
        return 1
    out = pathlib.Path(a.out); out.mkdir(parents=True, exist_ok=True)
    for n, data in b.files.items():
        (out / n).write_bytes(data)
    (out / "Christmas_Glow_Package.zip").write_bytes(b.zip_bytes)
    (out / "PRINTING_GUIDE.txt").write_text(b.guide)
    print("Wrote", out.resolve())
    return 0


if __name__ == "__main__":
    sys.exit(main())
