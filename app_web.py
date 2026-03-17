import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image
from streamlit_cropper import st_cropper
import datetime
import requests
import re

# 1. ページ設定
st.set_page_config(page_title="基礎シリーズ 英語②T", layout="centered")

# 2. デザイン設定（先生の安定版デザイン）
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #ffffff 0%, #fff3e0 100%); }
    .main-title { 
        color: #e67e22; text-align: center; font-weight: 700; 
        font-size: 1.5em; padding: 10px 0; border-bottom: 3px solid #ffcc80; 
        font-family: 'serif'; margin-bottom: 15px;
    }
    div.stButton > button { 
        background-color: #f39c12 !important; color: white !important; 
        border-radius: 15px !important; height: 3.5em !important; 
        font-size: 1.1em !important; font-weight: bold !important; 
        border: none !important; width: 100%; margin-bottom: 8px;
    }
    .feedback-container { background-color: #fff9f0; padding: 15px; border-radius: 10px; border-left: 6px solid #f39c12; font-size: 1.1em; color: #5d4037; }
    .feedback-container b { color: #784212; font-size: 1.2em; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ 英語②T（表現）</h1>", unsafe_allow_html=True)

# 3. 変数の初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text']:
    if key not in st.session_state:
        st.session_state[key] = False if 'finished' in key or 'show' in key else (0 if 'idx' in key or 'score' in key else None)

# 4. AI設定：404エラー回避のための「モデル名自動検知」
if 'target_model' not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # 利用可能なモデルからProを探す
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        pro_model = [m for m in models if '1.5-pro' in m]
        # 見つかればそれを使う、なければ一番マシなものを使う
        st.session_state.target_model = pro_model[0] if pro_model else "gemini-1.5-flash"
    except:
        st.session_state.target_model = "gemini-1.5-pro"

# 5. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except:
        st.error("questions.csvが見つかりません。")
        st.stop()

# --- サイドバー ---
st.sidebar.title("📚 Menu")
if st.sidebar.button("最初からリセット"):
    st.session_state.clear()
    st.rerun()

kous = sorted(list(set([str(q['kou']) for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択してください", kous)
order_type = st.sidebar.radio("出題順を選択", ["順番通り", "ランダム"])

if st.sidebar.button("学習スタート"):
    if selected_kous:
        selected_data = [q for q in st.session_state.all_questions if str(q['kou']) in selected_kous]
        if order_type == "ランダム": random.shuffle(selected_data)
        st.session_state.current_list, st.session_state.current_idx, st.session_state.score = selected_data, 0, 0
        st.session_state.finished, st.session_state.show_feedback = False, False
        st.rerun()

# --- メイン画面 ---
if st.session_state.current_list is None:
    st.info("👈 左のメニューから講を選んでスタートしてください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.success(f"スコア: {st.session_state.score} / {len(st.session_state.current_list)}")
    if st.button("もう一度挑戦"):
        st.session_state.clear()
        st.rerun()
    st.stop()

q = st.session_state.current_list[st.session_state.current_idx]
st.markdown(f"### 第{q['no']}問 ({st.session_state.current_idx + 1}/{len(st.session_state.current_list)})")
st.markdown(f"## {q['japanese']}")

tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])

with tab2:
    user_text = st.text_input("回答を入力", key=f"t_{st.session_state.current_idx}")

with tab3:
    audio_data = st.audio_input("声に出して解答", key=f"a_{st.session_state.current_idx}")

# --- 採点ロジック ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 採点する"):
        if not (user_text or audio_data):
            st.warning("⚠️ 解答を入力してください。")
        else:
            with st.spinner("Pro版AIが添削中..."):
                try:
                    model = genai.GenerativeModel(st.session_state.target_model)
                    inst = f"日本文:{q['japanese']}\n正解例:{q['english']}\n生徒解答:{user_text}\n文法的に正しければ別解も正解(Perfect)として。不合格、記号**、カギカッコは一切使わず、前向きに添削して。正解なら必ず『正解です』と含めて。"
                    
                    if audio_data:
                        res = model.generate_content([inst, {"mime_type": "audio/wav", "data": audio_data.read()}])
                    else:
                        res = model.generate_content(f"{inst}\n生徒：{user_text}")
                    
                    f_text = re.sub(r'[\*「」『』]', '', res.text)
                    st.session_state.feedback_text, st.session_state.show_feedback = f_text, True
                    if "正解です" in f_text: st.session_state.score += 1
                except Exception as e:
                    st.error(f"AIエラー: {e}")

with col2:
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list): st.session_state.finished = True
        st.session_state.show_feedback = False
        st.rerun()

if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<br><br><b>模範解答：{q['english']}</b></div>", unsafe_allow_html=True)
    tts = gTTS(q['english'], lang='en')
    af = io.BytesIO()
    tts.write_to_fp(af)
    st.audio(af, autoplay=True)
