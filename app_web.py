import os
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
st.set_page_config(page_title="基礎シリーズ_英語②_T_重要文例", layout="centered")

# CSS: 先生こだわりのデザイン
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: "MS PMincho", "Hiragino Mincho ProN", serif; }
    .stApp { background: linear-gradient(135deg, #ffffff 0%, #fff3e0 100%); }
    .main-title { color: #e67e22; text-align: center; font-weight: 700; font-size: 1.2em; padding: 8px 0; border-bottom: 3px solid #ffcc80; margin-bottom: 12px; }
    .q-label, .q-text { font-size: 1.2em; color: #784212; font-weight: bold; }
    
    .feedback-container { 
        background-color: #fff9f0; padding: 12px 18px; border-radius: 15px; 
        border-left: 8px solid #f39c12; margin-top: 10px; white-space: pre-line; 
        line-height: 1.25 !important; font-size: 1.05em; color: #4e342e; 
    }
    .feedback-container * { margin-top: 0px !important; margin-bottom: 2px !important; }
    
    .feedback-container b, .feedback-container strong { 
        font-family: "Century", serif; font-size: 1.05em; 
        color: #784212; background-color: #fff3e0; padding: 0 2px; 
    }
    .model-answer-text { 
        font-family: "Century", serif; font-size: 1.05em; font-weight: bold; 
        margin-top: 8px !important; color: #784212; border-top: 1px dashed #ffcc80; padding-top: 5px; 
    }
    div.stButton > button { background-color: #f39c12 !important; color: white !important; border-radius: 15px !important; height: 3.5em !important; font-weight: bold !important; width: 100%; }
    
    .chat-bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 10px; line-height: 1.4; font-size: 1.05em; }
    .user-bubble { background-color: #ffe0b2; color: #784212; }
    .ai-bubble { background-color: #ffffff; border: 1px solid #ffcc80; color: #4e342e; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ_英語②_T_重要文例</h1>", unsafe_allow_html=True)

# 2. 変数初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text', 'chat_history']:
    if key not in st.session_state:
        if key == 'chat_history': st.session_state[key] = []
        else: st.session_state[key] = False if 'finished' in key or 'show' in key else (0 if 'idx' in key or 'score' in key else None)

# 3. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except:
        st.error("questions.csvが見つかりません。"); st.stop()

# 4. サイドバー
st.sidebar.title("📚 Menu")
if st.sidebar.button("リセット"): st.session_state.clear(); st.rerun()
all_kous = sorted(list(set([str(q.get('kou', '1')) for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択", all_kous)
order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

if st.sidebar.button("学習スタート"):
    if selected_kous:
        data = [q for q in st.session_state.all_questions if str(q.get('kou', '1')) in selected_kous]
        if order_type == "ランダム": random.shuffle(data)
        st.session_state.current_list, st.session_state.current_idx, st.session_state.score = data, 0, 0
        st.session_state.finished, st.session_state.show_feedback, st.session_state.chat_history = False, False, []; st.rerun()

if st.session_state.current_list is None:
    st.info("👈 講を選んでスタートしてください。"); st.stop()

if st.session_state.finished:
    st.balloons(); st.success(f"終了！ スコア: {st.session_state.score} / {len(st.session_state.current_list)}")
    if st.button("最初に戻る"): st.session_state.clear(); st.rerun()
    st.stop()

q = st.session_state.current_list[st.session_state.current_idx]
ans_text = q.get('english', q.get('answer', ''))

st.markdown(f"<div class='q-label'>第{st.session_state.current_idx + 1}問</div>", unsafe_allow_html=True)
st.markdown(f"<div class='q-text'>{q.get('japanese', '')}</div>", unsafe_allow_html=True)

# 6. タブ
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告", "❓ 質問コーナー"])

img_for_ai = None; input_type = "typed"
with tab1:
    raw = st.camera_input("撮影", key=f"c_{st.session_state.current_idx}")
    if raw: img_for_ai = st_cropper(Image.open(raw), realtime_update=True, box_color='#f39c12'); input_type = "image"
with tab2: typed_ans = st.text_input("回答を入力", key=f"t_{st.session_state.current_idx}")
with tab3:
    audio_data = st.audio_input("録音ボタンを押して解答", key=f"a_{st.session_state.current_idx}")
    if audio_data: input_type = "voice"

with tab4:
    with st.form("report_form"):
        u_name = st.text_input("お名前"); r_msg = st.text_area("メッセージ")
        if st.form_submit_button("送信"):
            if u_name and r_msg:
                try:
                    res = requests.post(st.secrets["GAS_WEBAPP_URL"], json={"name": u_name, "message": r_msg, "question": q.get('japanese', '')}, timeout=10)
                    if res.status_code == 200: st.success("先生に送信しました。")
                except: st.error("送信に失敗しました。")

# --- 💡 修正ポイント：質問コーナー（リターンキー送信無効版） ---
with tab5:
    st.subheader("🤖 AI講師に質問")
    for chat in st.session_state.chat_history:
        role_class = "user-bubble" if chat["role"] == "user" else "ai-bubble"
        st.markdown(f"<div class='chat-bubble {role_class}'>{chat['content']}</div>", unsafe_allow_html=True)

    # st.chat_inputの代わりにtext_areaを使用
    user_input_text = st.text_area("質問内容（リターンキーで改行できます）", key="chat_area", height=100)
    
    # 送信ボタン（⬆️）を明示的に配置
    if st.button("⬆️ 質問を送信する"):
        if user_input_text:
            st.session_state.chat_history.append({"role": "user", "content": user_input_text})
            with st.spinner("先生が考えています..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(next((m for m in available if 'flash' in m), 'gemini-1.5-flash'))
                    chat_instruction = f"""英語講師です。現在生徒は『{q.get('japanese','')}』(模範解答：{ans_text})を解いています。
                    【ルール】日本語は明朝体、英語はCentury。記号**は禁止。和訳は「」付。"""
                    response = model.generate_content([chat_instruction, user_input_text])
                    clean_reply = response.text.replace("**", "")
                    st.session_state.chat_history.append({"role": "ai", "content": clean_reply})
                    st.rerun()
                except: st.error("エラーが発生しました。")

# 8. 採点
st.markdown("---")
if st.button("🚀 採点する"):
    if not (typed_ans or audio_data or img_for_ai): st.warning("⚠️ 録音中の場合は **⏹️** を押してから採点に進んでください。")
    else:
        with st.spinner("添削中..."):
            try:
                genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                model = genai.GenerativeModel(next((m for m in available if 'flash' in m), 'gemini-1.5-flash'))
                voice_rule = "音声入力時は大文字小文字・句読点を一切不問とし、語順が合っていれば正解とせよ。" if input_type == "voice" else ""
                prompt = f"""英語講師として添削。日本文『{q.get('japanese','')}』、模範解答『{ans_text}』。{voice_rule}
                【構成】1:評価、2:あなたの解答：<b>[生徒の解答をCentury体で表示]</b>、(空行)、3:解説(和訳は「 」付)。不合格禁止。回答に**は入れない。"""
                inp = [prompt]
                if img_for_ai: inp.append(img_for_ai)
                elif audio_data: inp.append({"mime_type": "audio/wav", "data": audio_data.read()})
                else: inp.append(f"生徒の解答：{typed_ans}")
                res = model.generate_content(inp)
                f_text = res.text.replace("**", "")
                st.session_state.feedback_text, st.session_state.show_feedback = f_text, True
                if any(w in f_text for w in ["正解", "Perfect"]): st.session_state.score += 1; st.balloons()
            except: st.error("エラーが発生しました。")

if st.button("次へ進む ➔"):
    st.session_state.current_idx += 1
    if st.session_state.current_idx >= len(st.session_state.current_list): st.session_state.finished = True
    st.session_state.show_feedback = False; st.session_state.chat_history = []; st.rerun()

if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<div class='model-answer-text'>模範解答：{ans_text}</div></div>", unsafe_allow_html=True)
    tts_ans = gTTS(ans_text, lang='en'); af_ans = io.BytesIO(); tts_ans.write_to_fp(af_ans); st.audio(af_ans, autoplay=False)
