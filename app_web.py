import streamlit as st
from google import genai
from google.genai import types
import pandas as pd
import random
from gtts import gTTS
import io

# 1. ページ設定とデザイン
st.set_page_config(page_title="基礎S_英語表現T_重要文例Lab", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #D6EAF8; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; font-size: 1.1em; }
    h1, h2, h3 { color: #1B4F72; }
    .stTextInput>div>div>input { font-size: 1.2em; }
    </style>
    """, unsafe_allow_html=True)

# 2. 初期設定（ライブラリの新しい書き方に対応）
if 'client' not in st.session_state:
    try:
        st.session_state.client = genai.Client(api_key=st.secrets["GEMINI_API_KEY"])
        # 最新の書き方でモデルリストを取得
        available_models = [m.name for m in st.session_state.client.list_models() if 'flash' in m.name.lower()]
        st.session_state.target_model = available_models[0] if available_models else 'gemini-1.5-flash'
    except Exception as e:
        st.error(f"接続の準備に失敗しました: {e}")

# 3. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except Exception as e:
        st.error(f"CSVエラー: {e}")
        st.stop()

# --- サイドバー設定 ---
st.sidebar.title("🛠️ 学習設定")

kou_list = sorted(list(set([q['kou'] for q in st.session_state.all_questions])), 
                  key=lambda x: str(x))

selected_kous = st.sidebar.multiselect("学習する講を選択", kou_list, default=[kou_list[0]] if kou_list else [])
order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

if st.sidebar.button("この設定で開始/リセット"):
    selected_data = [q for q in st.session_state.all_questions if q['kou'] in selected_kous]
    if order_type == "ランダム":
        random.shuffle(selected_data)
    st.session_state.current_list = selected_data
    st.session_state.current_idx = 0
    st.session_state.show_feedback = False
    st.session_state.feedback_text = ""
    st.rerun()

# --- メイン画面 ---
if 'current_list' not in st.session_state:
    st.info("左のサイドバーから講を選んで「開始」ボタンを押してください。")
    st.stop()

st.title("基礎S_英語表現T_重要文例Lab")

q = st.session_state.current_list[st.session_state.current_idx]

st.subheader(f"問 {q['no']}: {q['japanese']}")
st.caption(f"（{q['kou']} - {st.session_state.current_idx + 1} / {len(st.session_state.current_list)} 問目）")

user_ans = st.text_input("あなたの答え:", key=f"ans_{st.session_state.current_idx}")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("採点"):
        sys_inst = f"あなたは親切な日本人の英語教師です。解答を採点し、必ず【日本語のみ】で正解例 {q['english']} と比較して解説してください。見出しを使わず、標準的な文字サイズで回答してください。"
        try:
            # 最新の生成メソッドを使用
            res = st.session_state.client.generate_content(
                model=st.session_state.target_model,
                contents=f"生徒回答：{user_ans}",
                config=types.GenerateContentConfig(system_instruction=sys_inst)
            )
            st.session_state.feedback_text = res.text
            st.session_state.show_feedback = True
            
            user_clean = "".join(e for e in user_ans if e.isalnum()).lower()
            correct_clean = "".join(e for e in q['english'] if e.isalnum()).lower()
            if user_clean == correct_clean:
                st.balloons()
        except Exception as e:
            st.error(f"採点中にエラーが発生しました: {e}")

with col2:
    if st.button("正解と音声"):
        st.session_state.show_feedback = True
        st.session_state.feedback_text = "正解例と音声を確認して、音読してみましょう！"

with col3:
    if st.button("次へ"):
        if st.session_state.current_idx < len(st.session_state.current_list) - 1:
            st.session_state.current_idx += 1
            st.session_state.show_feedback = False
            st.rerun()
        else:
            st.success("全ての選んだ問題が終わりました！")

# 結果表示
if st.session_state.show_feedback:
    st.info(st.session_state.feedback_text)
    st.write(f"**【正解例】** {q['english']}")
    
    tts = gTTS(q['english'], lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    st.audio(fp)
