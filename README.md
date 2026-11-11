# Custom Christmas Lithophane Generator

Upload a photo and export STL files for a hollow, light-up lithophane ornament with the picture wrapped around the whole ball. Runs locally in your browser; the generation engine is separate from the interface so it can later run as a web service.

## Run on Windows
1. Install Python 3.10 to 3.12 from python.org and tick "Add python.exe to PATH".
2. Double-click `run.bat`. The first run creates a `.venv` and installs the requirements, then opens the app.

Manual: `py -3 -m venv .venv`, `.venv\Scripts\activate`, `pip install -r requirements.txt`, `streamlit run app.py`.
Headless: `python cli.py photo.jpg --out out --quality standard`. Tests: `pip install pytest`, `python -m pytest tests -q`.

## Using it
The left panel holds the design settings. The four tabs are 3D Preview, Photo & Seam, Printing Guide and Export STL. Export STL is always at the right of the tab bar; every page also has a button that jumps to it.

Export gives five downloads: Complete package (ZIP: all STL files plus the printing guide), Test tile, Main ball, Bottom cap, and Complete assembly (fit check only, not for printing).

## How it works
- The photo is sampled on a longitude and latitude grid. Outer radius = inner radius + wall thickness, where thickness follows brightness (white = thin, black = thick). The inner surface is a perfect sphere.
- Diameter is the maximum outer diameter, reached by the darkest pixels.
- Photo layouts: Repeat (keeps proportions, copies around the ball, optional mirroring) or Panorama (one 2:1 crop over the full sphere). Seams are cross-faded or mirrored so the edges join without a step.
- Near both poles the wall blends to a constant thickness, so the grid never pinches into noise and the hanging loop has a solid base.
- The ball splits on a flat plane 40 degrees below the equator. The cap is a dome that continues the photo over the bottom, with a threaded collar (2.5 mm pitch, 45 degree flanks, 0.35 mm clearance) and an LED ring with vent slots.
- Every part is one closed profile swept 360 degrees, so meshes are manifold by construction. Only the loop eyelet uses a boolean union (manifold3d).
- Before export: watertight, winding, volume sign, zero-area faces, single piece, topology (Euler number), size in mm, thinnest wall, opening clear for the LED, and a software check that the cap does not overlap the ball. STL files are re-read and re-checked. Any failure blocks the download.

## Files
`settings.py` configuration and derived dimensions | `image_processor.py` loading, tone, wrap sampling | `spherical_generator.py` geometry | `mesh_validation.py` | `engine.py` entry point | `exporter.py` STL, ZIP | `printing_guide.py` guide content and printer fit check | `preview.py` Plotly preview | `theme.py` styling and artwork | `app.py` Streamlit | `cli.py`

## Engine API
```python
from engine import generate
from exporter import build_export_bundle
from settings import OrnamentSettings
result = generate(image_bytes, OrnamentSettings.from_dict({"shell": {"diameter_mm": 100}}))
bundle = build_export_bundle(result)   # raises ExportBlocked if validation failed
```

## Known limits
- Checked in software only; print the test tile first, then the ornament, and adjust the thread clearance if the cap is tight or loose.
- The cap prints upside down and its flange bridges about 7 mm. Some printers may need cap-only supports.
- The LED sits low, so the bottom of the ball glows brightest.
- The default 100 mm ball needs a tea light of about 38 mm or smaller; the smallest ball for a 38 mm LED is about 85 mm.
- Fonts load from Google Fonts when online and fall back to system fonts offline.
