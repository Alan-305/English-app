import streamlit as st
import pandas as pd
import random
import re
import os
from google import genai
from google.genai import types
from gtts import gTTS
import base64

# --- ページ設定 ---
st.set_page_config(page_title="基礎S_英語表現T_重要文例Lab", layout="centered")

# カスタムCSSで水色の背景とデザインを調整
st.markdown("""
    <style>
    .stApp { background-color: #B3E5FC; }
    .stButton>button { width: 100%; border-radius: 10px; }
    .main-title { color: #004D61; text-align: center; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- Geminiの初期設定（アプリ起動時に1回だけ実行） ---
if 'client' not in st.session_state:
    try:
        # SecretsからAPIキーを読み込んでGeminiを準備
        st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
    except Exception as e:
        st.error(f"APIキーの設定に問題があります: {e}")

# --- 問題データの読み込み ---
if 'quiz_list' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        st.session_state.quiz_list = df.to_dict('records')
    except Exception as e:
        st.error(f"CSVファイルの読み込みに失敗しました: {e}")
if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0
    st.session_state.quiz_list = []
    st.session_state.started = False

def play_audio(text):
    tts = gTTS(text=text, lang='en')
    tts.save("temp.mp3")
    with open("temp.mp3", "rb") as f:
        data = f.read()
        b64 = base64.b64encode(data).decode()
        md = f'<audio autoplay="true" src="data:audio/mp3;base64,{b64}">'
        st.markdown(md, unsafe_allow_html=True)

def clean_text(text):
    text = re.sub(r'[*#\-_]{2,}', '', text)
    text = text.replace('「', '').replace('」', '')
    return text.strip()

# --- 画面構成 ---
st.markdown("<h1 class='main-title'>基礎S_英語表現T_重要文例Lab</h1>", unsafe_allow_html=True)

if not st.session_state.started:
    # 設定画面
    st.subheader("学習設定")
    start_num = st.number_input("開始番号", min_value=1, value=1)
    end_num = st.number_input("終了番号", min_value=1, value=len(st.session_state.questions))
    is_random = st.checkbox("問題をランダムにする")
    mute = st.checkbox("音声を流さない（ミュート）")
    st.session_state.mute = mute

    if st.button("学習開始"):
        selected = st.session_state.questions[start_num-1 : end_num]
        if is_random:
            random.shuffle(selected)
        st.session_state.quiz_list = selected
        st.session_state.current_idx = 0
        st.session_state.started = True
        st.rerun()

else:
    # クイズ画面
    q = st.session_state.quiz_list[st.session_state.current_idx]
    st.info(f"問題: {q.get('japanese') or q.get('日本語')}")
    
    user_ans = st.text_area("ここに英語を入力してください", height=100)
    
    col1, col2, col3, col4 = st.columns(4)
    
    if col1.button("採点"):
        model_ans = q.get('english') or q.get('英語')
        sys_inst = f"英語講師。モデル回答：{model_ans}。100点満点で採点し、日本語で解説。記号や「」は厳禁。"
        res = st.session_state.client.models.generate_content(
            model='gemini-2.0-flash',
            config=types.GenerateContentConfig(system_instruction=sys_inst),
            contents=f"生徒回答：{user_ans}"
        )
        st.session_state.result_text = clean_text(res.text)
        if not st.session_state.mute:
            play_audio(model_ans)

    if col2.button("ヒント"):
        model_ans = q.get('english') or q.get('英語')
        hint = " ".join(model_ans.split()[:3]) + " ..."
        st.warning(f"ヒント: {hint}")

    if col3.button("再生"):
        model_ans = q.get('english') or q.get('英語')
        play_audio(model_ans)

    if col4.button("次へ"):
        if st.session_state.current_idx < len(st.session_state.quiz_questions) - 1:
            st.session_state.current_idx += 1
            st.rerun()
        else:
            st.success("全問終了！")
            st.session_state.started = False
            st.rerun()

    if 'result_text' in st.session_state:
        st.success(st.session_state.result_text)

    # 質問コーナー
    st.divider()
    user_query = st.text_input("💡 質問コーナー")
    if user_query:
        res_q = st.session_state.client.models.generate_content(
            model='gemini-2.0-flash',
            contents=f"質問：{user_query}\n日本語で回答。"
        )
        st.write(clean_text(res_q.text))
