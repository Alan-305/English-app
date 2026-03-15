import streamlit as st
from google import genai
from google.genai import types
import pandas as pd

# 1. ページ設定
st.set_page_config(page_title="基礎S_英語表現T_重要文例Lab", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #D6EAF8; }
    </style>
    """, unsafe_allow_html=True)

# 2. Geminiの準備と「使えるモデル」の自動検索
if 'client' not in st.session_state:
    try:
        # 窓口をデフォルトに戻して接続
        client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        st.session_state.client = client
        
        # --- ここが重要：今使えるモデルをGoogleに聞いて、一番いいものを選ぶ ---
        available_models = [m.name for m in client.models.list() if 'flash' in m.name.lower()]
        if available_models:
            # 例: 'models/gemini-2.0-flash' などが見つかる
            st.session_state.target_model = available_models[0]
        else:
            st.session_state.target_model = 'gemini-2.0-flash' # 保険
            
    except Exception as e:
        st.error(f"接続の準備でエラーが発生しました: {e}")

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

# 自動で見つかったモデル名をこっそり表示（デバッグ用）
if 'target_model' in st.session_state:
    st.caption(f"使用中のAIエンジン: {st.session_state.target_model}")

q = st.session_state.quiz_list[st.session_state.current_idx]
st.subheader(f"Problem {st.session_state.current_idx + 1}: {q['japanese']}")

user_ans = st.text_input("Answer:", key=f"ans_{st.session_state.current_idx}")

col1, col2 = st.columns(2)

with col1:
    if st.button("採点"):
        sys_inst = f"あなたは親切な日本人の英語教師です。生徒の解答を採点し、必ず【日本語で】正解例 {q['english']} と比較しながら詳しく解説してください。"        
        try:
            res = st.session_state.client.models.generate_content(
                model=st.session_state.target_model, # 自動検知したモデルを使用
                contents=f"生徒回答：{user_ans}"
            )
            st.session_state.feedback_text = res.text
            st.session_state.show_feedback = True
        except Exception as e:
            st.error(f"採点エラー詳細: {e}")

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
