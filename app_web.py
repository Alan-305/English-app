import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io
import random
import requests
from PIL import Image
from streamlit_cropper import st_cropper
import re

# --- 1. ページ設定 ---
st.set_page_config(page_title="基礎シリーズ_英語②_T_重要文例", layout="centered")

# デザイン設定（サイドバーやメニューが消えないように調整）
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
    .feedback-container { background-color: #fff9f0; padding: 20px; border-radius: 15px; border-left: 8px solid #f39c12; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ_英語②_T_重要文例</h1>", unsafe_allow_html=True)

# --- 2. セッション変数の初期化 ---
keys = ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text', 'user_answer']
for key in keys:
    if key not in st.session_state:
        st.session_state[key] = False if 'finished' in key or 'show' in key else (0 if 'idx' in key or 'score' in key else None)

# --- 3. データの読み込み ---
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except:
        st.error("questions.csvが読み込めません。")
        st.stop()

# --- 4. サイドバー ---
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

# --- 5. メイン画面の分岐 ---
if st.session_state.current_list is None:
    st.info("👈 左側のメニューから講を選んで「学習スタート」を押してください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.markdown(f"<div style='text-align:center;'><h2>最終スコア</h2><p style='font-size:3em;color:#e67e22;font-weight:bold;'>{st.session_state.score} / {len(st.session_state.current_list)}</p></div>", unsafe_allow_html=True)
    if st.button("もう一度挑戦"):
        st.session_state.clear()
        st.rerun()
    st.stop()

# 現在の問題データ
q = st.session_state.current_list[st.session_state.current_idx]
q_text = q.get('japanese', q.get('question', '問題文なし'))
ans_text = q.get('english', q.get('answer', ''))

st.markdown(f"<p style='color:#784212; margin-bottom:5px;'>第{q.get('no', st.session_state.current_idx + 1)}問 ({st.session_state.current_idx + 1}/{len(st.session_state.current_list)})</p><h3 style='color:#784212; margin-top:0;'>{q_text}</h3>", unsafe_allow_html=True)

# --- 6. タブ機能の完全復活 ---
tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])

input_user_text = ""
with tab1:
    st.write("👇 撮影またはアップロードしてください。")
    cam_file = st.camera_input("カメラ", key=f"c_{st.session_state.current_idx}")
    img_file = st.file_uploader("画像を選択", type=['png', 'jpg', 'jpeg'], key=f"u_{st.session_state.current_idx}")
    raw = cam_file if cam_file else img_file
    if raw:
        try: st_cropper(Image.open(raw), realtime_update=True, box_color='#f39c12', aspect_ratio=None)
        except: st.info("画像を表示中...")

with tab2:
    input_user_text = st.text_input("回答をタイピング", key=f"t_{st.session_state.current_idx}")

with tab3:
    st.audio_input("録音して解答", key=f"a_{st.session_state.current_idx}")

with tab4:
    st.subheader("松尾先生への報告")
    with st.form(key="support_form", clear_on_submit=True):
        sender = st.text_input("お名前")
        msg = st.text_area("メッセージ内容")
        if st.form_submit_button("送信"):
            st.success("（デモ）報告を送信しました。")

# --- 7. 採点とNextボタン ---
st.markdown("---")
c1, c2 = st.columns(2)

with c1:
    if st.button("🚀 採点する"):
        if input_user_text:
            with st.spinner("Pro版AIが添削中..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    prompt = f"日本文:{q_text}\n正解例:{ans_text}\n生徒解答:{input_user_text}\n文法的に正しければ正解。不合格、記号**、カギカッコは禁止。励まして。"
                    res = model.generate_content(prompt)
                    clean_text = re.sub(r'[\*「」『』]', '', res.text)
                    st.session_state.feedback_text, st.session_state.show_feedback = clean_text, True
                    if "正解" in clean_text: st.session_state.score += 1
                except Exception as e:
                    st.error(f"AIエラー: {e}")
        else:
            st.warning("「打ち込み」タブに回答を入力してください。")

with col2 if 'col2' in locals() else c2:
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
