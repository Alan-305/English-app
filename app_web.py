import streamlit as st
from google import genai
from google.genai import types
import pandas as pd

# 1. ページ設定（水色の背景を確保）
st.set_page_config(page_title="基礎S_英語表現T_重要文例Lab", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #D6EAF8; }
    </style>
    """, unsafe_allow_html=True)

# 2. Geminiの準備（SDKにお任せする2026年標準設定）
if 'client' not in st.session_state:
    try:
        st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        # 使えるモデルを自動取得
        available_models = [m.name for m in st.session_state.client.models.list() if 'flash' in m.name.lower()]
        st.session_state.target_model = available_models[0] if available_models else 'gemini-1.5-flash'
    except Exception as e:
        st.error(f"接続の準備に失敗しました: {e}")

# 3. データの読み込み
if 'quiz_list' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.quiz_list = df.to_dict('records')
        st.session_state.current_idx = 0
        st.session_state.show_feedback = False
    except Exception as e:
        st.error(f"CSV読み込みエラー: {e}")
        st.stop()

# --- メイン画面 ---
st.title("基礎S_英語表現T_重要文例Lab")

q = st.session_state.quiz_list[st.session_state.current_idx]
st.subheader(f"Problem {st.session_state.current_idx + 1}: {q['japanese']}")

user_ans = st.text_input("Answer:", key=f"ans_{st.session_state.current_idx}")

col1, col2 = st.columns(2)

with col1:
    if st.button("採点"):
        # 日本語で、と強く指示します
        sys_inst = f"あなたは親切な日本人の英語教師です。解答を採点し、必ず【日本語のみ】で正解例 {q['english']} と比較して解説してください。回答の冒頭に大きな見出し（#や##）を使わず、太字（**）などを使って標準的な文字サイズで読みやすく構成してください。"        
        try:
            res = st.session_state.client.models.generate_content(
                model=st.session_state.target_model,
                config=types.GenerateContentConfig(system_instruction=sys_inst),
                contents=f"生徒回答：{user_ans}"
            )
            st.session_state.feedback_text = res.text
            st.session_state.show_feedback = True
            
            # --- 正解ならバルーンを飛ばす！ ---
            # 記号や空白を取り除いて「文字だけ」で比較する
            user_clean = "".join(e for e in user_ans if e.isalnum()).lower()
            correct_clean = "".join(e for e in q['english'] if e.isalnum()).lower()
            
            if user_clean == correct_clean:
                st.balloons()                
        except Exception as e:
            st.error(f"採点エラー: {e}")

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
    st.write(f"正解例: {q['english']}")
