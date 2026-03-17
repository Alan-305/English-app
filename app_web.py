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

# --- 1. ページ設定（タイトルの修正） ---
st.set_page_config(page_title="基礎シリーズ_英語②_T_重要文例", layout="centered")

# --- 2. デザイン設定（サイドバーを隠さないCSS） ---
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
        width: 100%;
    }
    .feedback-container { background-color: #fff9f0; padding: 20px; border-radius: 15px; border-left: 8px solid #f39c12; color: #5d4037; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ_英語②_T_重要文例</h1>", unsafe_allow_html=True)

# --- 3. セッション変数の初期化 ---
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text']:
    if key not in st.session_state:
        st.session_state[key] = False if key in ['finished', 'show_feedback'] else (0 if key not in ['current_list', 'feedback_text'] else None)

# --- 4. データの読み込み ---
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        # 列名を正規化
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except Exception as e:
        st.error(f"questions.csvの読み込みエラー: {e}")
        st.stop()

# --- 5. サイドバー設定 ---
st.sidebar.title("📚 Menu")
if st.sidebar.button("最初からリセット"):
    st.session_state.clear()
    st.rerun()

# 講のリスト作成
all_kous = sorted(list(set([str(q.get('kou', q.get('lecture', '1'))) for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択してください", all_kous)
order_type = st.sidebar.radio("出題順を選択", ["順番通り", "ランダム"])

if st.sidebar.button("学習スタート"):
    if selected_kous:
        # 選択された講の問題を抽出
        data = [q for q in st.session_state.all_questions if str(q.get('kou', q.get('lecture', '1'))) in selected_kous]
        if data:
            if order_type == "ランダム":
                random.shuffle(data)
            st.session_state.current_list = data
            st.session_state.current_idx = 0
            st.session_state.score = 0
            st.session_state.finished = False
            st.session_state.show_feedback = False
            st.rerun()

# --- 6. メイン画面の制御 ---
if st.session_state.current_list is None:
    st.info("👈 左のメニューから「講」を選んで「学習スタート」を押してください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.success(f"全問題終了！ スコア: {st.session_state.score} / {len(st.session_state.current_list)}")
    if st.button("もう一度挑戦する"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# 現在の問題
q = st.session_state.current_list[st.session_state.current_idx]
q_text = q.get('japanese', q.get('question', '問題文なし'))
ans_text = q.get('english', q.get('answer', ''))

st.write(f"### 第{q.get('no', st.session_state.current_idx + 1)}問 ({st.session_state.current_idx + 1}/{len(st.session_state.current_list)})")
st.write(f"## {q_text}")

tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])

with tab1:
    cam_file = st.camera_input("解答を撮影", key=f"c_{st.session_state.current_idx}")
    img_file = st.file_uploader("または画像を選択", type=['png', 'jpg', 'jpeg'], key=f"u_{st.session_state.current_idx}")
    raw_img = cam_file if cam_file else img_file

with tab2:
    user_text = st.text_input("英文を入力してください", key=f"t_{st.session_state.current_idx}")

with tab3:
    audio_file = st.audio_input("声に出して解答", key=f"a_{st.session_state.current_idx}")

with tab4:
    st.write("松尾先生へのメッセージ")
    st.text_area("内容", key="msg")
    st.button("送信する")

# --- 7. 採点・Nextボタン ---
st.markdown("---")
c1, c2 = st.columns(2)

with c1:
    if st.button("🚀 採点する"):
        if not (user_text or raw_img or audio_file):
            st.warning("⚠️ 解答を入力してください。")
        else:
            with st.spinner("Pro版AIが添削中..."):
                try:
                    # 404エラー回避のため、モデル名を確実に指定
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    
                    prompt = f"""あなたは英語講師です。模範解答『{ans_text}』と比較し、生徒の解答を添削してください。
                    【ルール】
                    - 意味が通じれば別解も正解(Perfect!)とする。
                    - 不合格という言葉は使わず、前向きに励ますこと。
                    - 記号 ** や カギカッコ は使わないこと。
                    - 正解なら『正解です』という言葉を必ず含めること。"""
                    
                    # 入力形式に応じたAI呼び出し
                    if raw_img:
                        res = model.generate_content([prompt, Image.open(raw_img)])
                    elif audio_file:
                        res = model.generate_content([prompt, {"mime_type": "audio/wav", "data": audio_file.read()}])
                    else:
                        res = model.generate_content(f"{prompt}\n生徒解答：{user_text}")
                    
                    # 記号の強制排除
                    f_text = re.sub(r'[\*「」『』]', '', res.text)
                    st.session_state.feedback_text = f_text
                    st.session_state.show_feedback = True
                    if "正解です" in f_text:
                        st.session_state.score += 1
                except Exception as e:
                    st.error(f"AIエラー: {e} (Proモデルが準備中の可能性があります)")

with c2:
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list):
            st.session_state.finished = True
        st.session_state.show_feedback = False
        st.rerun()

# 結果表示
if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<br><br><b>模範解答：{ans_text}</b></div>", unsafe_allow_html=True)
    tts = gTTS(ans_text, lang='en')
    af = io.BytesIO()
    tts.write_to_fp(af)
    st.audio(af, autoplay=True)
