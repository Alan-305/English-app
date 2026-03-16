import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image

# 1. ページ設定とデザイン（ここから書き換え）
st.set_page_config(page_title="基礎S_英語表現T_重要文例Lab", layout="centered")

st.markdown("""
    <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;700&family=Roboto+Slab:wght@400;700&display=swap" rel="stylesheet">
    <style>
    /* 全体の背景 */
    .stApp {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
    }
    
    /* タイトルの装飾 */
    .main-title {
        font-family: 'Noto Sans JP', sans-serif;
        color: #1B4F72;
        text-align: center;
        font-weight: 700;
        padding-bottom: 20px;
        border-bottom: 2px solid #1B4F72;
    }
    
    /* カード風のコンテナ */
    .st-emotion-cache-1r6slb0, .stCard {
        background-color: white !important;
        padding: 30px !important;
        border-radius: 20px !important;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1) !important;
        margin-bottom: 20px !important;
    }
    
    /* ボタンのカスタマイズ */
    div.stButton > button {
        background-color: #1B4F72 !important;
        color: white !important;
        border-radius: 12px !important;
        border: none !important;
        height: 3.5em !important;
        font-weight: bold !important;
        transition: all 0.3s ease !important;
    }
    div.stButton > button:hover {
        background-color: #2E86C1 !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 5px 15px rgba(0,0,0,0.2) !important;
    }
    
    /* 英語フォント */
    .english-text {
        font-family: 'Roboto Slab', serif;
        font-size: 1.4em;
        color: #2C3E50;
    }
    
    /* 日本語フォント */
    .japanese-text {
        font-family: 'Noto Sans JP', sans-serif;
        font-size: 1.1em;
        font-weight: 500;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 変数の初期化 ---
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list']:
    if key not in st.session_state:
        st.session_state[key] = False if key in ['finished', 'show_feedback'] else (0 if key != 'current_list' else None)

# 2. AIの初期設定（動的なモデル選択）
if 'target_model' not in st.session_state or st.session_state.target_model is None:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in available_models if 'flash' in m]
        st.session_state.target_model = flash_models[0] if flash_models else available_models[0]
        st.session_state.ai_configured = True
    except Exception as e:
        st.error(f"AI設定エラー: {e}")

# 3. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except Exception as e:
        st.error(f"CSVエラー: {e}")
        st.stop()

# --- サイドバー設定 ---
st.sidebar.title("💎 Study Lab Menu")
st.sidebar.info(f"Active AI: {st.session_state.target_model}")

if st.sidebar.button("システムをリセット"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")
kous = sorted(list(set([q['kou'] for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("学習する講を選択", kous, default=[kous[0]] if kous else [])
order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

if st.sidebar.button("学習を開始する"):
    selected_data = [q for q in st.session_state.all_questions if q['kou'] in selected_kous]
    if selected_data:
        if order_type == "ランダム":
            random.shuffle(selected_data)
        st.session_state.current_list = selected_data
        st.session_state.current_idx = 0
        st.session_state.score = 0
        st.session_state.finished = False
        st.session_state.show_feedback = False
        st.rerun()

# --- メイン画面分岐 ---
if st.session_state.current_list is None:
    st.markdown("<h1 class='main-title'>English Expression Lab</h1>", unsafe_allow_html=True)
    st.info("サイドバーから「講」を選んで学習をスタートしましょう！")
    st.stop()

if st.session_state.finished:
    st.markdown("<h1 class='main-title'>Result 🎉</h1>", unsafe_allow_html=True)
    total = len(st.session_state.current_list)
    score = st.session_state.score
    st.balloons()
    st.markdown(f"""
    <div style="background-color: white; padding: 40px; border-radius: 20px; text-align: center;">
        <h2 style="color: #1B4F72;">お疲れ様でした！</h2>
        <p style="font-size: 1.2em;">今回のあなたのスコア</p>
        <p style="font-size: 4em; color: #E74C3C; font-weight: bold;">{score} <span style="font-size: 0.5em; color: #333;">/ {total}</span></p>
        <p>今日学んだ表現を、ぜひ声に出して復習してくださいね。</p>
    </div>
    """, unsafe_allow_html=True)
    if st.button("もう一度別の問題に挑戦する"):
        st.session_state.finished = False
        st.session_state.current_idx = 0
        st.rerun()
    st.stop()

# --- 学習メイン画面 ---
st.markdown("<h1 class='main-title'>English Expression Lab</h1>", unsafe_allow_html=True)

# プログレスバーの表示
progress = (st.session_state.current_idx) / len(st.session_state.current_list)
st.progress(progress)
st.sidebar.metric("現在のスコア", f"{st.session_state.score} 点")

# 問題表示エリア（カード風）
q = st.session_state.current_list[st.session_state.current_idx]
with st.container():
    st.markdown(f"<p class='japanese-text'>第{q['no']}問</p>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size: 1.5em; font-weight: bold; color: #1B4F72;'>{q['japanese']}</p>", unsafe_allow_html=True)
    st.caption(f"{q['kou']} - {st.session_state.current_idx + 1} / {len(st.session_state.current_list)} 問目")

# 解答入力エリア（タブ）
tab1, tab2, tab3 = st.tabs(["📷 Photo", "⌨️ Type", "🎤 Voice"])
with tab1:
    active_image = st.camera_input("ノートを撮影", key=f"cam_{st.session_state.current_idx}")
with tab2:
    user_text = st.text_input("英文を入力してください", key=f"text_{st.session_state.current_idx}")
with tab3:
    audio_file = st.audio_input("マイクに向かって話してください", key=f"audio_{st.session_state.current_idx}")

# アクションボタン
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("採点する"):
        if not (active_image or user_text or audio_file):
            st.warning("解答を提出してください。")
        else:
            with st.spinner("AI Teacher is checking..."):
                try:
                    model = genai.GenerativeModel(st.session_state.target_model)
                    instruction = f"英語教師として正解例『{q['english']}』と比較し採点。正解なら『正解です』と明記し、発音や表現を褒めてください。"
                    if audio_file:
                        res = model.generate_content([instruction, {"mime_type": "audio/wav", "data": audio_file.read()}])
                    elif active_image:
                        res = model.generate_content([instruction, Image.open(active_image)])
                    else:
                        res = model.generate_content(f"{instruction}\n生徒：{user_text}")
                    st.session_state.feedback_text = res.text
                    st.session_state.show_feedback = True
                    if "正解" in res.text:
                        st.session_state.score += 1
                        st.balloons()
                except Exception as e:
                    st.error(f"Error: {e}")

with col2:
    if st.button("答えを見る"):
        st.session_state.show_feedback = True
        st.session_state.feedback_text = "正解を確認して、何度も音読しましょう。"

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

# フィードバック表示
if st.session_state.show_feedback:
    st.markdown("---")
    st.info(st.session_state.feedback_text)
    st.markdown(f"<p class='english-text'><b>Answer:</b> {q['english']}</p>", unsafe_allow_html=True)
    tts = gTTS(q['english'], lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    st.audio(fp)
