# app.py (Frontend Streamlit - Đã sửa để gọi API Backend)

import streamlit as st
import os, io, math, base64, re
from PIL import Image
import html
import requests # <-- Dùng để gọi API Backend

# --- API CONFIGURATION ---
# !!! QUAN TRỌNG: THAY THẾ BẰNG URL CHÍNH XÁC CỦA BACKEND FASTAPI TRÊN RENDER CỦA BẠN !!!
API_BASE_URL = "https://tank-marking-backend-1.onrender.com" # Thay thế URL này!

# ---------------- CONFIG & CONSTANTS (Giữ lại cho UI/Preview) ----------------
st.set_page_config(page_title="Tank Marking PDF Generator", layout="centered")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LETTERS_FOLDER = os.path.join(ROOT_DIR, "ABC")
os.makedirs(LETTERS_FOLDER, exist_ok=True)

ICONS_FOLDER = os.path.join(ROOT_DIR, "icons")
if not os.path.isdir(ICONS_FOLDER):
    os.makedirs(ICONS_FOLDER, exist_ok=True)

# Chỉ cần giá trị key, không cần giá trị pt cho frontend preview
PAPER_SIZES = {"A1": None, "A2": None, "A3": None, "A4": None} 
CHAR_HEIGHT_DEFAULT = 100
DEFAULT_CHAR_SPACING_MM = 20
DEFAULT_SPACE_MM = 40
LINE_GAP_MM = 10
MARGIN_LEFT_MM = 20
MARGIN_TOP_MM = 20
FOOTER_MARGIN_MM = 10

# ---------------- UTILITIES (CHỈ DÀNH CHO PREVIEW CỤC BỘ) ----------------
# Các hàm này cần giữ lại để xử lý Preview và tính toán tràn lề (Overflow Check)

# Bổ sung các thư viện Reportlab ảo (Dummy) để tránh lỗi nếu không muốn cài Reportlab cho Frontend
try:
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import A1, A2, A3, A4, landscape, portrait
    PAPER_SIZES_PT = {"A1": A1, "A2": A2, "A3": A3, "A4": A4}
except ImportError:
    st.error("Lỗi: ReportLab không được cài đặt. Preview và Check có thể không chính xác.")
    mm = 1
    def A1(): return (2380, 3368) # Giá trị dummy
    def A2(): return (1684, 2380)
    def A3(): return (1190, 1684)
    def A4(): return (841, 1190)
    def landscape(size): return (size[1], size[0])
    def portrait(size): return size
    PAPER_SIZES_PT = {"A1": A1(), "A2": A2(), "A3": A3(), "A4": A4()}

def page_size_mm(paper_name, orientation):
    w_pt, h_pt = PAPER_SIZES_PT.get(paper_name, A4())
    if orientation == "Landscape":
        w_pt, h_pt = landscape((w_pt, h_pt))
    else:
        w_pt, h_pt = portrait((w_pt, h_pt))
    # Trả về kích thước tính bằng point (pt)
    return (w_pt, h_pt)

def build_image_index(folder):
    # Giữ lại logic này cho Preview/Library
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
    if not ch: return None
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

def _encode_file_to_base64(path):
    # Dùng cho việc hiển thị ảnh Preview
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

def render_preview_html(lines, letter_height_mm, paper_choice, orientation, footer_text, max_preview_width_px=900):
    # Giữ nguyên logic render HTML Preview
    # Cần: page_size_mm, estimate_width_mm_from_image, find_image_for_char, _encode_file_to_base64
    px_per_mm = 2.5
    page_w_pt, page_h_pt = page_size_mm(paper_choice, orientation)
    page_w_mm = (page_w_pt / mm)
    # ... (giữ nguyên logic render HTML Preview) ...
    
    # ... (Phần còn lại của hàm render_preview_html) ...
    # constants
    page_h_mm = (page_h_pt / mm)
    page_w_px = int(page_w_mm * px_per_mm)
    page_h_px = int(page_h_mm * px_per_mm)
    draw_h_px = int(letter_height_mm * px_per_mm)
    gap_px = int(LINE_GAP_MM * px_per_mm)
    margin_left_px = int(MARGIN_LEFT_MM * px_per_mm)
    margin_top_px = int(MARGIN_TOP_MM * px_per_mm)
    available_width_mm = page_w_mm - 2 * MARGIN_LEFT_MM

    scale = 1.0
    if page_w_px > max_preview_width_px:
        scale = max_preview_width_px / page_w_px
    if scale < 0.25:
        scale = 0.25

    scaled_page_w_px = int(page_w_px * scale)
    scaled_page_h_px = int(page_h_px * scale)

    html_blocks = []
    html_blocks.append(f"""
    <div style="display:flex;justify-content:center;padding:12px;">
      <div style="width:{scaled_page_w_px + 2*margin_left_px + 40}px; max-width:100%; height:70vh; overflow-y:auto; overflow-x:hidden; border-radius:6px;">
        <div style="width:{page_w_px}px; height:{page_h_px}px; background:#fff;
                     box-shadow:0 0 14px rgba(0,0,0,0.45); position:relative;
                     padding:{margin_top_px}px {margin_left_px}px; overflow:hidden;
                     transform:scale({scale}); transform-origin:top left; margin:0 auto;">
    """)

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
    # Giữ nguyên logic render Library Preview
    global IMAGE_INDEX
    IMAGE_INDEX = build_image_index(LETTERS_FOLDER)

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

# Xóa các biến header_bg_b64, custom_css và logic liên quan đến ICONS_FOLDER nếu bạn đã bỏ thư mục icons
# Hoặc giữ lại nếu bạn vẫn muốn dùng tùy chỉnh UI
header_bg_b64 = None 
if os.path.isdir(ICONS_FOLDER):
    header_candidates = [f for f in os.listdir(ICONS_FOLDER) if f.lower().endswith(".png")]
    header_candidates = sorted(header_candidates)
    if header_candidates:
        header_bg_b64 = _encode_file_to_base64(os.path.join(ICONS_FOLDER, header_candidates[0]))

custom_css = """<style>.streamlit-expanderHeader {font-weight:600}</style>"""
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

# --- Xử lý Letter height ĐƠN GIẢN HÓA (Đã bỏ logic quick_text phức tạp) ---
st.markdown("### Letter height (mm)")
chosen_height_mm = st.selectbox(
    "Select letter height (mm):",
    options=[50, 75, 100],
    index=2,
    help="Choose one of the preset letter heights."
)
# Đảm bảo nó là float để gửi lên API
chosen_height_mm = float(chosen_height_mm)


# Xử lý biến quick_text (Đã bị loại bỏ trong logic mới)
# Bạn CẦN xóa đoạn code sau để tránh lỗi nếu nó vẫn còn trong file của bạn:
# if "quick_text" in st.session_state:
#     quick_text = st.session_state["quick_text"]
#     st.experimental_rerun()
# ... (và logic try/except parse quick_text)

footer_text = st.text_input("Footer (author)", value="Author")

# optional: load icons for buttons (giữ lại nếu có thư mục icons)
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
        # Đảm bảo gen_pdf_btn LUÔN được gán giá trị ở đây
        gen_pdf_btn = st.button("Generate PDF (download)", key="gen")


# Always show library preview at bottom (bắt buộc phải chạy)
library_html = render_library_html()

# Khi người dùng nhấp Preview (Logic này chạy cục bộ)
if preview_btn:
    # Logic kiểm tra tràn lề/thiếu ký tự (Check)
    IMAGE_INDEX = build_image_index(LETTERS_FOLDER)
    missing_chars = set()
    overflow_lines = {}
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

    # Hiển thị kết quả Check
    if missing_chars:
        st.markdown(f"<div style='color:white;background:#b71c1c;padding:8px;border-radius:6px;'>❌ Missing characters: {', '.join(sorted(missing_chars))}</div>", unsafe_allow_html=True)
    if overflow_lines:
        details = "<br>".join([f"Line {ln}: overflow {val} mm" for ln, val in overflow_lines.items()])
        st.markdown(f"<div style='color:#111;background:#ffd54f;padding:8px;border-radius:6px;'>⚠️ {len(overflow_lines)} line(s) exceed page width.<br>{details}</div>", unsafe_allow_html=True)
    if not missing_chars and not overflow_lines:
        st.success("✅ All checks passed — ready to generate PDF.")

    # Hiển thị Preview
    st.markdown("### PDF Preview")
    preview_html = render_preview_html(lines, chosen_height_mm, paper_choice, orientation, footer_text, max_preview_width_px=900)
    st.markdown(preview_html, unsafe_allow_html=True)

    st.markdown(library_html, unsafe_allow_html=True)
else:
    # Luôn hiển thị Library Preview khi không ở chế độ Preview
    st.markdown("<div style='color:#444;margin-top:12px;'>Tip: press <strong>Preview</strong> to see the page scaled to fit horizontally. Vertical scrolling will appear when content is tall.</div>", unsafe_allow_html=True)
    st.markdown(library_html, unsafe_allow_html=True)


# --- GENERATE PDF BUTTON (Gọi API) ---
if gen_pdf_btn:
    st.info("Đang gửi yêu cầu tạo PDF tới Backend...")
    
    # 1. Chuẩn bị Dữ liệu (Payload)
    payload = {
        "lines": lines,
        "letter_height_mm": chosen_height_mm,
        "paper_choice": paper_choice,
        "orientation": orientation,
        "footer_text": footer_text
    }
    
    try:
        # 2. Gửi Request POST đến API Backend (Endpoint đã đổi thành /generate-pdf)
        response = requests.post(f"{API_BASE_URL}/generate-pdf", json=payload, timeout=60)
        
        # 3. Kiểm tra và Xử lý Response
        response.raise_for_status() # Bắt lỗi HTTP status code 4xx/5xx

        pdf_bytes = response.content
        st.success("✅ PDF đã được tạo thành công bởi Backend. Tải xuống:")
        
        # Nút Download
        st.download_button(
            "⬇️ Tải xuống PDF", 
            data=pdf_bytes, 
            file_name="TankMarking.pdf", 
            mime="application/pdf"
        )

    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Lỗi HTTP từ Backend (Status {response.status_code}): Vui lòng kiểm tra logs Backend.")
        # if response.text: st.code(response.text)
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Lỗi kết nối: Không thể kết nối đến Backend API tại {API_BASE_URL}. Kiểm tra URL và trạng thái Backend.")
    except requests.exceptions.Timeout:
        st.error("❌ Lỗi Timeout: Backend mất quá nhiều thời gian để xử lý (hơn 60 giây).")
    except Exception as e:
        st.error(f"❌ Lỗi không xác định: {e}")

# Footer small help (English)
