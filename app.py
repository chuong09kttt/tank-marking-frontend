# app.py (Cho Frontend Streamlit)
import streamlit as st
import os, io, math, base64, re
from PIL import Image
import html
import requests # <-- CẦN THÊM THƯ VIỆN NÀY ĐỂ GỌI API

# --- API CONFIG ---
# Thay thế bằng URL chính xác của service tank_marking_backend-1 trên Render
API_BASE_URL = "https://tank-marking-backend-1.onrender.com" 

# ---------------- CONFIG & CONSTANTS ----------------
# Giữ lại các hằng số liên quan đến UI và tính toán sơ bộ
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
# Các thư mục này KHÔNG còn cần thiết cho logic tạo PDF, chỉ cần cho Preview
LETTERS_FOLDER = os.path.join(ROOT_DIR, "ABC") 
ICONS_FOLDER = os.path.join(ROOT_DIR, "icons") 
# ... (Giữ các hằng số PAPER_SIZES, MARGINS, etc. nếu cần cho logic Preview/Check)
PAPER_SIZES = {"A1": None, "A2": None, "A3": None, "A4": None} # Đã bị đơn giản hóa
# (Để đơn giản, tôi giữ các hàm tính toán cho Preview/Check)
# ...

# ---------------- UTILITIES (CHỈ DÀNH CHO PREVIEW CỤC BỘ) ----------------
# Cần giữ lại: build_image_index, find_image_for_char, estimate_width_mm_from_image
# và các hàm render HTML/Base64 để hiển thị Preview.
# Cần cài đặt thư viện requests trong requirements.txt của frontend.

# ... (Giữ nguyên các hàm: build_image_index, find_image_for_char, estimate_width_mm_from_image,
#      page_size_mm, mm_to_pt, _encode_file_to_base64, render_preview_html, render_library_html)
#      vì chúng cần thiết cho chức năng Preview và Check (như tính toán tràn lề).
# XÓA HÀM generate_pdf()

# ---------------- UI ----------------
# ... (Giữ nguyên phần UI từ st.markdown đến footer_text = st.text_input) ...

# ---------------- LOGIC GỌI API ----------------
if gen_pdf_btn:
    st.info("Đang gửi yêu cầu tạo PDF tới Backend...")
    
    # 1. Chuẩn bị Dữ liệu (Payload)
    payload = {
        "lines": lines,
        "letter_height_mm": float(chosen_height_mm),
        "paper_choice": paper_choice,
        "orientation": orientation,
        "footer_text": footer_text
    }
    
    try:
        # 2. Gửi Request POST đến API Backend
        response = requests.post(f"{API_BASE_URL}/generate-pdf", json=payload, timeout=90)

        # 3. Kiểm tra và Xử lý Response
        if response.status_code == 200:
            pdf_bytes = response.content
            st.success("✅ PDF đã được tạo thành công bởi Backend.")
            
            # Nút Download
            st.download_button(
                "⬇️ Tải xuống PDF", 
                data=pdf_bytes, 
                file_name="TankMarking.pdf", 
                mime="application/pdf"
            )
        else:
            st.error(f"❌ Lỗi từ Backend: Mã lỗi {response.status_code}. Vui lòng kiểm tra logs Backend.")
            # st.error(response.text) # Có thể in lỗi chi tiết nếu cần

    except requests.exceptions.ConnectionError:
        st.error(f"❌ Lỗi kết nối: Không thể kết nối đến Backend API tại {API_BASE_URL}.")
    except requests.exceptions.Timeout:
        st.error("❌ Lỗi Timeout: Backend mất quá nhiều thời gian để xử lý.")
    except Exception as e:
        st.error(f"❌ Lỗi không xác định: {e}")

# ... (Giữ nguyên logic của Preview Button - nó vẫn chạy cục bộ cho tính toán) ...
