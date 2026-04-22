
import streamlit as st
import sqlite3, requests
import pandas as pd
from deep_translator import GoogleTranslator

# --- 1. CẤU HÌNH DATABASE ---
DB = "vocab.db"

def init_db():
    with sqlite3.connect(DB) as conn:
        conn.execute("""CREATE TABLE IF NOT EXISTS vocab 
            (id INTEGER PRIMARY KEY AUTOINCREMENT, 
             word TEXT, 
             meaning TEXT, 
             word_type TEXT, 
             example TEXT, 
             status TEXT)""")

def add_word(word, meaning, word_type, example):
    with sqlite3.connect(DB) as conn:
        conn.execute("INSERT INTO vocab (word, meaning, word_type, example, status) VALUES (?,?,?,?,?)", 
                     (word, meaning, word_type, example, "Đang học"))

def get_words():
    with sqlite3.connect(DB) as conn:
        return pd.read_sql("SELECT * FROM vocab", conn)

def update_status(wid, status):
    with sqlite3.connect(DB) as conn:
        conn.execute("UPDATE vocab SET status=? WHERE id=?", (status, wid))

def del_word(wid):
    with sqlite3.connect(DB) as conn:
        conn.execute("DELETE FROM vocab WHERE id=?", (wid,))

# --- 2. HÀM TRA TỪ & DỊCH ---
def get_word_data(word):
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{word}"
    try:
        res = requests.get(url, timeout=5)
        if res.status_code == 200:
            data = res.json()
            meaning_en = data[0]['meanings'][0]['definitions'][0]['definition']
            example = data[0]['meanings'][0]['definitions'][0].get('example', "")
            word_type_en = data[0]['meanings'][0]['partOfSpeech']

            # Dịch nghĩa tự động bằng deep-translator
            meaning_vi = GoogleTranslator(source='auto', target='vi').translate(meaning_en)

            return {
                "meaning": f"{meaning_en} \n(Nghĩa: {meaning_vi})",
                "example": example,
                "word_type": word_type_en
            }
    except:
        pass
    return None

# --- 3. GIAO DIỆN CHÍNH ---
st.set_page_config(page_title="Học Từ Vựng Pro", layout="wide")
init_db()

st.markdown("<h1 style='text-align: center; color: #2E86C1;'>📚 WEBSITE HỌC TỪ VỰNG TIẾNG ANH</h1>", unsafe_allow_html=True)
st.divider()

menu = ["🎓 Ôn tập (Flashcard)", "📖 Quản lý từ vựng", "➕ Thêm từ mới"]
choice = st.sidebar.selectbox("Menu", menu)

# --- CHỨC NĂNG 1: THÊM TỪ MỚI ---
if choice == "➕ Thêm từ mới":
    st.subheader("Thêm từ vựng mới")

    if "temp_data" not in st.session_state:
        st.session_state.temp_data = {"word": "", "meaning": "", "example": "", "type": "Khác"}

    c1, c2 = st.columns([3, 1])
    input_word = c1.text_input("Nhập từ tiếng Anh cần tra")
    if c2.button("🔍 Tra từ & Dịch", use_container_width=True):
        if input_word:
            with st.spinner("Đang lấy dữ liệu..."):
                result = get_word_data(input_word)
                if result:
                    st.session_state.temp_data = {
                        "word": input_word,
                        "meaning": result["meaning"],
                        "example": result["example"],
                        "type": result["word_type"]
                    }
                else:
                    st.warning("Không tìm thấy dữ liệu tự động, hãy tự điền nhé!")

    with st.form("vocab_form", clear_on_submit=True):
        f_word = st.text_input("Từ vựng (*)", value=st.session_state.temp_data["word"])

        type_opts = ["noun", "verb", "adjective", "adverb", "Khác"]
        curr_type = st.session_state.temp_data["type"]
        idx = type_opts.index(curr_type) if curr_type in type_opts else 4

        f_type = st.selectbox("Từ loại", type_opts, index=idx)
        f_meaning = st.text_area("Nghĩa & Giải thích (*)", value=st.session_state.temp_data["meaning"])
        f_example = st.text_area("Câu ví dụ", value=st.session_state.temp_data["example"])

        if st.form_submit_button("Lưu vào kho từ"):
            if f_word and f_meaning:
                add_word(f_word, f_meaning, f_type, f_example)
                st.success(f"Đã thêm: **{f_word}**")
                st.session_state.temp_data = {"word": "", "meaning": "", "example": "", "type": "Khác"}
            else:
                st.error("Vui lòng điền đủ Từ và Nghĩa!")

# --- CHỨC NĂNG 2: QUẢN LÝ TỪ VỰNG ---
elif choice == "📖 Quản lý từ vựng":
    st.subheader("Kho từ vựng của bạn")
    df = get_words()

    if not df.empty:
        # Làm đẹp hiển thị bảng
        st.dataframe(df[['id', 'word', 'word_type', 'meaning', 'status']], use_container_width=True)

        st.divider()
        st.write("### 🛠 Thao tác nhanh")
        c1, c2, c3 = st.columns([2, 2, 1])

        selected_id = c1.selectbox("Chọn ID từ vựng", df['id'].tolist())
        action = c2.selectbox("Hành động", ["Đánh dấu: Đã thuộc", "Đánh dấu: Đang học", "Xóa vĩnh viễn"])

        if c3.button("Xác nhận", use_container_width=True):
            if "Đã thuộc" in action:
                update_status(selected_id, "Đã thuộc")
                st.success("Đã cập nhật trạng thái!")
            elif "Đang học" in action:
                update_status(selected_id, "Đang học")
                st.success("Đã cập nhật trạng thái!")
            else:
                del_word(selected_id)
                st.warning("Đã xóa từ!")
            st.rerun()
    else:
        st.info("Chưa có từ nào trong kho.")

# --- CHỨC NĂNG 3: ÔN TẬP (FLASHCARD) ---
else:
    st.subheader("🎓 Flashcard: Ôn tập từ đang học")
    df = get_words()
    learning_words = df[df['status'] == "Đang học"]

    if not learning_words.empty:
        # Quản lý trạng thái thẻ bằng session_state
        if "card_idx" not in st.session_state:
            st.session_state.card_idx = 0
            st.session_state.flipped = False

        # Lấy từ hiện tại
        current_word = learning_words.iloc[st.session_state.card_idx % len(learning_words)]

        # Giao diện thẻ
        st.markdown(f"""
            <div style="background-color: #f9f9f9; padding: 50px; border: 2px solid #2E86C1; 
                        border-radius: 20px; text-align: center; min-height: 200px;">
                <h1 style="color: #2E86C1; font-size: 50px;">{current_word['word']}</h1>
                <p style="color: #888;">({current_word['word_type']})</p>
            </div>
        """, unsafe_allow_html=True)

        st.write("")
        col1, col2 = st.columns(2)

        if col1.button("👁️ Lật thẻ (Xem nghĩa)", use_container_width=True):
            st.session_state.flipped = True

        if col2.button("⏭️ Từ tiếp theo", use_container_width=True):
            st.session_state.card_idx += 1
            st.session_state.flipped = False
            st.rerun()

        if st.session_state.flipped:
            st.info(f"**Nghĩa:** {current_word['meaning']}")
            if current_word['example']:
                st.warning(f"**Ví dụ:** {current_word['example']}")
    else:
        st.balloons()
        st.success("Chúc mừng! Bạn đã thuộc hết tất cả từ vựng rồi!")

st.sidebar.markdown("---")
st.sidebar.write("💡 *Mẹo: Hãy tra từ trước khi Lưu để lấy nghĩa tự động!*")
