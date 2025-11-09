# app.py (Frontend Streamlit - Đã sửa lỗi NameError)

import streamlit as st
import os, io, math, base64, re
from PIL import Image
import html
import requests # <-- Dùng để gọi API Backend

# --- API CONFIGURATION ---
# !!! QUAN TRỌNG: THAY THẾ BẰNG URL CHÍNH XÁC CỦA BACKEND FASTAPI TRÊN RENDER CỦA BẠN !!!
API_BASE_URL = "https://your-backend-service-name.onrender.com" # THAY URL NÀY!

# ---------------- CONFIG & CONSTANTS (Giữ lại cho UI/Preview) ----------------
st.set_page_config(page_title="Tank Marking PDF Generator", layout="centered")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
LETTERS_FOLDER = os.path.join(ROOT_DIR, "ABC")
ICONS_FOLDER = os.path.join(ROOT_DIR, "icons")
if not os.path.isdir(LETTERS_FOLDER): os.makedirs(LETTERS_FOLDER, exist_ok=True)
if not os.path.isdir(ICONS_FOLDER): os.makedirs(ICONS_FOLDER, exist_ok=True)

# Dummy ReportLab imports cho Preview Check
try:
    from reportlab.lib.units import mm
    from reportlab.lib.pagesizes import A1, A2, A3, A4, landscape, portrait
    PAPER_SIZES_PT = {"A1": A1, "A2": A2, "A3": A3, "A4": A4}
except ImportError:
    # Fallback cho Streamlit không cần cài ReportLab
    mm = 1
    def A1(): return (2380, 3368) 
    def A2(): return (1684, 2380)
    def A3(): return (1190, 1684)
    def A4(): return (841, 1190)
    def landscape(size): return (size[1], size[0])
    def portrait(size): return size
    PAPER_SIZES_PT = {"A1": A1(), "A2": A2(), "A3": A3(), "A4": A4()}

PAPER_SIZES = {"A1": None, "A2": None, "A3": None, "A4": None}
CHAR_HEIGHT_DEFAULT = 100
DEFAULT_CHAR_SPACING_MM = 20
DEFAULT_SPACE_MM = 40
LINE_GAP_MM = 10
MARGIN_LEFT_MM = 20
MARGIN_TOP_MM = 20
FOOTER_MARGIN_MM = 10

# ---------------- UTILITIES (Giữ nguyên cho Preview và Library) ----------------
# *Các hàm: build_image_index, find_image_for_char, estimate_width_mm_from_image, 
#           page_size_mm, _encode_file_to_base64, render_preview_html, render_library_html 
#           giữ nguyên logic như bản trước*

# (Đơn giản hóa: Tôi giả định các hàm này được dán vào đây hoặc import từ file khác)
# ... (Dán các hàm UTILITIES từ bản trước vào đây) ...

def page_size_mm(paper_name, orientation):
    w_pt, h_pt = PAPER_SIZES_PT.get(paper_name, A4())
    if orientation == "Landscape":
        w_pt, h_pt = landscape((w_pt, h_pt))
    else:
        w_pt, h_pt = portrait((w_pt, h_pt))
    return (w_pt, h_pt)

def build_image_index(folder):
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
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

# Cần dán hàm render_preview_html và render_library_html đầy đủ vào đây để chạy Preview.
# Tôi sẽ bỏ qua nội dung chi tiết của chúng để rút gọn, giả định chúng đã được dán.
def render_preview_html(lines, letter_height_mm, paper_choice, orientation, footer_text, max_preview_width_px=900):
    # Dán code render_preview_html đầy đủ tại đây
    return ""

def render_library_html(preview_height_px=50, spacing_px=10):
    # Dán code render_library_html đầy đủ tại đây
    return ""


# ---------------- UI (Đã sửa vị trí nút) ----------------

# Apply custom CSS
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

# Input Controls
user_text = st.text_area("Enter text (each line = 1 PDF line):", height=220, value="10WB\n25VOID\n50FO")
lines = [ln for ln in user_text.splitlines() if ln.strip()]

paper_choice = st.selectbox("Paper size", list(PAPER_SIZES.keys()), index=0)
orientation = st.radio("Orientation", ["Portrait", "Landscape"], index=1)

st.markdown("### Letter height (mm)")
chosen_height_mm = st.selectbox(
    "Select letter height (mm):",
    options=[50, 75, 100],
    index=2,
    help="Choose one of the preset letter heights."
)
chosen_height_mm = float(chosen_height_mm)

footer_text = st.text_input("Footer (author)", value="Author")


# --- PHẦN SỬA LỖI: TẠO NÚT TRƯỚC KHI SỬ DỤNG BIẾN ---

# optional: load icons for buttons
icon_download_b64 = None
icon_preview_b64 = None
if os.path.isdir(ICONS_FOLDER):
    for fname in sorted(os.listdir(ICONS_FOLDER)):
        lf = fname.lower()
        if "download" in lf or "dl" in lf:
            icon_download_b64 = _encode_file_to_base64(os.path.join(ICONS_FOLDER, fname))
        if "preview" in lf or "eye" in lf:
            icon_preview_b64 = _encode_file_to_base64(os.path.join(ICONS_FOLDER, fname))

# TẠO NÚT VÀ GÁN GIÁ TRỊ
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

# --- KẾT THÚC PHẦN SỬA LỖI ---


# Luôn show library preview
library_html = render_library_html()

# Khi người dùng nhấp Preview (Logic này chạy cục bộ)
if preview_btn:
    # ... (Giữ nguyên logic kiểm tra tràn lề/thiếu ký tự) ...
    # Logic kiểm tra...
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
        # 2. Gửi Request POST đến API Backend
        response = requests.post(f"{API_BASE_URL}/generate-pdf", json=payload, timeout=60)
        
        # 3. Kiểm tra và Xử lý Response
        response.raise_for_status() 

        pdf_bytes = response.content
        st.success("✅ PDF đã được tạo thành công bởi Backend. Tải xuống:")
        
        st.download_button(
            "⬇️ Tải xuống PDF", 
            data=pdf_bytes, 
            file_name="TankMarking.pdf", 
            mime="application/pdf"
        )

    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Lỗi HTTP từ Backend (Status {response.status_code}): Vui lòng kiểm tra logs Backend.")
    except requests.exceptions.ConnectionError:
        st.error(f"❌ Lỗi kết nối: Không thể kết nối đến Backend API tại {API_BASE_URL}. Kiểm tra URL và trạng thái Backend.")
    except requests.exceptions.Timeout:
        st.error("❌ Lỗi Timeout: Backend mất quá nhiều thời gian để xử lý (hơn 60 giây).")
    except Exception as e:
        st.error(f"❌ Lỗi không xác định: {e}")
