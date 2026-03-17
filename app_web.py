import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io
import random
from PIL import Image
from streamlit_cropper import st_cropper
import requests
import re

# 1. ページ設定
st.set_page_config(page_title="基礎シリーズ 英語②T", layout="centered")

# デザイン（オレンジ基調）
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #ffffff 0%, #fff3e0 100%); }
    .main-title { color: #e67e22; text-align: center; font-weight: 700; font-size: 1.5em; border-bottom: 3px solid #ffcc80; padding: 10px; }
    div.stButton > button { background-color: #f39c12 !important; color: white !important; border-radius: 15px !important; width: 100%; height: 3.5em; font-weight: bold; }
    .feedback-container { background-color: #fff9f0; padding: 20px; border-radius: 15px; border-left: 8px solid #f39c12; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ 英語②T（表現）</h1>", unsafe_allow_html=True)

# 2. セッション変数の初期化
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
if st.sidebar.button("最初からリセット"):
    st.session_state.clear()
    st.rerun()

all_kous = sorted(list(set([str(q.get('kou', q.get('lecture', '1'))) for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択してください", all_kous)
order_type = st.sidebar.radio("出題順を選択", ["順番通り", "ランダム"])

if st.sidebar.button("学習スタート"):
    if selected_kous:
        data = [q for q in st.session_state.all_questions if str(q.get('kou', q.get('lecture', '1'))) in selected_kous]
        if order_type == "ランダム": random.shuffle(data)
        st.session_state.current_list, st.session_state.current_idx, st.session_state.score = data, 0, 0
        st.session_state.finished, st.session_state.show_feedback = False, False
        st.rerun()

# --- メイン画面 ---
if st.session_state.current_list is None:
    st.info("👈 左側のメニューから講を選んでスタートしてください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.markdown(f"<div style='text-align:center;'><h2>スコア: {st.session_state.score} / {len(st.session_state.current_list)}</h2></div>", unsafe_allow_html=True)
    if st.button("最初に戻る"):
        st.session_state.clear()
        st.rerun()
    st.stop()

q = st.session_state.current_list[st.session_state.current_idx]
ans_text = q.get('english', q.get('answer', ''))

st.write(f"### 第{st.session_state.current_idx+1}問 / {len(st.session_state.current_list)}")
st.write(f"## {q.get('japanese', '')}")

# タブの復活
tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])

# 写真処理
img_for_ai = None
with tab1:
    st.write("👇 解答を撮影してください。")
    cam_file = st.camera_input("カメラ", key=f"c_{st.session_state.current_idx}")
    img_file = st.file_uploader("または画像を選択", type=['png', 'jpg', 'jpeg'], key=f"u_{st.session_state.current_idx}")
    raw_img = cam_file if cam_file else img_file
    if raw_img:
        img_for_ai = st_cropper(Image.open(raw_img), realtime_update=True, box_color='#f39c12')

with tab2:
    typed_text = st.text_input("英文をタイピング", key=f"t_{st.session_state.current_idx}")

with tab3:
    audio_data = st.audio_input("声に出して解答", key=f"a_{st.session_state.current_idx}")

# 報告タブの復活
with tab4:
    st.subheader("松尾先生への報告")
    WEB_APP_URL = "https://script.google.com/macros/s/XXXXX/exec" # ← GASのURL
    with st.form(key="report_form", clear_on_submit=True):
        sender = st.text_input("お名前")
        msg = st.text_area("メッセージ（質問や報告など）")
        if st.form_submit_button("送信"):
            if WEB_APP_URL.startswith("http"):
                try:
                    requests.post(WEB_APP_URL, json={"name": sender, "message": msg})
                    st.success("先生にメッセージを送信しました！")
                except: st.error("送信に失敗しました。")
            else: st.info("※送信先URLが設定されていません。")

# --- 採点 ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 採点する"):
        if not (typed_text or audio_data or img_for_ai):
            st.warning("⚠️ 解答を入力してください。")
        else:
            with st.spinner("AIが確認中..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"あなたは英語教師です。日本文『{q.get('japanese','')}』に対し、生徒の解答を添削して。模範解答：{ans_text}。別解も正解(Perfect)として。不合格、記号**、カギカッコは禁止。励ましてください。正解なら『正解です』と含めて。"

                    if img_for_ai:
                        response = model.generate_content([prompt, img_for_ai])
                    elif audio_data:
                        response = model.generate_content([prompt, {"mime_type": "audio/wav", "data": audio_data.read()}])
                    else:
                        response = model.generate_content(f"{prompt}\n生徒解答：{typed_text}")
                    
                    clean_text = re.sub(r'[\*「」『』]', '', response.text)
                    st.session_state.feedback_text, st.session_state.show_feedback = clean_text, True
                    if "正解です" in clean_text or "Perfect" in clean_text:
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
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<br><br><b>模範解答：{ans_text}</b></div>", unsafe_allow_html=True)
    tts = gTTS(ans_text, lang='en')
    af = io.BytesIO()
    tts.write_to_fp(af)
    st.audio(af, autoplay=True)
