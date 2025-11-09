# app.py (Frontend Streamlit) - ROBUST VERSION

import streamlit as st
import os, io, math, base64, re
from PIL import Image, ImageDraw, ImageFont
import html
import requests 
from reportlab.lib.units import mm
import time

# --- API CONFIGURATION ---
API_BASE_URL = "https://tank-marking-backend.onrender.com"

# ---------------- CONFIG & CONSTANTS ----------------
st.set_page_config(page_title="Tank Marking PDF Generator", layout="centered")

# Paper sizes for preview
A1 = (2380, 3368) 
A2 = (1684, 2380)
A3 = (1190, 1684)
A4 = (841, 1190)

def landscape(size): 
    return (size[1], size[0])

def portrait(size): 
    return size

PAPER_SIZES_PT = {"A1": A1, "A2": A2, "A3": A3, "A4": A4}
PAPER_SIZES = {"A1": None, "A2": None, "A3": None, "A4": None}

DEFAULT_CHAR_SPACING_MM = 20
DEFAULT_SPACE_MM = 40
LINE_GAP_MM = 10
MARGIN_LEFT_MM = 20
MARGIN_TOP_MM = 20

# ---------------- OFFLINE CHARACTER GENERATION ----------------

def create_fallback_char_image(char, size=100):
    """Tạo ảnh fallback cho ký tự"""
    img = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(img)
    
    # Vẽ border
    draw.rectangle([5, 5, size-5, size-5], outline='black', width=3)
    
    # Vẽ chữ
    try:
        font = ImageFont.truetype("arial.ttf", size//2)
    except:
        try:
            font = ImageFont.load_default()
        except:
            font = None
    
    bbox = draw.textbbox((0, 0), char, font=font) if font else (0, 0, size, size)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (size - text_width) // 2
    y = (size - text_height) // 2
    
    draw.text((x, y-5), char, fill='black', font=font)
    return img

def char_to_base64(char, size=100):
    """Chuyển ký tự thành ảnh base64"""
    img = create_fallback_char_image(char, size)
    buffered = io.BytesIO()
    img.save(buffered, format="PNG")
    return base64.b64encode(buffered.getvalue()).decode()

# ---------------- UTILITIES ----------------

def page_size_mm(paper_name, orientation):
    """Tính kích thước trang theo mm"""
    w_pt, h_pt = PAPER_SIZES_PT.get(paper_name, PAPER_SIZES_PT["A4"])
    if orientation == "Landscape":
        w_pt, h_pt = landscape((w_pt, h_pt))
    else:
        w_pt, h_pt = portrait((w_pt, h_pt))
    w_mm = (w_pt / 72) * 25.4
    h_mm = (h_pt / 72) * 25.4
    return (w_mm, h_mm)

@st.cache_data(ttl=3600)
def fetch_available_chars():
    """Lấy danh sách ký tự từ backend với fallback"""
    try:
        response = requests.get(f"{API_BASE_URL}/available-chars", timeout=10)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None  # Return None để biết là failed

def get_image_url(ch):
    """Lấy URL ảnh với fallback về base64"""
    # Luôn sử dụng fallback cho đến khi backend ổn định
    return f"data:image/png;base64,{char_to_base64(ch)}"

def estimate_width_mm_from_char(ch, letter_height_mm):
    return letter_height_mm 

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
                    line_html += f"<img src='{img_url}' style='height:{int(letter_height_mm*px_per_mm)}px; margin-right:{int(DEFAULT_CHAR_SPACING_MM*px_per_mm)}px; display:inline-block;'>"
                
                x_mm += draw_w_mm
                x_mm += DEFAULT_CHAR_SPACING_MM
        
        line_html += "</div>"

        if x_mm > available_width_mm:
            line_html = f"<div style='background:rgba(255,200,0,0.4);padding:2px;border-radius:3px'>{line_html}</div>"

        html_blocks.append(line_html + f"<div style='width:100%;height:1px;background:#000;margin-top:{int(LINE_GAP_MM*px_per_mm)}px;'></div>")

    html_blocks.append("</div></div>")
    return "\n".join(html_blocks)

def render_library_html(preview_height_px=50, spacing_px=10):
    """Render library với fallback images"""
    # Tập ký tự mẫu để hiển thị
    sample_chars = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789/."
    
    library_html = "<div style='background:#fff;border-top:2px solid #ccc;margin-top:20px;padding:10px;'>"
    library_html += "<div style='font-weight:bold;margin-bottom:6px;color:#333;'>Tank Marking Library (Using Fallback Images)</div>"
    library_html += "<div style='display:flex;overflow-x:auto;white-space:nowrap;padding:5px;'>"

    for char in sample_chars:
        img_url = get_image_url(char)
        library_html += f"""
        <div style='display:inline-block; margin-right:{spacing_px}px; text-align:center;'>
            <img src='{img_url}' style='height:{preview_height_px}px; display:block; margin-bottom: 2px;'>
            <span style='font-size:10px; color:#666;'>{html.escape(char)}</span>
        </div>
        """

    library_html += "</div></div>"
    return library_html

# ---------------- UI ----------------

st.markdown("""
<style>
.header-banner {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 20px;
    border-radius: 10px;
    color: white;
    text-align: center;
    margin-bottom: 20px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='header-banner'><h1 style='margin:6px 0;'>Tank Marking PDF Generator</h1></div>", unsafe_allow_html=True)

# Hiển thị trạng thái backend
st.warning("⚠️ **Backend is currently experiencing issues** - Using fallback mode for preview. PDF generation may not work.")

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

# Buttons
col_buttons = st.columns([1, 1])
with col_buttons[0]:
    preview_btn = st.button("Preview", key="preview")
with col_buttons[1]:
    gen_pdf_btn = st.button("Generate PDF (try anyway)", key="gen")

# --- PREVIEW LOGIC ---
library_html = render_library_html()

if preview_btn:
    st.markdown("### PDF Preview (Fallback Mode)")
    preview_html = render_preview_html(lines, chosen_height_mm, paper_choice, orientation, footer_text)
    st.markdown(preview_html, unsafe_allow_html=True)
    st.markdown(library_html, unsafe_allow_html=True)

else:
    st.markdown("<div style='color:#444;margin-top:12px;'>Press <strong>Preview</strong> to see the layout with fallback characters.</div>", unsafe_allow_html=True)
    st.markdown(library_html, unsafe_allow_html=True)

# --- GENERATE PDF LOGIC ---
if gen_pdf_btn:
    if not lines:
        st.error("❌ Please enter some text first")
        st.stop()
        
    st.info("🔄 Attempting to generate PDF with backend...")
    
    # Test backend connection first
    try:
        test_response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if test_response.status_code != 200:
            st.error("❌ Backend is currently unavailable. Please try again later.")
            st.stop()
    except:
        st.error("❌ Cannot connect to backend server. Please try again later.")
        st.stop()
    
    # Try to generate PDF
    payload = {
        "lines": lines,
        "letter_height_mm": chosen_height_mm,
        "paper_choice": paper_choice,
        "orientation": orientation,
        "footer_text": footer_text
    }
    
    try:
        with st.spinner("Generating PDF... This may take a few seconds"):
            response = requests.post(f"{API_BASE_URL}/generate-pdf", json=payload, timeout=30)
        
        if response.status_code == 200:
            pdf_bytes = response.content
            st.success("✅ PDF generated successfully! Download:")
            st.download_button(
                "⬇️ Download PDF", 
                data=pdf_bytes, 
                file_name="TankMarking.pdf", 
                mime="application/pdf"
            )
        else:
            st.error(f"❌ Backend error {response.status_code}. The backend service may be restarting.")
            st.info("💡 Please wait a few minutes and try again, or check the backend logs.")

    except requests.exceptions.Timeout:
        st.error("❌ PDF generation timeout - backend is not responding")
    except requests.exceptions.ConnectionError:
        st.error("❌ Cannot connect to backend server")
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")

# Debug info
with st.sidebar:
    st.markdown("### 🔧 System Status")
    
    # Test backend connection
    try:
        health_response = requests.get(f"{API_BASE_URL}/", timeout=5)
        if health_response.status_code == 200:
            st.error("❌ Backend: Connected but has internal errors")
        else:
            st.error(f"❌ Backend: HTTP {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        st.error("❌ Backend: Cannot connect")
    except requests.exceptions.Timeout:
        st.error("❌ Backend: Timeout")
    except Exception as e:
        st.error(f"❌ Backend: {str(e)}")
    
    st.info("🔄 Frontend: Using fallback mode")
    st.write(f"Backend URL: {API_BASE_URL}")
