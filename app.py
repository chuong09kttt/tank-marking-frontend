# app.py (Frontend Streamlit)

import streamlit as st
import os, io, math, base64, re
from PIL import Image
import html
import requests 
from reportlab.lib.units import mm # Giữ lại để tính toán pt/mm chính xác

# --- API CONFIGURATION ---
# !!! Đảm bảo URL này đã được xác nhận là đúng và đã hoạt động !!!
API_BASE_URL = "https://tank-marking-backend.onrender.com" 

# ---------------- CONFIG & CONSTANTS ----------------
st.set_page_config(page_title="Tank Marking PDF Generator", layout="centered")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_FOLDER = os.path.join(ROOT_DIR, "icons") 
if not os.path.isdir(ICONS_FOLDER): 
    os.makedirs(ICONS_FOLDER, exist_ok=True)

# Dummy ReportLab imports (cho tính toán kích thước)
try:
    from reportlab.lib.pagesizes import A1, A2, A3, A4, landscape, portrait
    PAPER_SIZES_PT = {"A1": A1, "A2": A2, "A3": A3, "A4": A4}
except ImportError:
    # Đổi các hàm dummy thành các TUPLE cố định
    A1 = (2380, 3368) 
    A2 = (1684, 2380)
    A3 = (1190, 1684)
    A4 = (841, 1190) # <-- A4 bây giờ là một TUPLE, không phải HÀM
    
    def landscape(size): 
        return (size[1], size[0])
    
    def portrait(size): 
        return size
    
    # Khởi tạo PAPER_SIZES_PT để lưu trữ các TUPLE này
    PAPER_SIZES_PT = {"A1": A1, "A2": A2, "A3": A3, "A4": A4}
    # CHÚ Ý: ĐÃ BỎ DẤU NGOẶC ĐƠN SAU A1, A2, A3, A4

PAPER_SIZES = {"A1": None, "A2": None, "A3": None, "A4": None}
DEFAULT_CHAR_SPACING_MM = 20
DEFAULT_SPACE_MM = 40
LINE_GAP_MM = 10
MARGIN_LEFT_MM = 20
MARGIN_TOP_MM = 20

# ---------------- UTILITIES (Load ảnh từ API) ----------------

def page_size_mm(paper_name, orientation):
    """Tính kích thước trang theo mm"""
    w_pt, h_pt = PAPER_SIZES_PT.get(paper_name, PAPER_SIZES_PT["A4"])
    if orientation == "Landscape":
        w_pt, h_pt = landscape((w_pt, h_pt))
    else:
        w_pt, h_pt = portrait((w_pt, h_pt))
    # Chuyển đổi từ points sang mm (1 point = 1/72 inch, 1 inch = 25.4 mm)
    w_mm = (w_pt / 72) * 25.4
    h_mm = (h_pt / 72) * 25.4
    return (w_mm, h_mm)

@st.cache_data(ttl=3600) # Cache kết quả trong 1 giờ
def fetch_available_chars():
    """Gọi API Backend để lấy danh sách tên file ảnh có sẵn."""
    try:
        response = requests.get(f"{API_BASE_URL}/available-chars", timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"❌ Could not fetch character list from Backend API. Please check backend logs. Status: {getattr(e.response, 'status_code', 'N/A')}")
        return []

def build_image_index_from_files(file_names):
    """
    Xây dựng index map key ký tự gốc (/, ., a, 1) -> tên file.
    Xử lý tên file 'slash.png' và tên file '_.png'.
    """
    idx = {}
    
    # Map từ tên file đã được mã hóa (ví dụ: '_') sang ký tự gốc ('.')
    REVERSE_MAP = {"_": "."}
    
    for file_name in file_names:
        base_name_lower = os.path.splitext(file_name)[0].lower()
        
        # 1. Key mặc định (cho a, b, c, 1, 2, 3, _)
        char_key = REVERSE_MAP.get(base_name_lower, base_name_lower)
        
        # 2. Xử lý tên file mới cho ký tự '/'
        if base_name_lower == 'slash':
            char_key = '/'
        
        # Lưu vào index: key (/, ., a, 1) -> file_name (A.png, SLASH.png, _.png)
        # char_key là '/', file_name là 'SLASH.png'
        if char_key not in idx:
            idx[char_key] = file_name
            
    return idx

# Khởi tạo Index ảnh dựa trên dữ liệu từ Backend
AVAILABLE_FILE_NAMES = fetch_available_chars()
IMAGE_INDEX_FRONTEND = build_image_index_from_files(AVAILABLE_FILE_NAMES)

def get_image_url(ch):
    """Lấy tên file từ index và tạo URL Backend."""
    
    # Ký tự tìm kiếm trong Index là ký tự gốc (chữ thường)
    search_key = ch.lower()

    # Tra cứu file_name (ví dụ: '/' tìm ra '#.png')
    file_name = IMAGE_INDEX_FRONTEND.get(search_key)
    
    if file_name:
        # Tạo URL từ tên file (ví dụ: .../static/ABC/#.png)
        return f"{API_BASE_URL}/static/ABC/{file_name}" 
    return None
    
def estimate_width_mm_from_char(ch, letter_height_mm):
    # Giả định tỉ lệ 1:1 cho tất cả ký tự trong Preview
    return letter_height_mm 

def _encode_file_to_base64(path):
    # Giữ lại hàm này cho việc load icon cục bộ
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

def render_preview_html(lines, letter_height_mm, paper_choice, orientation, footer_text, max_preview_width_px=900):
    px_per_mm = 2.5
    page_w_mm, page_h_mm = page_size_mm(paper_choice, orientation)
    
    scale = 1.0
    if page_w_mm * px_per_mm > max_preview_width_px:
        scale = max_preview_width_px / (page_w_mm * px_per_mm)
    if scale < 0.25: 
        scale = 0.25
    
    margin_left_px = int(MARGIN_LEFT_MM * px_per_mm)
    margin_top_px = int(MARGIN_TOP_MM * px_per_mm)
    
    html_blocks = []
    html_blocks.append(f"""
    <div style="display:flex;justify-content:center;padding:12px;">
      <div style="width:{int(page_w_mm * px_per_mm * scale) + 2*margin_left_px + 40}px; max-width:100%; height:70vh; overflow-y:auto; overflow-x:hidden; border-radius:6px;">
        <div style="width:{int(page_w_mm * px_per_mm)}px; height:{int(page_h_mm * px_per_mm)}px; background:#fff;
                     box-shadow:0 0 14px rgba(0,0,0,0.45); position:relative;
                     padding:{margin_top_px}px {margin_left_px}px; overflow:hidden;
                     transform:scale({scale}); transform-origin:top left; margin:0 auto;">
    """)
    
    available_width_mm = page_w_mm - 2 * MARGIN_LEFT_MM
    
    for idx, line in enumerate(lines):
        line_html = f"<div style='display:flex;align-items:center;white-space:nowrap;margin-bottom:{int(LINE_GAP_MM*px_per_mm)}px;'>"
        
        x_mm = 0.0
        for ch in line:
            if ch == " ":
                x_mm += DEFAULT_SPACE_MM
                line_html += f"<div style='display:inline-block;width:{int(DEFAULT_SPACE_MM*px_per_mm)}px;'></div>"
            else:
                draw_w_mm = estimate_width_mm_from_char(ch, letter_height_mm)
                draw_w_px = int(draw_w_mm * px_per_mm)
                
                img_url = get_image_url(ch)
                
                if img_url:
                    line_html += f"<img src='{img_url}' style='height:{int(letter_height_mm*px_per_mm)}px; margin-right:{int(DEFAULT_CHAR_SPACING_MM*px_per_mm)}px; display:inline-block;' onerror=\"this.style.border='2px solid red';\">"
                else:
                    line_html += f"<div style='width:{draw_w_px}px;height:{int(letter_height_mm*px_per_mm)}px;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;margin-right:{int(DEFAULT_CHAR_SPACING_MM*px_per_mm)}px;font-weight:bold;'>{html.escape(ch)}</div>"
                
                x_mm += draw_w_mm
                x_mm += DEFAULT_CHAR_SPACING_MM
        
        line_html += "</div>"

        if x_mm > available_width_mm:
            line_html = f"<div style='background:rgba(255,200,0,0.4);padding:2px;border-radius:3px'>{line_html}</div>"

        html_blocks.append(line_html + f"<div style='width:100%;height:1px;background:#000;margin-top:{int(LINE_GAP_MM*px_per_mm)}px;'></div>")

    html_blocks.append("</div></div>")
    return "\n".join(html_blocks)

def render_library_html(preview_height_px=50, spacing_px=10):
    """Render library chỉ với những ảnh có trong Backend."""
    keys = sorted(IMAGE_INDEX_FRONTEND.keys())
    library_html = "<div style='background:#fff;border-top:2px solid #ccc;margin-top:20px;padding:10px;'>"
    library_html += "<div style='font-weight:bold;margin-bottom:6px;color:#333;'>Tank Marking Library Preview (Loaded from Backend)</div>"
    library_html += "<div style='display:flex;overflow-x:auto;white-space:nowrap;padding:5px;'>"

    if not keys:
        library_html += "<div style='color:#666;padding:8px;'>No images found in the Backend ABC folder or connection failed.</div>"
    else:
        for key in keys: # key ở đây là ký tự gốc (ví dụ: '/', '.')
            img_url = get_image_url(key)
            
            # Nếu img_url vẫn là None (rất khó xảy ra nếu key đến từ index), chúng ta phải dùng fallback
            if not img_url:
                continue 

            library_html += f"""
            <div style='display:inline-block; margin-right:{spacing_px}px; text-align:center;'>
                <img src='{img_url}' style='height:{preview_height_px}px; display:block; margin-bottom: 2px;' onerror="this.style.border='2px solid red';">
                <span style='font-size:10px; color:#666;'>{html.escape(key)}</span>
            </div>
            """

    library_html += "</div></div>"
    return library_html

# ---------------- UI ----------------

# Apply custom CSS & Header
st.markdown("<div class='header-banner'><h1 style='margin:6px 0;'>Tank Marking PDF Generator</h1></div>", unsafe_allow_html=True)

# Input Controls
user_text = st.text_area("Enter text (each line = 1 PDF line):", height=220, value="10WB\n25VOID\n50FO")
lines = [ln for ln in user_text.splitlines() if ln.strip()]
paper_choice = st.selectbox("Paper size", list(PAPER_SIZES.keys()), index=0)
orientation = st.radio("Orientation", ["Portrait", "Landscape"], index=1)
st.markdown("### Letter height (mm)")
chosen_height_mm = float(st.selectbox(
    "Select letter height (mm):",
    options=[50, 75, 100],
    index=2
))
footer_text = st.text_input("Footer (author)", value="Author")

# TẠO NÚT VÀ GÁN GIÁ TRỊ
col_buttons = st.columns([1, 1])
with col_buttons[0]:
    preview_btn = st.button("Preview", key="preview")
with col_buttons[1]:
    gen_pdf_btn = st.button("Generate PDF (download)", key="gen")

# --- LOGIC SỬ DỤNG NÚT ---

library_html = render_library_html()

if preview_btn:
    missing_chars = set()
    overflow_lines = {}
    page_w_mm, page_h_mm = page_size_mm(paper_choice, orientation)
    available_width_mm = page_w_mm - 2 * MARGIN_LEFT_MM

    for i, line in enumerate(lines):
        x_mm = 0.0
        for ch in line:
            if ch == " ":
                x_mm += DEFAULT_SPACE_MM
                continue
            
            # Check if character is available in the filtered index
            if not get_image_url(ch): 
                missing_chars.add(ch)
            
            x_mm += estimate_width_mm_from_char(ch, chosen_height_mm)
            x_mm += DEFAULT_CHAR_SPACING_MM
        
        if x_mm > available_width_mm:
            overflow_lines[i+1] = round(x_mm - available_width_mm, 1)

    if missing_chars: 
        st.markdown(f"<div style='color:white;background:#b71c1c;padding:8px;border-radius:6px;'>❌ Missing characters: {', '.join(sorted(missing_chars))}</div>", unsafe_allow_html=True)
    if overflow_lines: 
        st.markdown(f"<div style='color:#111;background:#ffd54f;padding:8px;border-radius:6px;'>⚠️ {len(overflow_lines)} line(s) exceed page width.</div>", unsafe_allow_html=True)
    if not missing_chars and not overflow_lines: 
        st.success("✅ All checks passed.")
    
    st.markdown("### PDF Preview")
    preview_html = render_preview_html(lines, chosen_height_mm, paper_choice, orientation, footer_text, max_preview_width_px=900)
    st.markdown(preview_html, unsafe_allow_html=True)
    st.markdown(library_html, unsafe_allow_html=True)

else:
    st.markdown("<div style='color:#444;margin-top:12px;'>Tip: press <strong>Preview</strong> to see the page scaled to fit horizontally.</div>", unsafe_allow_html=True)
    st.markdown(library_html, unsafe_allow_html=True)

# --- GENERATE PDF BUTTON (Gọi API) ---
if gen_pdf_btn:
    st.info("Đang gửi yêu cầu tạo PDF tới Backend...")
    payload = {
        "lines": lines,
        "letter_height_mm": chosen_height_mm,
        "paper_choice": paper_choice,
        "orientation": orientation,
        "footer_text": footer_text
    }
    try:
        response = requests.post(f"{API_BASE_URL}/generate-pdf", json=payload, timeout=60)
        response.raise_for_status() 

        pdf_bytes = response.content
        st.success("✅ PDF đã được tạo thành công bởi Backend. Tải xuống:")
        st.download_button("⬇️ Tải xuống PDF", data=pdf_bytes, file_name="TankMarking.pdf", mime="application/pdf")

    except requests.exceptions.RequestException as e:
        status_code = getattr(e.response, 'status_code', 'N/A')
        st.error(f"❌ Lỗi kết nối hoặc HTTP ({status_code}): Kiểm tra URL Backend và logs.")
