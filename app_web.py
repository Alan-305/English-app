import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import random
import os

# ページ設定
st.set_page_config(page_title="基礎S_英語表現T_重要文例Lab", layout="centered")

# --- 初期設定（起動時に一度だけ実行） ---
if 'client' not in st.session_state:
    # StreamlitのSecretsからキーを読み込む
    st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])

if 'quiz_list' not in st.session_state:
    df = pd.read_csv('questions.csv')
    st.session_state.quiz_list = df.to_dict('records')

if 'current_idx' not in st.session_state:
    st.session_state.current_idx = 0
    st.session_state.score = 0
    st.session_state.show_feedback = False
    st.session_state.feedback_text = ""

# --- メイン画面 ---
st.title("基礎S_英語表現T_重要文例Lab")

q = st.session_state.quiz_list[st.session_state.current_idx]
st.subheader(f"Problem {q['No']}: {q['Japanese']}")

user_ans = st.text_input("Answer:", key=f"input_{st.session_state.current_idx}")

col1, col2 = st.columns(2)

with col1:
    if st.button("採点"):
        # 採点ロジック
        sys_inst = f"あなたは英語教師です。以下の解答を採点し、{q['English']} と比較して解説してください。"
        try:
            res = st.session_state.client.models.generate_content(
                model='gemini-1.5-flash',
                config=types.GenerateContentConfig(system_instruction=sys_inst),
                contents=f"生徒回答：{user_ans}"
            )
            st.session_state.feedback_text = res.text
            st.session_state.show_feedback = True
        except Exception as e:
            st.error(f"接続エラーが発生しました。APIキーを確認してください。")

with col2:
    if st.button("次へ"):
        if st.session_state.current_idx < len(st.session_state.quiz_list) - 1:
            st.session_state.current_idx += 1
            st.session_state.show_feedback = False
            st.rerun()
        else:
            st.success("全問終了です！お疲れ様でした！")

if st.session_state.show_feedback:
    st.info(st.session_state.feedback_text)
    st.write(f"正解例: {q['English']}")
