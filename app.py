# app.py (Frontend Streamlit)

import streamlit as st
import os, io, math, base64, re
from PIL import Image
import html
import requests 
from reportlab.lib.units import mm # Giữ lại để tính toán pt/mm chính xác

# --- API CONFIGURATION ---
# !!! THAY THẾ BẰNG URL BACKEND CỦA BẠN !!!
API_BASE_URL = "https://tank-marking-backend.onrender.com"   

# ---------------- CONFIG & CONSTANTS ----------------
st.set_page_config(page_title="Tank Marking PDF Generator", layout="centered")
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
ICONS_FOLDER = os.path.join(ROOT_DIR, "icons") 
if not os.path.isdir(ICONS_FOLDER): os.makedirs(ICONS_FOLDER, exist_ok=True)

# Dummy ReportLab imports cho Preview Check (giữ nguyên)
try:
    from reportlab.lib.pagesizes import A1, A2, A3, A4, landscape, portrait
    PAPER_SIZES_PT = {"A1": A1, "A2": A2, "A3": A3, "A4": A4}
except ImportError:
    # Fallback
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

# --- UTILITIES MỚI (Load ảnh từ API) ---

def page_size_mm(paper_name, orientation):
    w_pt, h_pt = PAPER_SIZES_PT.get(paper_name, A4())
    if orientation == "Landscape":
        w_pt, h_pt = landscape((w_pt, h_pt))
    else:
        w_pt, h_pt = portrait((w_pt, h_pt))
    return (w_pt, h_pt)

def build_image_index_frontend():
    # Giả định danh sách ký tự phổ biến có trong Backend
    common_chars = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")
    special_map = {".": "_", "/": "#"}
    idx = {}
    
    # Map ký tự -> tên file (ví dụ: 'a' -> 'A.png')
    for ch in common_chars:
        idx[ch.lower()] = f"{ch.upper()}.png"
    for k, v in special_map.items():
        idx[k] = f"{v}.png"
    return idx

IMAGE_INDEX_FRONTEND = build_image_index_frontend()

def get_image_url(ch):
    """Tạo URL công khai cho ảnh từ Backend API"""
    if not ch: return None
    special_map = {".": "_", "/": "#"}
    key = special_map.get(ch, ch).lower()
    
    file_name = IMAGE_INDEX_FRONTEND.get(key) 
    
    if file_name:
        # Đường dẫn tĩnh từ Backend FastAPI: /static/ABC/
        return f"{API_BASE_URL}/static/ABC/{file_name}" 
    return None

def estimate_width_mm_from_char(ch, letter_height_mm):
    # Vì không đọc được file ảnh cục bộ, ta giả định tỉ lệ 1:1 cho tất cả ký tự trong Preview
    return letter_height_mm 

def _encode_file_to_base64(path):
    # Giữ lại hàm này cho việc load icon cục bộ
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    except Exception:
        return None

def render_preview_html(lines, letter_height_mm, paper_choice, orientation, footer_text, max_preview_width_px=900):
    # Hàm này dùng để hiển thị HTML preview trên Streamlit
    px_per_mm = 2.5
    page_w_pt, page_h_pt = page_size_mm(paper_choice, orientation)
    page_w_mm = (page_w_pt / mm)
    page_h_mm = (page_h_pt / mm)
    draw_h_px = int(letter_height_mm * px_per_mm)
    gap_px = int(LINE_GAP_MM * px_per_mm)
    margin_left_px = int(MARGIN_LEFT_MM * px_per_mm)
    margin_top_px = int(MARGIN_TOP_MM * px_per_mm)
    available_width_mm = page_w_mm - 2 * MARGIN_LEFT_MM

    # Logic scaling...
    scale = 1.0
    if page_w_mm * px_per_mm > max_preview_width_px:
        scale = max_preview_width_px / (page_w_mm * px_per_mm)
    if scale < 0.25: scale = 0.25
    
    html_blocks = []
    html_blocks.append(f"""
    <div style="display:flex;justify-content:center;padding:12px;">
      <div style="width:{int(page_w_mm * px_per_mm * scale) + 2*margin_left_px + 40}px; max-width:100%; height:70vh; overflow-y:auto; overflow-x:hidden; border-radius:6px;">
        <div style="width:{int(page_w_mm * px_per_mm)}px; height:{int(page_h_mm * px_per_mm)}px; background:#fff;
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
                img_url = get_image_url(ch)
                draw_w_px = int(estimate_width_mm_from_char(ch, letter_height_mm) * px_per_mm)
                
                if img_url:
                    # SỬ DỤNG URL TỪ BACKEND
                    line_html += f"<img src='{img_url}' style='height:{draw_h_px}px;margin-right:{int(DEFAULT_CHAR_SPACING_MM*px_per_mm)}px;display:inline-block;' onerror=\"this.style.background='#b71c1c';\">"
                else:
                    # FALLBACK: Ký tự không được map hoặc Backend không tìm thấy
                    line_html += f"<div style='width:{draw_w_px}px;height:{draw_h_px}px;background:#000;color:#fff;display:flex;align-items:center;justify-content:center;margin-right:{int(DEFAULT_CHAR_SPACING_MM*px_per_mm)}px;font-weight:bold;'>{html.escape(ch)}</div>"
        line_html += "</div>"

        # Logic kiểm tra tràn lề (dựa trên giả định width 1:1)
        total_w_mm = 0.0
        for ch in line:
            if ch == " ":
                total_w_mm += DEFAULT_SPACE_MM
            else:
                total_w_mm += estimate_width_mm_from_char(ch, letter_height_mm)
                total_w_mm += DEFAULT_CHAR_SPACING_MM
        
        if total_w_mm > available_width_mm:
            line_html = f"<div style='background:rgba(255,200,0,0.4);padding:2px;border-radius:3px'>{line_html}</div>"

        html_blocks.append(line_html + f"<div style='width:100%;height:1px;background:#000;margin-top:{gap_px}px;'></div>")

    html_blocks.append("</div></div>")
    return "\n".join(html_blocks)

def render_library_html(preview_height_px=50, spacing_px=10):
    """Render library bằng cách gọi URL từ API Backend."""
    keys = sorted(IMAGE_INDEX_FRONTEND.keys())
    library_html = "<div style='background:#fff;border-top:2px solid #ccc;margin-top:20px;padding:10px;'>"
    library_html += "<div style='font-weight:bold;margin-bottom:6px;color:#333;'>Tank Marking Library Preview (Loaded from Backend)</div>"
    library_html += "<div style='display:flex;overflow-x:auto;white-space:nowrap;padding:5px;'>"

    if not keys:
        library_html += "<div style='color:#666;padding:8px;'>Could not determine available characters.</div>"
    else:
        for key in keys:
            img_url = get_image_url(key)
            if img_url:
                library_html += f"""
                <div style='display:inline-block; margin-right:{spacing_px}px; text-align:center;'>
                    <img src='{img_url}' style='height:{preview_height_px}px; display:block; margin-bottom: 2px;' onerror="this.style.background='#b71c1c';">
                    <span style='font-size:10px; color:#666;'>{key}</span>
                </div>
                """
            else:
                library_html += f"<div style='width:{preview_height_px}px;height:{preview_height_px}px;background:#eee;color:#000;display:flex;align-items:center;justify-content:center;margin-right:{spacing_px}px;font-size:12px;font-weight:bold;'>{html.escape(key)}</div>"

    library_html += "</div></div>"
    return library_html


# ---------------- UI (Đã sửa lỗi NameError) ----------------

# Apply custom CSS & Header (giữ nguyên logic load icon nếu có)
header_bg_b64 = None 
if os.path.isdir(ICONS_FOLDER):
    # ... logic load icon
    pass
# ... CSS ...
st.markdown("... CSS ...", unsafe_allow_html=True)
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

# TẠO NÚT VÀ GÁN GIÁ TRỊ (Đã chuyển lên trên để tránh NameError)
icon_download_b64 = None # ... (giả định đã load icon nếu có)
icon_preview_b64 = None # ...
col_buttons = st.columns([1, 1])
with col_buttons[0]:
    preview_btn = st.button("Preview", key="preview")
with col_buttons[1]:
    gen_pdf_btn = st.button("Generate PDF (download)", key="gen")

# --- BẮT ĐẦU LOGIC SỬ DỤNG NÚT ---

library_html = render_library_html()

if preview_btn:
    # Logic kiểm tra tràn lề/thiếu ký tự (Check)
    missing_chars = set()
    overflow_lines = {}
    page_w_pt, page_h_pt = page_size_mm(paper_choice, orientation)
    available_width_mm = (page_w_pt / mm) - 2 * MARGIN_LEFT_MM

    for i, line in enumerate(lines):
        x_mm = 0.0
        for j, ch in enumerate(line):
            if ch == " ":
                x_mm += DEFAULT_SPACE_MM
                continue
            
            if not get_image_url(ch): # Kiểm tra ký tự có tồn tại không
                missing_chars.add(ch)
            
            x_mm += estimate_width_mm_from_char(ch, chosen_height_mm)
            x_mm += DEFAULT_CHAR_SPACING_MM
        
        if x_mm > available_width_mm:
            overflow_lines[i+1] = round(x_mm - available_width_mm, 1)

    if missing_chars: st.markdown(f"<div style='color:white;background:#b71c1c;padding:8px;border-radius:6px;'>❌ Missing characters: {', '.join(sorted(missing_chars))}</div>", unsafe_allow_html=True)
    if overflow_lines: st.markdown(f"<div style='color:#111;background:#ffd54f;padding:8px;border-radius:6px;'>⚠️ {len(overflow_lines)} line(s) exceed page width.</div>", unsafe_allow_html=True)
    if not missing_chars and not overflow_lines: st.success("✅ All checks passed.")
    
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
        st.error(f"❌ Lỗi kết nối hoặc HTTP ({status_code}): Kiểm tra URL Backend ({API_BASE_URL}) và logs.")
