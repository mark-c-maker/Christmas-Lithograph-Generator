"""Custom Christmas Lithophane Generator - Streamlit front end.
All geometry lives in engine.py and the modules it uses."""
import hashlib
import io
import json

import streamlit as st

import printing_guide as pg
import theme
from engine import generate
from exporter import ExportBlocked, FILENAMES, build_export_bundle, part_sizes
from image_processor import ImageError, load_image, prepare_map, sample_image
from preview import VIEWS, STAGE, make_figure, preview_arrays, seam_preview_image, tile_image
from settings import OrnamentSettings, Preset, Quality, SettingsError, WrapMode, grid_columns, min_diameter_for_led
from spherical_generator import GenerationError

st.set_page_config(page_title="Custom Christmas Lithophane Generator", page_icon=theme.favicon(),
                   layout="wide", initial_sidebar_state="auto")
import analytics
if st.query_params.get("admin") == "1":
    import admin_view
    admin_view.show()
    st.stop()
if not st.session_state.get("_visit_logged"):
    st.session_state["_visit_logged"] = True
    analytics.track("visit")
theme.inject_theme()

PAGES = ["3D Preview", "Photo & Seam", "Printing Guide", "Export STL"]
PRESETS = {"Photo": Preset.PHOTO, "High Contrast": Preset.HIGH_CONTRAST, "Silhouette": Preset.SILHOUETTE}
QUALITY = {"Draft": Quality.DRAFT, "Standard": Quality.STANDARD, "High": Quality.HIGH}
QUALITY_NOTE = {
    "Draft": "Quick fit check. Facets are visible on the surface.",
    "Standard": "Recommended. Smooth detail for most printers.",
    "High": "Finest detail. Larger files and slower slicing.",
}


# ----------------------------------------------------------------------- helpers
def seg(label, options, key, default, where=st, **kw):
    """Segmented control that never returns None."""
    v = where.segmented_control(label, options, default=default, key=key, selection_mode="single", **kw)
    if v is None:
        return st.session_state.get(f"_last_{key}", default)
    st.session_state[f"_last_{key}"] = v
    return v


def sec(n, title):
    st.sidebar.markdown(f'<div class="sec"><i>{n}</i>{title}</div>', unsafe_allow_html=True)


def small_label(text):
    st.markdown(f'<div class="control-label">{text}</div>', unsafe_allow_html=True)


@st.cache_data(show_spinner=False, max_entries=6)
def cached_preview(img_bytes: bytes, settings_json: str):
    s = OrnamentSettings.from_dict(json.loads(settings_json))
    r = generate(img_bytes, s, Quality.PREVIEW)
    v, f, t = preview_arrays(r)
    return dict(v=v, f=f, t=t, errors=r.errors, stats=r.stats, notes=r.notes,
                t_min=r.derived.t_min, t_max=r.derived.t_max, parts=part_sizes(r),
                height=r.stats["height_mm"])


@st.cache_data(show_spinner=False, max_entries=6)
def cached_map(img_bytes: bytes, settings_json: str):
    s = OrnamentSettings.from_dict(json.loads(settings_json))
    p = prepare_map(img_bytes, s, grid_columns(s, Quality.DRAFT))
    return seam_preview_image(p, s.wrap.seam_position_deg), tile_image(p), p.notes


def go_export():
    st.session_state["page"] = "Export STL"


# ----------------------------------------------------------------------- sidebar
sb = st.sidebar
sec(1, "Photo")
up = sb.file_uploader("Choose a PNG, JPG or WEBP image", type=["png", "jpg", "jpeg", "webp"])
if sb.button("Try a sample image"):
    buf = io.BytesIO(); sample_image().save(buf, "PNG")
    st.session_state["sample"] = buf.getvalue()
img_bytes = up.getvalue() if up is not None else st.session_state.get("sample")

s = OrnamentSettings()
with sb:
    sec(2, "Photo layout")
    layout = seg("How the photo wraps", ["Repeat", "Panorama"], "layout", "Repeat", label_visibility="collapsed")
    if layout == "Repeat":
        st.markdown('<div class="hint">Keeps the photo\'s proportions and repeats it around the ball. Best for portraits and everyday photos.</div>', unsafe_allow_html=True)
        s.wrap.mode = WrapMode.PRESERVE_ASPECT
        s.wrap.copies = st.slider("Copies around the ball", 1, 4, 2)
        s.wrap.mirror = st.toggle("Mirror every other copy", True, help="Hides the seam. Needs an even number of copies.")
        s.wrap.polar_fade_deg = 20.0
    else:
        st.markdown('<div class="hint">Stretches one 2:1 crop over the whole sphere. Best for wide landscape or panorama images.</div>', unsafe_allow_html=True)
        s.wrap.mode = WrapMode.FULL_SPHERE
    with st.expander("Crop and position"):
        s.image.zoom = st.slider("Zoom", 1.0, 4.0, 1.0, 0.05)
        s.image.pan_x = st.slider("Move left / right", -1.0, 1.0, 0.0, 0.05)
        s.image.pan_y = st.slider("Move up / down", -1.0, 1.0, 0.0, 0.05)
        s.image.rotation_deg = st.slider("Rotate (degrees)", -180.0, 180.0, 0.0, 1.0)
        s.wrap.seam_position_deg = st.slider("Seam position (degrees)", 0.0, 360.0, 180.0, 5.0,
                                             help="Where the photo's edges meet. 0 is the front, 180 is the back.")

    sec(3, "Appearance")
    s.image.preset = PRESETS[seg("Preset", list(PRESETS), "preset", "Photo", label_visibility="collapsed")]
    st.markdown('<div class="hint">Photo suits portraits. High Contrast suits strong light and dark areas. Silhouette suits logos and simple shapes.</div>', unsafe_allow_html=True)
    s.image.brightness = st.slider("Brightness", 0.5, 1.8, 1.0, 0.05)
    s.image.contrast = st.slider("Contrast", 0.5, 2.0, 1.0, 0.05)
    with st.expander("Fine tuning"):
        s.image.sharpness = st.slider("Sharpness", 0.0, 3.0, 1.0, 0.1)
        s.image.smoothing_px = st.slider("Smoothing", 0.0, 4.0, 0.0, 0.1)
    s.image.invert = st.toggle("Swap light and dark", False)

    sec(4, "Ornament")
    s.shell.diameter_mm = float(st.slider("Diameter (mm)", 60, 200, 100, 5))
    lo, hi = st.slider("Wall thickness (mm)", 0.6, 4.0, (1.0, 3.0), 0.1,
                       help="Light areas use the thin end and glow brightest. Dark areas use the thick end.")
    s.shell.min_wall_mm, s.shell.max_wall_mm = float(lo), float(hi)
    s.loop.enabled = st.toggle("Hanging loop", True)
    s.led.diameter_mm = float(st.slider("LED tea light diameter (mm)", 30, 50, 38, 1,
                                        help="Most battery tea lights are 38 mm wide. Measure yours."))
    with st.expander("Advanced"):
        s.shell.tone_gamma = st.slider("Midtone curve", 0.5, 2.0, 1.0, 0.05, help="Above 1 darkens midtones, below 1 lightens them.")
        s.image.grayscale_method = st.selectbox("Grayscale conversion", ["luminosity", "average", "red", "green", "blue"])
        s.wrap.seam_blend = st.slider("Seam softness", 0.0, 0.3, 0.12, 0.01)
        s.joint.thread_clearance_mm = st.slider("Cap thread clearance (mm)", 0.15, 0.7, 0.35, 0.05,
                                                help="Raise if the cap is too tight, lower if it is loose.")
        s.led.vent_count = st.slider("Slots in the LED ring", 0, 6, 3)
        s.joint.cap_alignment_deg = float(st.slider(
            "Cap picture alignment (degrees)", 0, 90, 30, 1,
            help="Printed caps stop a little before fully tight. Screw the cap in clockwise (seen from below) until snug. "
                 "If you must turn it a further X degrees to line the pictures up, set this to X and reprint the cap only."))

# ----------------------------------------------------------------------- header
theme.hero()

if img_bytes is None:
    st.markdown("""<div class="panel" style="max-width:640px"><h3 style="margin-top:0">Start with a photo</h3>
    <p style="color:var(--muted);line-height:1.6">Choose an image in the left panel, or press <b>Try a sample image</b> to see how it works.
    Square or portrait photos with a clear subject give the best result.</p></div>""", unsafe_allow_html=True)
    st.stop()

try:
    load_image(img_bytes)
    s.validate()
except (ImageError, SettingsError) as exc:
    st.error(str(exc))
    if isinstance(exc, SettingsError):
        need = min_diameter_for_led(s)
        if need:
            st.caption(f"The smallest ball for this LED is about {need:.0f} mm.")
    st.stop()

sj = json.dumps(s.to_dict())
sig = hashlib.sha1(sj.encode() + hashlib.sha1(img_bytes).digest()).hexdigest()

with st.container(key="nav"):
    chosen = seg("Section", PAGES, "page", PAGES[0], label_visibility="collapsed")
page = chosen
if st.session_state.get("_last_page") != page:
    st.session_state["_last_page"] = page
    analytics.track("page", page)


def cta(text_html):
    with st.container(key="cta"):
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        c1.markdown(f'<div class="cta-t">{text_html}</div>', unsafe_allow_html=True)
        c2.button("Go to Export STL", type="primary", on_click=go_export, key="cta_btn_" + page)


# ----------------------------------------------------------------------- pages
if page == "3D Preview":
    with st.container(key="page_preview"):
        try:
            with st.spinner("Updating the preview"):
                pv = cached_preview(img_bytes, sj)
        except (ImageError, SettingsError, GenerationError) as exc:
            st.error(str(exc)); st.stop()
        c1, c2, c3 = st.columns([1.5, 1, 1])
        with c1:
            small_label("View"); view = seg("View", list(VIEWS), "pv_view", "Front", label_visibility="collapsed")
        with c2:
            small_label("Lighting"); light = seg("Lighting", ["LED on", "Daylight"], "pv_light", "LED on", label_visibility="collapsed")
        with c3:
            small_label("Section"); section = seg("Section", ["Whole", "Cut-away"], "pv_section", "Whole", label_visibility="collapsed")
        with st.container(key="stage_lit" if light == "LED on" else "stage_day"):
            fig = make_figure(pv["v"], pv["f"], pv["t"], pv["t_min"], pv["t_max"], light, section, view)
            st.plotly_chart(fig, config={"displayModeBar": False, "scrollZoom": True})
        st.caption("Drag to rotate, scroll to zoom. Choosing a view resets the camera. "
                   "The glow is an estimate; real results depend on your filament and LED.")
        for n in pv["notes"]:
            st.markdown(f'<div class="notice">{n}</div>', unsafe_allow_html=True)
        p = pv["parts"]["Main Ball"]
        st.markdown(f"""<div class="stats">
          <div class="stat"><b>{s.shell.diameter_mm:.0f} mm</b><span>Diameter</span></div>
          <div class="stat"><b>{pv['height']:.0f} mm</b><span>Height with loop</span></div>
          <div class="stat"><b>{s.shell.min_wall_mm:.1f} to {s.shell.max_wall_mm:.1f} mm</b><span>Wall thickness</span></div>
          <div class="stat"><b>{pv['stats']['body_filament_g'] + pv['stats']['cap_filament_g']:.0f} g</b><span>Estimated PLA</span></div>
          <div class="stat"><b>{s.led.diameter_mm:.0f} mm</b><span>LED size</span></div></div>""", unsafe_allow_html=True)
        cta("<b>Happy with the design?</b><br><span>Generate and download the STL files on the Export STL tab.</span>")

elif page == "Photo & Seam":
    with st.container(key="page_photo"):
        st.markdown('<div class="page-title">Photo and seam</div>'
                    '<div class="page-sub">This is what the printer receives. The left image is your photo after cropping and tone adjustments. '
                    'The right image is the full wrapped map; the red line marks where the photo edges meet.</div>', unsafe_allow_html=True)
        try:
            m_img, t_img, m_notes = cached_map(img_bytes, sj)
        except (ImageError, SettingsError) as exc:
            st.error(str(exc)); st.stop()
        a, b = st.columns([1, 1.6])
        a.image(t_img, caption="Adjusted photo (one copy)")
        b.image(m_img, caption="Wrapped map, 360 x 180 degrees, seam centred")
        st.markdown(f"""<div class="panel" style="max-width:520px"><b style="font-family:var(--serif)">Brightness to wall thickness</b>
          <div class="legend"></div><div class="legend-labels"><span>White: {s.shell.min_wall_mm:.1f} mm, glows</span><span>Black: {s.shell.max_wall_mm:.1f} mm, dark</span></div></div>""", unsafe_allow_html=True)
        for n in m_notes:
            st.markdown(f'<div class="notice">{n}</div>', unsafe_allow_html=True)
        cta("<b>Ready to print?</b><br><span>Generate the STL files on the Export STL tab.</span>")

elif page == "Printing Guide":
    with st.container(key="page_guide"):
        try:
            pv = cached_preview(img_bytes, sj)
        except (ImageError, SettingsError, GenerationError) as exc:
            st.error(str(exc)); st.stop()
        st.markdown('<div class="page-title">Printing guide</div>'
                    '<div class="page-sub">Settings that work on most FDM printers, with slicer setting names and notes for popular machines. '
                    'Print the test tile first to judge detail and brightness.</div>', unsafe_allow_html=True)
        st.markdown("#### Will it fit your printer?")
        labels = [pg.printer_label(p) for p in pg.PRINTERS] + ["Other printer (enter build volume)"]
        pick = st.selectbox("Printer", labels, index=None, placeholder="Choose your printer", label_visibility="collapsed")
        vol = None
        if pick == labels[-1]:
            cx, cy, cz = st.columns(3)
            vol = (cx.number_input("Width (mm)", 80, 1000, 220), cy.number_input("Depth (mm)", 80, 1000, 220), cz.number_input("Height (mm)", 80, 1000, 250))
        elif pick:
            vol = pg.PRINTERS[labels.index(pick)][2]
        if vol:
            res = pg.fit_check({k: v for k, v in pv["parts"].items() if k != "Test Tile"} | {"Test Tile": pv["parts"]["Test Tile"]}, vol)
            cards = "".join(f'<div class="fitcard {"ok" if ok else "no"}"><strong>{"Fits" if ok else "Does not fit"}</strong><br><b>{n}</b><em>{t}</em></div>'
                            for n, ok, t in res)
            st.markdown(f'<div class="fit">{cards}</div>', unsafe_allow_html=True)
            if not all(ok for _, ok, _ in res):
                st.markdown('<div class="notice">Reduce the ball diameter in the left panel until every part fits.</div>', unsafe_allow_html=True)
        else:
            st.caption("Sizes include a 5 mm brim margin on every side.")
        st.markdown("#### Recommended settings")
        st.markdown('<div class="panel"><table class="gtable">' + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in pg.UNIVERSAL) + "</table></div>", unsafe_allow_html=True)
        st.markdown("#### Setting names by slicer")
        for name, rows in pg.SLICERS.items():
            with st.expander(name):
                st.markdown('<table class="gtable">' + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in rows) + "</table>", unsafe_allow_html=True)
        st.markdown("#### Notes by printer")
        for fam, notes in pg.FAMILIES.items():
            with st.expander(fam):
                for n in notes:
                    st.markdown(f"- {n}")
        st.markdown("#### Assembly and lighting")
        for i, step in enumerate(pg.ASSEMBLY, 1):
            st.markdown(f"{i}. {step}")
        st.markdown("#### Troubleshooting")
        st.markdown('<div class="panel"><table class="gtable">' + "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in pg.TROUBLESHOOTING) + "</table></div>", unsafe_allow_html=True)
        cta("<b>Ready to print?</b><br><span>Generate the STL files on the Export STL tab.</span>")

else:  # Export STL
    with st.container(key="page_export"):
        st.markdown('<div class="page-title">Export STL files</div>'
                    '<div class="page-sub">Choose the mesh detail, then generate. Every model is checked before it can be downloaded.</div>', unsafe_allow_html=True)
        chips = [f"{s.shell.diameter_mm:.0f} mm ball", f"Walls {s.shell.min_wall_mm:.1f} to {s.shell.max_wall_mm:.1f} mm",
                 "Hanging loop" if s.loop.enabled else "No hanging loop", f"{s.led.diameter_mm:.0f} mm LED tea light"]
        st.markdown('<div class="chips">' + "".join(f'<span class="chip">{c}</span>' for c in chips) + "</div>", unsafe_allow_html=True)
        small_label("Mesh detail")
        qname = seg("Mesh detail", list(QUALITY), "quality", "Standard", label_visibility="collapsed")
        q = QUALITY[qname]
        from settings import QUALITY_RESOLUTION_MM
        est = 19.0 * (s.shell.diameter_mm / 100) ** 2 * (0.6 / QUALITY_RESOLUTION_MM[q]) ** 2
        st.caption(f"{QUALITY_NOTE[qname]} The complete package is roughly {est:.0f} MB.")
        gen_sig = hashlib.sha1((sig + q.value).encode()).hexdigest()
        if st.button("Generate STL files", type="primary", key="gen_btn"):
            analytics.track("generate_click", f"{qname} {s.shell.diameter_mm:.0f}mm")
            bar = st.progress(0.0, text="Starting")
            try:
                r = generate(img_bytes, s, q, progress=lambda f, m: bar.progress(min(f * 0.92, 0.92), text=m))
                bar.progress(0.94, text="Writing STL files")
                bundle = build_export_bundle(r)
                st.session_state.update(bundle=bundle, bundle_sig=gen_sig, gen_stats=r.stats,
                                        gen_parts=part_sizes(r), gen_reports={k: v.stats for k, v in r.reports.items()},
                                        gen_wall=s.shell.min_wall_mm, gen_dia=s.shell.diameter_mm)
                bar.progress(1.0, text="Done")
                analytics.track("generate_ok", f"{qname} {s.shell.diameter_mm:.0f}mm")
                bar.empty()
            except ExportBlocked as exc:
                bar.empty(); st.session_state.pop("bundle", None); st.error(str(exc))
            except (ImageError, SettingsError, GenerationError) as exc:
                bar.empty(); st.session_state.pop("bundle", None); st.error(str(exc))

        bundle = st.session_state.get("bundle")
        ready = bundle is not None
        if ready and st.session_state.get("bundle_sig") != gen_sig:
            st.markdown('<div class="notice">Your design or mesh detail changed after these files were made. Generate again to update them.</div>', unsafe_allow_html=True)
        if ready:
            rs = st.session_state["gen_reports"]
            body, cap = rs["body"], rs["cap"]
            items = [f"Closed, watertight surfaces <small>(main ball and cap)</small>",
                     "Every face points outward",
                     "Opening clear for the LED <small>(bore {:.0f} mm wide)</small>".format(body["bore_radius_mm"] * 2),
                     "Thinnest wall {:.2f} mm <small>(minimum {:.2f} mm)</small>".format(body["thinnest_wall_mm"], st.session_state["gen_wall"]),
                     "Overall width {:.1f} mm <small>(requested {:.0f} mm)</small>".format(body["max_xy_radius_mm"] * 2, st.session_state["gen_dia"]),
                     "Cap thread fits with no overlap <small>(checked by software)</small>"]
            st.markdown('<div class="checks">' + "".join(f'<div class="check" style="animation-delay:{i*0.07:.2f}s">{t}</div>' for i, t in enumerate(items)) + "</div>", unsafe_allow_html=True)

        files = bundle.files if ready else {}
        parts = st.session_state.get("gen_parts", {})
        mb = lambda b: f"{len(b) / 1e6:.1f} MB"
        dim = lambda k: " x ".join(f"{v:.0f}" for v in parts[k]) + " mm" if k in parts else ""

        def card(key, kind, tag, tagcls, title, desc, meta, fname, data, mime):
            with st.container(key=f"card_{key}"):
                st.markdown(f'<div class="xc"><span class="tag {tagcls}">{tag}</span>{theme.icon(kind)}'
                            f'<div class="body"><h4>{title}</h4><p>{desc}</p><div class="meta">{meta}</div></div></div>', unsafe_allow_html=True)
                if ready:
                    st.download_button("Download", data, file_name=fname, mime=mime, key=f"dl_{key}",
                                       on_click=analytics.track, args=("download", key))
                else:
                    st.markdown('<div class="locked">Generate your files to download this</div>', unsafe_allow_html=True)

        st.markdown("#### Your files")
        card("zip", "zip", "Recommended", "red", "Complete package",
             "All the STL files below plus the printing guide, in one download.",
             (f"{mb(bundle.zip_bytes)} - 4 STL files and a printing guide" if ready else "4 STL files and a printing guide"),
             FILENAMES["zip"], bundle.zip_bytes if ready else b"", "application/zip")
        cols = st.columns(4)
        with cols[0]:
            card("tile", "tile", "Print first", "", "Test tile", "A flat panel of your photo. Print it to judge detail and brightness before the full ornament.",
                 f"{dim('Test Tile')} - {mb(files[FILENAMES['tile']])}" if ready else "", FILENAMES["tile"], files.get(FILENAMES["tile"], b""), "model/stl")
        with cols[1]:
            card("main", "ball", "Print", "", "Main ball", "The hollow lithophane ball with its hanging loop. Opening faces the bed.",
                 f"{dim('Main Ball')} - {mb(files[FILENAMES['main']])}" if ready else "", FILENAMES["main"], files.get(FILENAMES["main"], b""), "model/stl")
        with cols[2]:
            card("cap", "cap", "Print", "", "Bottom cap", "Screws into the ball. Holds the LED tea light. Prints upside down.",
                 f"{dim('Bottom Cap')} - {mb(files[FILENAMES['cap']])}" if ready else "", FILENAMES["cap"], files.get(FILENAMES["cap"], b""), "model/stl")
        with cols[3]:
            card("assembly", "assembly", "Reference only", "dim", "Complete assembly", "Ball and cap together for checking the fit in your slicer. Do not print.",
                 mb(files[FILENAMES['assembly']]) if ready else "", FILENAMES["assembly"], files.get(FILENAMES["assembly"], b""), "model/stl")
        if ready:
            st.caption(f"{st.session_state['gen_stats']['triangles']:,} triangles in total. Files are in millimetres and already oriented for printing.")
