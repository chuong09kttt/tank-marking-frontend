
# tank_marking_pdf_final_v3.py (updated per request)
import streamlit as st
import os, io, math, base64, re
from PIL import Image
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.pagesizes import A1, A2, A3, A4, landscape, portrait
import html

# ---------------- CONFIG ----------------
st.set_page_config(page_title="Tank Marking PDF Generator", layout="centered")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LETTERS_FOLDER = os.path.join(ROOT_DIR, "ABC")
os.makedirs(LETTERS_FOLDER, exist_ok=True)

ICONS_FOLDER = os.path.join(ROOT_DIR, "icons")  # optional icons/backgrounds
if not os.path.isdir(ICONS_FOLDER):
    os.makedirs(ICONS_FOLDER, exist_ok=True)

PAPER_SIZES = {"A1": A1, "A2": A2, "A3": A3, "A4": A4}
CHAR_HEIGHT_OPTIONS = [50, 75, 100, 150]
CHAR_HEIGHT_DEFAULT = 100
DEFAULT_CHAR_SPACING_MM = 20
DEFAULT_SPACE_MM = 40
LINE_GAP_MM = 10
MARGIN_LEFT_MM = 20
MARGIN_TOP_MM = 20
FOOTER_MARGIN_MM = 10

# ---------------- Utilities ----------------
def build_image_index(folder):
    """
    Build index mapping filename (without ext) -> path.
    Only include image files present in folder, sorted by filename.
    """
    idx = {}
    try:
        files = sorted([f for f in os.listdir(folder) if f.lower().endswith((".png", ".jpg", ".jpeg"))])
    except Exception:
        files = []
    for fname in files:
        key = os.path.splitext(fname)[0].lower()
        idx[key] = os.path.join(folder, fname)
    return idx

IMAGE_INDEX = build_image_index(LETTERS_FOLDER)

def find_image_for_char(ch):
    if not ch:
        return None
    special_map = {".": "_", "/": "#"}
    key = special_map.get(ch, ch).lower()
    return IMAGE_INDEX.get(key)

def estimate_width_mm_from_image(path, letter_height_mm):
    try:
        with Image.open(path) as im:
            w, h = im.size
            return (w / h) * letter_height_mm
    except Exception:
        return letter_height_mm

def page_size_mm(paper_name, orientation):
    w_pt, h_pt = PAPER_SIZES[paper_name]
    if orientation == "Landscape":
        w_pt, h_pt = landscape((w_pt, h_pt))
    else:
        w_pt, h_pt = portrait((w_pt, h_pt))
    return (w_pt, h_pt)

def mm_to_pt(x_mm):
    return x_mm * mm

# ---------------- PDF generation ----------------
def generate_pdf(lines, letter_height_mm, paper_choice, orientation, footer_text):
    buffer = io.BytesIO()
    page_w_pt, page_h_pt = page_size_mm(paper_choice, orientation)
    c = canvas.Canvas(buffer, pagesize=(page_w_pt, page_h_pt))

    y_top = page_h_pt - mm_to_pt(MARGIN_TOP_MM)
    y = y_top
    draw_h_pt = mm_to_pt(letter_height_mm)
    line_spacing_pt = draw_h_pt + mm_to_pt(2 * LINE_GAP_MM)
    available_width_pt = page_w_pt - 2 * mm_to_pt(MARGIN_LEFT_MM)
    page_number = 1

    for line in lines:
        total_line_width_mm = 0.0
        for ch in line:
            if ch == " ":
                total_line_width_mm += DEFAULT_SPACE_MM
            else:
                img_path = find_image_for_char(ch)
                if img_path:
                    total_line_width_mm += estimate_width_mm_from_image(img_path, letter_height_mm)
                else:
                    total_line_width_mm += letter_height_mm
                total_line_width_mm += DEFAULT_CHAR_SPACING_MM
        total_line_width_pt = mm_to_pt(total_line_width_mm)

        if total_line_width_pt > available_width_pt or y - line_spacing_pt < mm_to_pt(FOOTER_MARGIN_MM):
            c.setFont("Helvetica", 10)
            footer_str = f"Page {page_number} — {paper_choice} — {footer_text}.NCC"
            c.drawCentredString(page_w_pt / 2, mm_to_pt(FOOTER_MARGIN_MM), footer_str)
            c.showPage()
            page_number += 1
            y = y_top

        x = mm_to_pt(MARGIN_LEFT_MM)
        for i, ch in enumerate(line):
            if ch == " ":
                x += mm_to_pt(DEFAULT_SPACE_MM)
                continue
            img_path = find_image_for_char(ch)
            if img_path:
                try:
                    with Image.open(img_path) as im:
                        w_px, h_px = im.size
                        aspect = w_px / h_px
                        draw_w_pt = draw_h_pt * aspect
                    c.drawImage(img_path, x, y - draw_h_pt, width=draw_w_pt, height=draw_h_pt, mask='auto')
                except Exception:
                    c.setFillColorRGB(0, 0, 0)
                    c.rect(x, y - draw_h_pt, draw_h_pt, draw_h_pt, fill=True, stroke=False)
                    c.setFillColorRGB(1, 1, 1)
                    c.setFont("Helvetica-Bold", draw_h_pt * 0.5)
                    c.drawCentredString(x + draw_h_pt / 2, y - draw_h_pt / 2.8, ch)
                    draw_w_pt = draw_h_pt
            else:
                c.setFillColorRGB(0, 0, 0)
                c.rect(x, y - draw_h_pt, draw_h_pt, draw_h_pt, fill=True, stroke=False)
                c.setFillColorRGB(1, 1, 1)
                c.setFont("Helvetica-Bold", draw_h_pt * 0.5)
                c.drawCentredString(x + draw_h_pt / 2, y - draw_h_pt / 2.8, ch)
                draw_w_pt = draw_h_pt

            next_ch = line[i + 1] if i + 1 < len(line) else ""
            if next_ch == " ":
                x += draw_w_pt
            else:
                x += draw_w_pt + mm_to_pt(DEFAULT_CHAR_SPACING_MM)

        line_y = y - draw_h_pt - mm_to_pt(LINE_GAP_MM)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(0.5)
        c.line(mm_to_pt(MARGIN_LEFT_MM), line_y, page_w_pt - mm_to_pt(MARGIN_LEFT_MM), line_y)
        y -= (draw_h_pt + mm_to_pt(2 * LINE_GAP_MM))

    c.setFont("Helvetica", 10)
    footer_str = f"Page {page_number} — {paper_choice} — {footer_text}.NCC"
    c.drawCentredString(page_w_pt / 2, mm_to_pt(FOOTER_MARGIN_MM), footer_str)

    c.save()
    buffer.seek(0)
    return buffer

# ---------------- HTML Preview ----------------
def _encode_file_to_base64(path):
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

def render_preview_html(lines, letter_height_mm, paper_choice, orientation, footer_text, max_preview_width_px=900):
    """
    Render HTML preview including:
    - Main PDF preview (scaled white page on black background; auto scale to fit max_preview_width_px)
    - horizontal scrolling hidden; vertical scroll allowed
    """
    # constants
    px_per_mm = 2.5  # base scale for on-screen view (we will scale down if too large)
    page_w_pt, page_h_pt = page_size_mm(paper_choice, orientation)
    page_w_mm = (page_w_pt / mm)
    page_h_mm = (page_h_pt / mm)

    # convert mm → px at base scale
    page_w_px = int(page_w_mm * px_per_mm)
    page_h_px = int(page_h_mm * px_per_mm)
    draw_h_px = int(letter_height_mm * px_per_mm)
    gap_px = int(LINE_GAP_MM * px_per_mm)
    margin_left_px = int(MARGIN_LEFT_MM * px_per_mm)
    margin_top_px = int(MARGIN_TOP_MM * px_per_mm)
    available_width_mm = page_w_mm - 2 * MARGIN_LEFT_MM

    # compute scale factor so page fits within max_preview_width_px (no horizontal scrollbar)
    scale = 1.0
    if page_w_px > max_preview_width_px:
        scale = max_preview_width_px / page_w_px
    if scale < 0.25:
        scale = 0.25

    scaled_page_w_px = int(page_w_px * scale)
    scaled_page_h_px = int(page_h_px * scale)

    # Build HTML: main container forces vertical scroll only (overflow-y:auto; overflow-x:hidden)
    html_blocks = []
    html_blocks.append(f"""
    <div style="display:flex;justify-content:center;padding:12px;">
      <div style="width:{scaled_page_w_px + 2*margin_left_px + 40}px; max-width:100%; height:70vh; overflow-y:auto; overflow-x:hidden; border-radius:6px;">
        <div style="width:{page_w_px}px; height:{page_h_px}px; background:#fff;
                    box-shadow:0 0 14px rgba(0,0,0,0.45); position:relative;
                    padding:{margin_top_px}px {margin_left_px}px; overflow:hidden;
                    transform:scale({scale}); transform-origin:top left; margin:0 auto;">
    """)

    # lines
    for idx, line in enumerate(lines):
        line_html = f"<div style='display:flex;align-items:center;white-space:nowrap;margin-bottom:{gap_px}px;'>"
        for ch in line:
            if ch == " ":
                line_html += f"<div style='display:inline-block;width:{int(DEFAULT_SPACE_MM*px_per_mm)}px;'></div>"
            else:
                img_path = find_image_for_char(ch)
                if img_path and os.path.exists(img_path):
                    try:
                        with Image.open(img_path) as im:
                            w_px, h_px = im.size
                            aspect = w_px / h_px
                            draw_w_px = int(draw_h_px * aspect)
                        b64 = _encode_file_to_base64(img_path)
                        if b64:
                            safe_b64 = html.escape(b64)
                            line_html += f"<img src='data:image/png;base64,{safe_b64}' style='height:{draw_h_px}px;margin-right:{int(DEFAULT_CHAR_SPACING_MM*px_per_mm)}px;display:inline-block;'/>"
                        else:
                            line_html += f"<div style='width:{draw_h_px}px;height:{draw_h_px}px;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;margin-right:{int(DEFAULT_CHAR_SPACING_MM*px_per_mm)}px;font-weight:bold;'>{html.escape(ch)}</div>"
                    except Exception:
                        line_html += f"<div style='width:{draw_h_px}px;height:{draw_h_px}px;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;margin-right:{int(DEFAULT_CHAR_SPACING_MM*px_per_mm)}px;font-weight:bold;'>{html.escape(ch)}</div>"
                else:
                    line_html += f"<div style='width:{draw_h_px}px;height:{draw_h_px}px;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;margin-right:{int(DEFAULT_CHAR_SPACING_MM*px_per_mm)}px;font-weight:bold;'>{html.escape(ch)}</div>"
        line_html += "</div>"

        # calculate total width (for overflow highlight)
        total_w_mm = 0.0
        for ch in line:
            if ch == " ":
                total_w_mm += DEFAULT_SPACE_MM
            else:
                img_path = find_image_for_char(ch)
                if img_path:
                    total_w_mm += estimate_width_mm_from_image(img_path, letter_height_mm)
                else:
                    total_w_mm += letter_height_mm
                total_w_mm += DEFAULT_CHAR_SPACING_MM
        if total_w_mm > available_width_mm:
            line_html = f"<div style='background:rgba(255,200,0,0.4);padding:2px;border-radius:3px'>{line_html}</div>"

        html_blocks.append(line_html + f"<div style='width:100%;height:1px;background:#000;margin-top:{gap_px}px;'></div>")

    html_blocks.append("</div>")
    return "\n".join(html_blocks)

def render_library_html(preview_height_px=50, spacing_px=10):
    """
    Render the 'Tank Marking Library Preview' showing only images found in ABC,
    ordered by filename. Always displayed at bottom of UI.
    """
    # rebuild index to ensure current files
    global IMAGE_INDEX
    IMAGE_INDEX = build_image_index(LETTERS_FOLDER)

    # prepare sorted keys (in order of filenames)
    keys = [k for k in IMAGE_INDEX.keys()]
    library_html = "<div style='background:#fff;border-top:2px solid #ccc;margin-top:20px;padding:10px;'>"
    library_html += "<div style='font-weight:bold;margin-bottom:6px;color:#333;'>Tank Marking Library Preview</div>"
    library_html += "<div style='display:flex;overflow-x:auto;white-space:nowrap;padding:5px;'>"

    if not keys:
        library_html += "<div style='color:#666;padding:8px;'>No images found in folder 'ABC'. Add .png/.jpg files named for characters (e.g. A.png, 1.png, _.png for '.') to the folder.</div>"
    else:
        for key in keys:
            img_path = IMAGE_INDEX.get(key)
            if img_path and os.path.exists(img_path):
                b64 = _encode_file_to_base64(img_path)
                if b64:
                    try:
                        with Image.open(img_path) as im:
                            w_px, h_px = im.size
                            aspect = w_px / h_px
                            draw_w_px = int(preview_height_px * aspect)
                    except Exception:
                        draw_w_px = preview_height_px
                    safe_b64 = html.escape(b64)
                    library_html += f"<img src='data:image/png;base64,{safe_b64}' style='height:{preview_height_px}px;margin-right:{spacing_px}px;display:inline-block;'/>"
                else:
                    library_html += f"<div style='width:{preview_height_px}px;height:{preview_height_px}px;background:#eee;color:#000;display:flex;align-items:center;justify-content:center;margin-right:{spacing_px}px;font-size:12px;font-weight:bold;'>{html.escape(key)}</div>"
            else:
                library_html += f"<div style='width:{preview_height_px}px;height:{preview_height_px}px;background:#eee;color:#000;display:flex;align-items:center;justify-content:center;margin-right:{spacing_px}px;font-size:12px;font-weight:bold;'>{html.escape(key)}</div>"

    library_html += "</div></div>"
    return library_html

# ---------------- UI ----------------
# optional: load a subtle header background if available
header_bg_b64 = None
if os.path.isdir(ICONS_FOLDER):
    header_candidates = [f for f in os.listdir(ICONS_FOLDER) if f.lower().endswith(".png")]
    header_candidates = sorted(header_candidates)
    if header_candidates:
        header_bg_b64 = _encode_file_to_base64(os.path.join(ICONS_FOLDER, header_candidates[0]))

# apply small CSS to make UI nicer and use header background if available
custom_css = """
<style>
.streamlit-expanderHeader {font-weight:600}
</style>
"""
if header_bg_b64:
    custom_css += f"""
    <style>
    .header-banner {{
        background-image: url("data:image/png;base64,{header_bg_b64}");
        background-repeat: no-repeat;
        background-position: right center;
        background-size: 180px auto;
        opacity: 0.18;
        border-radius: 8px;
        padding: 12px;
    }}
    </style>
    """

st.markdown(custom_css, unsafe_allow_html=True)

st.markdown("<div class='header-banner'><h1 style='margin:6px 0;'>Tank Marking PDF Generator</h1></div>", unsafe_allow_html=True)


# Text area input
user_text = st.text_area("Enter text (each line = 1 PDF line):", height=220, value="10WB\n25VOID\n50FO")
lines = [ln for ln in user_text.splitlines() if ln.strip()]

paper_choice = st.selectbox("Paper size", list(PAPER_SIZES.keys()), index=0)
orientation = st.radio("Orientation", ["Portrait", "Landscape"], index=1)

# Letter height: single editable "Quick pick" field with suggestion buttons (choose or type)
# --- Letter height (mm): choose from combobox ---
st.markdown("### Letter height (mm)")
chosen_height_mm = st.selectbox(
    "Select letter height (mm):",
    options=[50, 75, 100],
    index=2,  # default = 75
    help="Choose one of the preset letter heights."
)


# If session_state was set by a suggestion button, propagate to quick_text variable used below
if "quick_text" in st.session_state:
    quick_text = st.session_state["quick_text"]
    # reflect in UI by writing a small script (best-effort visual sync)
    st.experimental_rerun()

# parse the chosen height
try:
    if quick_text and re.match(r'^\d+(\.\d+)?$', quick_text.strip()):
        chosen_height_mm = float(quick_text.strip())
    else:
        # fallback to default
        chosen_height_mm = float(CHAR_HEIGHT_DEFAULT)
except Exception:
    chosen_height_mm = float(CHAR_HEIGHT_DEFAULT)

if float(chosen_height_mm).is_integer():
    chosen_height_mm = int(chosen_height_mm)

footer_text = st.text_input("Footer (author)", value="Author")

# optionally show small icons next to the actions if available
icon_download_b64 = None
icon_preview_b64 = None
if os.path.isdir(ICONS_FOLDER):
    for fname in sorted(os.listdir(ICONS_FOLDER)):
        lf = fname.lower()
        if "download" in lf or "dl" in lf:
            icon_download_b64 = _encode_file_to_base64(os.path.join(ICONS_FOLDER, fname))
        if "preview" in lf or "eye" in lf:
            icon_preview_b64 = _encode_file_to_base64(os.path.join(ICONS_FOLDER, fname))

# UI buttons
col_buttons = st.columns([1, 1])
with col_buttons[0]:
    if icon_preview_b64:
        preview_btn = st.button("Preview", key="preview", help="Preview on-screen (scaled to fit).")
    else:
        preview_btn = st.button("Preview", key="preview")
with col_buttons[1]:
    if icon_download_b64:
        gen_pdf_btn = st.button("Generate PDF", key="gen")
    else:
        gen_pdf_btn = st.button("Generate PDF (download)", key="gen")

# Always show library preview at bottom (but we'll also include it after preview)
library_html = render_library_html()

# When user clicks Preview: run checks and show scaled preview
if preview_btn:
    # rebuild the index in case files changed
    IMAGE_INDEX = build_image_index(LETTERS_FOLDER)

    missing_chars = set()
    overflow_lines = {}
    # compute available width in mm based on selected paper/orientation
    page_w_pt, page_h_pt = page_size_mm(paper_choice, orientation)
    available_width_mm = (page_w_pt / mm)
    available_width_mm -= 2 * MARGIN_LEFT_MM

    for i, line in enumerate(lines):
        x_mm = 0.0
        for j, ch in enumerate(line):
            if ch == " ":
                x_mm += DEFAULT_SPACE_MM
                continue
            img = find_image_for_char(ch)
            if not img:
                missing_chars.add(ch)
                w_mm = chosen_height_mm
            else:
                w_mm = estimate_width_mm_from_image(img, chosen_height_mm)
            next_ch = line[j+1] if j+1 < len(line) else ""
            if next_ch == " ":
                x_mm += w_mm
            else:
                x_mm += w_mm + DEFAULT_CHAR_SPACING_MM
        if x_mm > available_width_mm:
            overflow_lines[i+1] = round(x_mm - available_width_mm, 1)

    # display checks (English)
    if missing_chars:
        st.markdown(f"<div style='color:white;background:#b71c1c;padding:8px;border-radius:6px;'>❌ Missing characters: {', '.join(sorted(missing_chars))}</div>", unsafe_allow_html=True)
    if overflow_lines:
        details = "<br>".join([f"Line {ln}: overflow {val} mm" for ln, val in overflow_lines.items()])
        st.markdown(f"<div style='color:#111;background:#ffd54f;padding:8px;border-radius:6px;'>⚠️ {len(overflow_lines)} line(s) exceed page width.<br>{details}</div>", unsafe_allow_html=True)
    if not missing_chars and not overflow_lines:
        st.success("✅ All checks passed — ready to generate PDF.")

    st.markdown("### PDF Preview")
    preview_html = render_preview_html(lines, chosen_height_mm, paper_choice, orientation, footer_text, max_preview_width_px=900)
    st.markdown(preview_html, unsafe_allow_html=True)

    # show library after preview as well
    st.markdown(library_html, unsafe_allow_html=True)
else:
    # even when not previewing, still show a compact note and the library preview (always visible)
    st.markdown("<div style='color:#444;margin-top:12px;'>Tip: press <strong>Preview</strong> to see the page scaled to fit horizontally. Vertical scrolling will appear when content is tall.</div>", unsafe_allow_html=True)
    st.markdown(library_html, unsafe_allow_html=True)

# Generate PDF button action
if gen_pdf_btn:
    # rebuild index again
    IMAGE_INDEX = build_image_index(LETTERS_FOLDER)
    pdf_buffer = generate_pdf(lines, chosen_height_mm, paper_choice, orientation, footer_text)
    st.success("✅ PDF generated — click below to download")
    st.download_button("⬇️ Download PDF", data=pdf_buffer, file_name="TankMarking.pdf", mime="application/pdf")

# Footer small help (English)
