import streamlit as st
from google import genai  # 2026年最新のインポート方式
import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image
from streamlit_cropper import st_cropper
import requests
import re

# ページ設定
st.set_page_config(page_title="基礎シリーズ_英語②_T_重要文例", layout="centered")

# デザイン設定
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
        border: none !important; width: 100%;
    }
    .feedback-container { background-color: #fff9f0; padding: 20px; border-radius: 15px; border-left: 8px solid #f39c12; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ_英語②_T_重要文例</h1>", unsafe_allow_html=True)

# セッション状態の初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text']:
    if key not in st.session_state:
        st.session_state[key] = False if key in ['finished', 'show_feedback'] else (0 if key not in ['current_list', 'feedback_text'] else None)

# データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except:
        st.error("questions.csvが見つかりません。")
        st.stop()

# サイドバー
st.sidebar.title("📚 Menu")
kous = sorted(list(set([str(q.get('kou', q.get('lecture', '1'))) for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択してください", kous)
order_type = st.sidebar.radio("出題順を選択", ["順番通り", "ランダム"])

if st.sidebar.button("学習スタート"):
    if selected_kous:
        data = [q for q in st.session_state.all_questions if str(q.get('kou', q.get('lecture', '1'))) in selected_kous]
        if data:
            if order_type == "ランダム":
                random.shuffle(data)
            st.session_state.current_list, st.session_state.current_idx, st.session_state.score = data, 0, 0
            st.session_state.finished, st.session_state.show_feedback = False, False
            st.rerun()

# メイン画面の制御
if st.session_state.current_list is None:
    st.info("👈 左側のメニューから講を選んで学習スタートを押してください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.success(f"全問題終了！ スコア: {st.session_state.score} / {len(st.session_state.current_list)}")
    if st.button("もう一度挑戦"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# 問題表示
q = st.session_state.current_list[st.session_state.current_idx]
st.write(f"### 第{q.get('no', st.session_state.current_idx + 1)}問 ({st.session_state.current_idx + 1}/{len(st.session_state.current_list)})")
st.write(f"## {q.get('japanese', q.get('question', ''))}")

tab1, tab2, tab3 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声"])

with tab2:
    user_answer = st.text_input("英文を入力", key=f"t_{st.session_state.current_idx}")

# 採点とNext
col1, col2 = st.columns(2)
with col1:
    if st.button("🚀 採点する"):
        if user_answer:
            with st.spinner("Pro版AIが添削中..."):
                try:
                    # 最新のSDKによるProモデル呼び出し
                    client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
                    prompt = f"日本文: {q.get('japanese', '')}\n正解例: {q.get('english', q.get('answer', ''))}\n生徒解答: {user_answer}\nルール: 文法的に正しければ別解も正解(Perfect)とする。不合格という言葉、**のような記号、カギカッコ「」は一切使わず、厳格かつ前向きに添削して。"
                    
                    response = client.models.generate_content(model="gemini-1.5-pro", contents=prompt)
                    
                    # 記号の強制クリーニング
                    clean_text = re.sub(r'[\*「」『』]', '', response.text)
                    st.session_state.feedback_text, st.session_state.show_feedback = clean_text, True
                    if "正解" in clean_text or "Perfect" in clean_text:
                        st.session_state.score += 1
                except Exception as e:
                    st.error(f"AIエラー: {e}")

with col2:
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list):
            st.session_state.finished = True
        st.session_state.show_feedback = False
        st.rerun()

if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}</div>", unsafe_allow_html=True)
    tts = gTTS(q.get('english', q.get('answer', '')), lang='en')
    af = io.BytesIO()
    tts.write_to_fp(af)
    st.audio(af, autoplay=True)
