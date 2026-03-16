import os
os.system("pip install google-generativeai gTTS Pillow")import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image

# 1. ページ設定とデザイン
st.set_page_config(page_title="基礎S_英語表現T_重要文例Lab", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #D6EAF8; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; font-size: 1.1em; }
    h1, h2, h3 { color: #1B4F72; }
    .stTextInput>div>div>input { font-size: 1.2em; }
    </style>
    """, unsafe_allow_html=True)

# 2. AIの初期設定（最も安定した認証方式に変更）
if 'ai_configured' not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        st.session_state.ai_configured = True
        # 安定版のモデル名を指定
        st.session_state.target_model = 'gemini-1.5-flash'
    except Exception as e:
        st.error(f"AIの準備に失敗しました。Secretsの設定を確認してください: {e}")

# 3. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except Exception as e:
        st.error(f"CSV読み込みエラー: {e}")
        st.stop()

# --- サイドバー設定 ---
st.sidebar.title("🛠️ 学習設定")
kou_list = sorted(list(set([q['kou'] for q in st.session_state.all_questions])), key=lambda x: str(x))
selected_kous = st.sidebar.multiselect("学習する講を選択", kou_list, default=[kou_list[0]] if kou_list else [])
order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

if st.sidebar.button("この設定で開始/リセット"):
    selected_data = [q for q in st.session_state.all_questions if q['kou'] in selected_kous]
    if order_type == "ランダム":
        random.shuffle(selected_data)
    st.session_state.current_list = selected_data
    st.session_state.current_idx = 0
    st.session_state.show_feedback = False
    st.session_state.feedback_text = ""
    st.session_state.ocr_text = ""
    st.rerun()

# --- メイン画面 ---
if 'current_list' not in st.session_state:
    st.info("左のサイドバーから講を選んで「開始」ボタンを押してください。")
    st.stop()

st.title("基礎S_英語表現T_重要文例Lab")

q = st.session_state.current_list[st.session_state.current_idx]
st.subheader(f"問 {q['no']}: {q['japanese']}")
st.caption(f"（{q['kou']} - {st.session_state.current_idx + 1} / {len(st.session_state.current_list)} 問目）")

# --- カメラ/写真による文字起こし ---
with st.expander("📷 写真から解答を入力（OCR機能）"):
    input_image = st.file_uploader("ノートや手書きの答えをアップロード", type=['png', 'jpg', 'jpeg'], key="uploader")
    camera_file = st.camera_input("カメラで撮影")
    
    target_img = camera_file if camera_file else input_image
    
    if target_img and st.button("AIで文字起こしを実行"):
        with st.spinner("AIが英文を読み取っています..."):
            try:
                img = Image.open(target_img)
                model = genai.GenerativeModel(st.session_state.target_model)
                ocr_res = model.generate_content(["この画像に書かれている英文のみをテキストとして書き出してください。解説は不要です。", img])
                st.session_state.ocr_text = ocr_res.text.strip()
                st.success("読み取り完了！下の欄に反映されました。")
            except Exception as e:
                st.error(f"文字起こしエラー: {e}")

# 解答入力欄
user_ans = st.text_input("あなたの答え:", value=st.session_state.get('ocr_text', ""), key=f"input_{st.session_state.current_idx}")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("採点"):
        prompt = f"""
        あなたは親切な日本人の英語教師です。
        【正解例】: {q['english']}
        【生徒の回答】: {user_ans}
        上記を比較し、採点と解説を日本語のみで行ってください。
        大きな見出しを使わず、標準サイズで読みやすく回答してください。
        """
        try:
            model = genai.GenerativeModel(st.session_state.target_model)
            res = model.generate_content(prompt)
            st.session_state.feedback_text = res.text
            st.session_state.show_feedback = True
            
            # 桜を咲かせる（バルーン）判定
            user_clean = "".join(e for e in user_ans if e.isalnum()).lower()
            correct_clean = "".join(e for e in q['english'] if e.isalnum()).lower()
            if user_clean == correct_clean:
                st.balloons()
        except Exception as e:
            st.error(f"採点エラー: {e}")

with col2:
    if st.button("正解と音声"):
        st.session_state.show_feedback = True
        st.session_state.feedback_text = "正解と音声を確認しましょう。"

with col3:
    if st.button("次へ"):
        if st.session_state.current_idx < len(st.session_state.current_list) - 1:
            st.session_state.current_idx += 1
            st.session_state.show_feedback = False
            st.session_state.ocr_text = ""
            st.rerun()
        else:
            st.success("全ての選んだ問題が終わりました！")

# 結果表示
if st.session_state.show_feedback:
    st.info(st.session_state.feedback_text)
    st.write(f"**【正解例】** {q['english']}")
    
    tts = gTTS(q['english'], lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    st.audio(fp)
