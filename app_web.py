import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image

# 1. ページ設定とデザイン（エラーに強い新形式）
st.set_page_config(page_title="基礎S_英語表現T_重要文例Lab", layout="centered")

# デザイン指示を「文字」ではなく「指示」として強制認識させます
custom_css = """
<style>
    .stApp { background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); }
    .main-title { color: #1B4F72; text-align: center; font-weight: 700; padding-bottom: 20px; border-bottom: 2px solid #1B4F72; }
    div[data-testid="stVerticalBlock"] > div:has(div.stTabs) { background-color: white !important; padding: 25px !important; border-radius: 15px !important; box-shadow: 0 4px 12px rgba(0,0,0,0.08) !important; }
    div.stButton > button { background-color: #1B4F72 !important; color: white !important; border-radius: 10px !important; height: 3.5em !important; font-weight: bold !important; }
    .english-text { font-size: 1.3em; color: #2C3E50; font-weight: bold; }
    .japanese-text { font-size: 1.1em; }
</style>
"""
st.markdown(custom_css, unsafe_allow_html=True)

# 2. 変数の初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list']:
    if key not in st.session_state:
        st.session_state[key] = False if key in ['finished', 'show_feedback'] else (0 if key != 'current_list' else None)

# 3. AIの初期設定
if 'target_model' not in st.session_state or st.session_state.target_model is None:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in available_models if 'flash' in m]
        st.session_state.target_model = flash_models[0] if flash_models else available_models[0]
    except:
        st.session_state.target_model = "models/gemini-1.5-flash"

# 4. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except Exception as e:
        st.error(f"CSV読み込みエラー: {e}")
        st.stop()

# --- サイドバー ---
st.sidebar.title("💎 Study Lab Menu")
if st.sidebar.button("システムをリセット"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")
kous = sorted(list(set([q['kou'] for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択", kous, default=[kous[0]] if kous else [])
order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

if st.sidebar.button("学習を開始する"):
    selected_data = [q for q in st.session_state.all_questions if q['kou'] in selected_kous]
    if selected_data:
        if order_type == "ランダム": random.shuffle(selected_data)
        st.session_state.current_list = selected_data
        st.session_state.current_idx = 0
        st.session_state.score = 0
        st.session_state.finished = False
        st.session_state.show_feedback = False
        st.rerun()

# --- メイン画面 ---
if st.session_state.current_list is None:
    st.markdown("<h1 class='main-title'>English Expression Lab</h1>", unsafe_allow_html=True)
    st.info("サイドバーから講を選んで開始してください。")
    st.stop()

if st.session_state.finished:
    st.markdown("<h1 class='main-title'>Result 🎉</h1>", unsafe_allow_html=True)
    total = len(st.session_state.current_list)
    score = st.session_state.score
    st.balloons()
    st.markdown(f"<div style='background:white;padding:30px;border-radius:15px;text-align:center;'><h2>お疲れ様でした！</h2><p style='font-size:3em;color:#E74C3C;'>{score} / {total}</p></div>", unsafe_allow_html=True)
    if st.button("もう一度挑戦"):
        st.session_state.finished = False
        st.rerun()
    st.stop()

st.markdown("<h1 class='main-title'>English Expression Lab</h1>", unsafe_allow_html=True)
progress = (st.session_state.current_idx) / len(st.session_state.current_list)
st.progress(progress)
st.sidebar.metric("現在のスコア", f"{st.session_state.score} 点")

q = st.session_state.current_list[st.session_state.current_idx]
st.markdown(f"<p class='japanese-text'>第{q['no']}問</p>", unsafe_allow_html=True)
st.markdown(f"<h2 style='color:#1B4F72;'>{q['japanese']}</h2>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📷 Photo", "⌨️ Type", "🎤 Voice"])
with tab1: active_image = st.camera_input("撮影", key=f"cam_{st.session_state.current_idx}")
with tab2: user_text = st.text_input("回答入力", key=f"text_{st.session_state.current_idx}")
with tab3: audio_file = st.audio_input("話して提出", key=f"audio_{st.session_state.current_idx}")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("採点する"):
        with st.spinner("AI checking..."):
            try:
                model = genai.GenerativeModel(st.session_state.target_model)
                inst = f"英語教師として正解例『{q['english']}』と比較。正解なら『正解です』と含め日本語で解説して。"
                if audio_file: res = model.generate_content([inst, {"mime_type": "audio/wav", "data": audio_file.read()}])
                elif active_image: res = model.generate_content([inst, Image.open(active_image)])
                else: res = model.generate_content(f"{inst}\n生徒：{user_text}")
                st.session_state.feedback_text = res.text
                st.session_state.show_feedback = True
                if "正解" in res.text:
                    st.session_state.score += 1
                    st.balloons()
            except Exception as e: st.error(f"Error: {e}")
with col2:
    if st.button("答えを見る"):
        st.session_state.show_feedback = True
        st.session_state.feedback_text = "正解を確認しましょう。"
with col3:
    label = "Next ➔" if st.session_state.current_idx < len(st.session_state.current_list) - 1 else "Finish"
    if st.button(label):
        if st.session_state.current_idx < len(st.session_state.current_list) - 1:
            st.session_state.current_idx += 1
            st.session_state.show_feedback = False
            st.rerun()
        else:
            st.session_state.finished = True
            st.rerun()

if st.session_state.show_feedback:
    st.markdown("---")
    st.info(st.session_state.feedback_text)
    st.markdown(f"<p class='english-text'>Answer: {q['english']}</p>", unsafe_allow_html=True)
    tts = gTTS(q['english'], lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    st.audio(fp)
