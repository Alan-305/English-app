import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image

# 1. ページ設定とデザイン（オレンジグラデーション & テキスト拡大対応）
st.set_page_config(page_title="基礎シリーズ 英語②T（表現）", layout="centered")

st.markdown("""
<style>
    /* 全体の背景 */
    .stApp { 
        background: linear-gradient(135deg, #ffffff 0%, #fff3e0 100%); 
    }
    
    /* タイトル */
    .main-title { 
        color: #e67e22; 
        text-align: center; 
        font-weight: 700; 
        padding-bottom: 10px; 
        border-bottom: 3px solid #ffcc80;
        font-family: 'serif';
        margin-bottom: 30px;
    }
    
    /* カード部分 */
    div[data-testid="stVerticalBlock"] > div:has(div.stTabs) { 
        background-color: white !important; 
        padding: 30px !important; 
        border-radius: 15px !important; 
        border: 1px solid #ffe0b2 !important;
        box-shadow: 4px 4px 10px rgba(255, 165, 0, 0.05) !important;
    }
    
    /* ボタンデザイン */
    div.stButton > button { 
        background-color: #f39c12 !important; 
        color: white !important; 
        border-radius: 10px !important; 
        height: 3.5em !important; 
        font-weight: bold !important; 
        border: none !important;
    }
    
    /* 解説セクションの見出し */
    .explanation-label {
        color: #d35400;
        font-weight: bold;
        font-size: 1.2em;
        margin-top: 20px;
        margin-bottom: 10px;
    }

    /* 解説文のボックス */
    .explanation-box {
        background-color: #fff9f0;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #f39c12;
        line-height: 1.6;
        font-size: 1.1em;
        color: #5d4037;
    }

    /* 解説の中の英文（太字部分）を大きく表示 */
    .explanation-box b, .explanation-box strong {
        font-family: 'serif';
        font-size: 1.3em; /* 正解例と同じサイズに調整 */
        color: #784212;
        padding: 0 2px;
    }
    
    /* 正解例のテキスト */
    .english-text { 
        font-family: 'serif'; 
        font-size: 1.4em; 
        color: #784212; 
        font-weight: bold; 
        margin-top: 15px;
    }
    
    .japanese-text { font-size: 1.1em; color: #5d4037; }
</style>
""", unsafe_allow_html=True)

# 2. 変数の初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text']:
    if key not in st.session_state:
        st.session_state[key] = False if key in ['finished', 'show_feedback'] else (0 if key not in ['current_list', 'feedback_text'] else None)

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
st.sidebar.title("📚 Study Lab Menu")
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
    st.markdown("<h1 class='main-title'>基礎シリーズ 英語②T（表現）</h1>", unsafe_allow_html=True)
    st.info("サイドバーから講を選んで開始してください。")
    st.stop()

if st.session_state.finished:
    st.markdown("<h1 class='main-title'>Result 🎉</h1>", unsafe_allow_html=True)
    total = len(st.session_state.current_list)
    score = st.session_state.score
    st.balloons()
    st.markdown(f"<div style='background:white;padding:30px;border:2px solid #ffcc80;border-radius:15px;text-align:center;'><h2>最終成績</h2><p style='font-size:3.5em;color:#e67e22;font-weight:bold;'>{score} / {total}</p></div>", unsafe_allow_html=True)
    if st.button("もう一度挑戦"):
        st.session_state.finished = False
        st.rerun()
    st.stop()

st.markdown("<h1 class='main-title'>基礎シリーズ 英語②T（表現）</h1>", unsafe_allow_html=True)
progress = (st.session_state.current_idx) / len(st.session_state.current_list)
st.progress(progress)

q = st.session_state.current_list[st.session_state.current_idx]
st.markdown(f"<p class='japanese-text'>第{q['no']}問（{q['kou']}）</p>", unsafe_allow_html=True)
st.markdown(f"<h2 style='color:#784212;'>{q['japanese']}</h2>", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["📷 Photo", "⌨️ Type", "🎤 Voice"])
with tab1: active_image = st.camera_input("撮影", key=f"cam_{st.session_state.current_idx}")
with tab2: user_text = st.text_input("回答入力", key=f"text_{st.session_state.current_idx}")
with tab3: audio_file = st.audio_input("話して提出", key=f"audio_{st.session_state.current_idx}")

col1, col2, col3 = st.columns(3)
with col1:
    if st.button("採点する"):
        if not (active_image or user_text or audio_file):
            st.warning("解答を入力してください。")
        else:
            with st.spinner("分析中..."):
                try:
                    model = genai.GenerativeModel(st.session_state.target_model)
                    # プロンプトの修正：正解例自体の解説を禁止
                    inst = f"""
                    生徒の回答を正解例『{q['english']}』と比較し、添削とアドバイスを日本語で作成してください。
                    【条件】
                    - **正解例そのものの意味や文法事項の解説は一切含めないでください。** - 生徒の回答のミス、綴りの間違い、あるいは良い点のみを指摘してください。
                    - 正解の場合は、文中に必ず『正解です』と入れてください。
                    - 解説の中で英文を書くときは、その部分を必ず ** (太字) で囲んでください。
                    - 「英語教師としての解説」などの見出しは不要です。内容のみを書いてください。
                    """
                    if audio_file: res = model.generate_content([inst, {"mime_type": "audio/wav", "data": audio_file.read()}])
                    elif active_image: res = model.generate_content([inst, Image.open(active_image)])
                    else: res = model.generate_content(f"{inst}\n生徒の回答：{user_text}")
                    
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

# --- 解説エリア ---
if st.session_state.show_feedback:
    st.markdown("---")
    st.markdown("<p class='explanation-label'>解説</p>", unsafe_allow_html=True)
    # 解説ボックスの中にAIの回答を表示（英文は自動的に大きく太字になるようCSSで設定済み）
    st.markdown(f"<div class='explanation-box'>{st.session_state.feedback_text}</div>", unsafe_allow_html=True)
    
    st.markdown(f"<p class='english-text'>Answer: {q['english']}</p>", unsafe_allow_html=True)
    tts = gTTS(q['english'], lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    st.audio(fp)
