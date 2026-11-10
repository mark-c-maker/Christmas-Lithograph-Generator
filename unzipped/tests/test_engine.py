import io, math, os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import numpy as np
import pytest
import trimesh
from PIL import Image

from engine import generate
from exporter import ExportBlocked, build_export_bundle
from image_processor import ImageError, load_image, sample_image
from settings import OrnamentSettings, Preset, Quality, SettingsError, WrapMode

IMG = sample_image(1200)


def png(img, fmt="PNG"):
    b = io.BytesIO(); img.save(b, fmt); return b.getvalue()


def gen(mut=None, img=IMG, q=Quality.DRAFT):
    s = OrnamentSettings()
    if mut: mut(s)
    return generate(img, s, q)


def test_default_valid_and_hollow():
    r = gen()
    assert r.ok, r.errors
    assert r.reports["body"].stats["euler_number"] == 0   # loop = one handle
    assert r.reports["cap"].stats["euler_number"] == 2
    assert r.reports["body"].stats["bore_radius_mm"] >= r.derived.cr_out
    assert r.reports["body"].stats["thinnest_wall_mm"] >= 1.0 - 1e-3


def test_dimensions_mm():
    r = gen()
    xy = max(np.hypot(*r.body.vertices[:, :2].T))
    assert 49.0 < xy <= 50.05


@pytest.mark.parametrize("preset", list(Preset))
def test_presets(preset):
    assert gen(lambda s: setattr(s.image, "preset", preset)).ok


@pytest.mark.parametrize("copies,mirror", [(1, False), (2, True), (2, False), (3, False), (4, True)])
def test_preserve_aspect(copies, mirror):
    def m(s):
        s.wrap.mode = WrapMode.PRESERVE_ASPECT; s.wrap.copies = copies; s.wrap.mirror = mirror
    assert gen(m).ok


def test_no_loop_is_genus0():
    r = gen(lambda s: setattr(s.loop, "enabled", False))
    assert r.ok and r.reports["body"].stats["euler_number"] == 2


def test_no_vents_and_big_led_error():
    assert gen(lambda s: setattr(s.led, "vent_count", 0)).ok
    with pytest.raises(SettingsError):
        gen(lambda s: setattr(s.shell, "diameter_mm", 70.0))


def test_other_diameters():
    for dia in (90.0, 120.0):
        assert gen(lambda s, d=dia: setattr(s.shell, "diameter_mm", d)).ok


@pytest.mark.parametrize("img", [
    Image.new("L", (200, 4000), 128),                       # very tall
    Image.new("RGB", (6000, 120), (10, 10, 10)),            # very wide, all dark
    Image.new("RGBA", (300, 300), (255, 0, 0, 0)),          # fully transparent
    Image.new("RGB", (300, 300), (255, 255, 255)),          # all white
    Image.fromarray(np.random.default_rng(1).integers(0, 255, (300, 300), dtype=np.uint8), "L"),  # noise
])
def test_unusual_images(img):
    assert gen(img=png(img)).ok


def test_jpeg_webp():
    for fmt in ("JPEG", "WEBP"):
        assert gen(img=png(IMG, fmt)).ok


def test_bad_uploads():
    for bad in (b"", b"not an image", png(IMG, "BMP"), png(Image.new("RGB", (10, 10)))):
        with pytest.raises(ImageError):
            load_image(bad)
    with pytest.raises(ImageError):
        load_image(b"\0" * (26 * 1024 * 1024))


def test_export_roundtrip_and_blocking():
    r = gen()
    b = build_export_bundle(r)
    for name in ("Christmas_Lithophane_Main_Ball.stl", "Christmas_Lithophane_Bottom_Cap.stl"):
        m = trimesh.load(io.BytesIO(b.files[name]), file_type="stl")
        assert m.is_watertight and m.is_winding_consistent and m.volume > 0
        assert abs(m.bounds[0][2]) < 1e-3                    # sits on the bed
    r.reports["body"].errors.append("forced failure")
    with pytest.raises(ExportBlocked):
        build_export_bundle(r)


def test_thread_and_led_clearance():
    r = gen()
    def vol(a, b):
        x = trimesh.boolean.intersection([a, b], engine="manifold")
        return float(abs(x.volume)) if len(x.faces) else 0.0
    assert vol(r.body, r.cap) < 1e-3
    p = r.settings.joint.thread_pitch_mm
    for ang in (30, 120, 250):
        c = r.cap.copy()
        c.apply_transform(trimesh.transformations.rotation_matrix(math.radians(ang), [0, 0, 1]))
        c.apply_translation([0, 0, -p * (1 - ang / 360)])
        assert vol(r.body, c) < 1e-3, ang
    d = r.derived
    base = -d.r_in * math.cos(math.asin(19.0 / d.r_in)) + 0.02
    led = trimesh.creation.cylinder(radius=19.0, height=13.0, sections=96)
    led.apply_translation([0, 0, base + 6.5])
    assert vol(led, r.cap) < 1e-3 and vol(led, r.body) < 1e-3


def test_seam_continuous():
    r = gen()
    w = r.prepared.wrapped
    lat = np.linspace(-60, 60, 50)
    a = w.sample(np.full(50, 179.999), lat); b = w.sample(np.full(50, 180.001), lat)
    assert np.abs(a - b).max() < 0.02


def test_settings_json_roundtrip():
    s = OrnamentSettings(); s.wrap.mode = WrapMode.PRESERVE_ASPECT; s.quality = Quality.HIGH
    assert OrnamentSettings.from_dict(s.to_dict()) == s


def test_zip_contents_and_no_json():
    import zipfile
    b = build_export_bundle(gen())
    names = zipfile.ZipFile(io.BytesIO(b.zip_bytes)).namelist()
    assert sorted(names) == sorted([
        "Christmas_Lithophane_Main_Ball.stl", "Christmas_Lithophane_Bottom_Cap.stl",
        "Christmas_Lithophane_Complete_Assembly.stl", "Christmas_Lithophane_Test_Tile.stl", "Printing_Guide.txt"])
    assert not any(n.endswith(".json") for n in names)
    guide = zipfile.ZipFile(io.BytesIO(b.zip_bytes)).read("Printing_Guide.txt").decode()
    assert "Bambu" in guide and "Neptune 4 Plus" in guide and "Prusa" in guide


def test_fit_check():
    from printing_guide import fit_check, PRINTERS
    parts = {"Main Ball": (100.0, 100.0, 99.0)}
    a1mini = [p for p in PRINTERS if p[1] == "A1 mini"][0][2]
    assert fit_check(parts, a1mini)[0][1]                    # 100 mm ball fits 180 mm cube
    assert not fit_check({"Big": (190.0, 190.0, 100.0)}, a1mini)[0][1]
    assert not fit_check({"Tall": (50.0, 50.0, 200.0)}, a1mini)[0][1]
