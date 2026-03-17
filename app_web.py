import os
# 最新のPython環境でのエラーを防ぐための魔法の1行
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image
from streamlit_cropper import st_cropper
import requests
import re

# 1. ページ設定
st.set_page_config(page_title="英語学習アプリ", layout="centered")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #ffffff 0%, #fff3e0 100%); }
    .main-title { color: #e67e22; text-align: center; font-weight: 700; font-size: 1.5em; border-bottom: 3px solid #ffcc80; padding: 10px; }
    div.stButton > button { background-color: #f39c12 !important; color: white !important; border-radius: 15px !important; width: 100%; height: 3.5em; font-weight: bold; }
    .feedback-container { background-color: #fff9f0; padding: 20px; border-radius: 15px; border-left: 8px solid #f39c12; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ 英語②T</h1>", unsafe_allow_html=True)

# 2. セッション状態の初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text']:
    if key not in st.session_state:
        st.session_state[key] = False if 'finished' in key or 'show' in key else (0 if 'idx' in key or 'score' in key else None)

# 3. データの読み込み
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
kous = sorted(list(set([str(q.get('kou', q.get('lecture', '1'))) for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択してください", kous)
order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

if st.sidebar.button("学習スタート"):
    if selected_kous:
        data = [q for q in st.session_state.all_questions if str(q.get('kou', q.get('lecture', '1'))) in selected_kous]
        if order_type == "ランダム": random.shuffle(data)
        st.session_state.current_list, st.session_state.current_idx, st.session_state.score = data, 0, 0
        st.session_state.finished, st.session_state.show_feedback = False, False
        st.rerun()

# --- メイン画面 ---
if st.session_state.current_list is None:
    st.info("👈 左のメニューから講を選んでスタートしてください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.success(f"終了！ スコア: {st.session_state.score} / {len(st.session_state.current_list)}")
    if st.button("最初に戻る"):
        st.session_state.clear()
        st.rerun()
    st.stop()

q = st.session_state.current_list[st.session_state.current_idx]
ans_text = q.get('english', q.get('answer', ''))

st.write(f"### 第{st.session_state.current_idx + 1}問 / {len(st.session_state.current_list)}")
st.write(f"## {q.get('japanese', '')}")

tab1, tab2, tab3 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声"])

# 写真処理
cropped_image = None
with tab1:
    cam_file = st.camera_input("カメラ", key=f"c_{st.session_state.current_idx}")
    img_file = st.file_uploader("画像を選択", type=['png', 'jpg', 'jpeg'], key=f"u_{st.session_state.current_idx}")
    raw_img = cam_file if cam_file else img_file
    if raw_img:
        cropped_image = st_cropper(Image.open(raw_img), realtime_update=True, box_color='#f39c12')

with tab2:
    typed_answer = st.text_input("英文を入力", key=f"t_{st.session_state.current_idx}")

with tab3:
    audio_data = st.audio_input("声に出して解答", key=f"a_{st.session_state.current_idx}")

# --- 採点ロジック ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 採点する"):
        if not (typed_answer or audio_data or cropped_image):
            st.warning("⚠️ 解答を入力してください。")
        else:
            with st.spinner("AIが確認中..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    # 404エラー回避のため「models/」を省いて指定
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"日本文: {q.get('japanese','')}\n正解例: {ans_text}\n文法的に正しければ別解も正解として添削してください。不合格、記号**、カギカッコは一切使わず、前向きな言葉で。正解なら必ず『正解です』と含めること。"

                    # 入力形式に応じてAIへの渡し方を変える
                    if cropped_image:
                        response = model.generate_content([prompt, cropped_image])
                    elif audio_data:
                        response = model.generate_content([prompt, {"mime_type": "audio/wav", "data": audio_data.read()}])
                    else:
                        response = model.generate_content(f"{prompt}\n生徒解答: {typed_answer}")
                    
                    clean_text = re.sub(r'[\*「」『』]', '', response.text)
                    st.session_state.feedback_text, st.session_state.show_feedback = clean_text, True
                    if "正解です" in clean_text: st.session_state.score += 1
                except Exception as e:
                    st.error(f"AIエラー: {e}")

with col2:
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list): st.session_state.finished = True
        st.session_state.show_feedback = False
        st.rerun()

if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<br><br><b>模範解答：{ans_text}</b></div>", unsafe_allow_html=True)
    tts = gTTS(ans_text, lang='en')
    af = io.BytesIO()
    tts.write_to_fp(af)
    st.audio(af, autoplay=True)
