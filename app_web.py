import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image
from streamlit_cropper import st_cropper
import datetime
import requests
import re

# 1. ページ設定
st.set_page_config(page_title="基礎シリーズ_英語②_T_重要文例", layout="centered")

# 2. デザイン設定（昨日の安定デザインを継承）
st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #ffffff 0%, #fff3e0 100%); }
    .main-title { 
        color: #e67e22; text-align: center; font-weight: 700; 
        font-size: 1.5em; padding: 10px 0; border-bottom: 3px solid #ffcc80; 
        font-family: 'serif'; margin-bottom: 15px;
    }
    [data-testid="stCameraInput"] { width: 100% !important; }
    [data-testid="stCameraInput"] video { border-radius: 10px !important; width: 100% !important; height: auto !important; aspect-ratio: 4/3 !important; }
    
    div.stButton > button { 
        background-color: #f39c12 !important; color: white !important; 
        border-radius: 15px !important; height: 3.5em !important; 
        font-size: 1.1em !important; font-weight: bold !important; 
        border: none !important; width: 100%; margin-bottom: 8px;
    }
    div[data-testid="stVerticalBlock"] > div:has(div.stTabs) { 
        background-color: white !important; padding: 15px !important; 
        border-radius: 15px !important; border: 1px solid #ffe0b2 !important; 
    }
    .feedback-container { background-color: #fff9f0; padding: 15px; border-radius: 10px; border-left: 6px solid #f39c12; font-size: 1.1em; color: #5d4037; }
    
    .feedback-container b, .feedback-container strong { 
        font-family: 'serif'; font-size: 1.35em; color: #784212; 
        background-color: #fff3e0; padding: 0 4px; font-weight: bold;
    }
    .model-answer-text { font-family: 'serif'; font-size: 1.4em; font-weight: bold; margin-top: 15px; color: #784212; border-top: 1px dashed #ffcc80; padding-top: 10px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ_英語②_T_重要文例</h1>", unsafe_allow_html=True)

# 3. 変数の初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text']:
    if key not in st.session_state:
        st.session_state[key] = False if key in ['finished', 'show_feedback'] else (0 if key not in ['current_list', 'feedback_text'] else None)

# 4. AI設定 (Proモデルを優先、エラー時はFlashへ自動回避)
if 'target_model' not in st.session_state or st.session_state.target_model is None:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        # Proモデルをデフォルトに設定
        st.session_state.target_model = "gemini-1.5-pro"
    except:
        st.session_state.target_model = "gemini-1.5-flash"

# 5. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except:
        st.error("問題データ(questions.csv)を読み込めません。")
        st.stop()

# --- サイドバー：昨日の機能 + ランダム設定 ---
st.sidebar.title("📚 Menu")
with st.sidebar.expander("⚠️ スマホで動かない場合"):
    st.write("1. URLが **https** で始まっているか確認。")
    st.write("2. ブラウザの設定でカメラとマイクを**許可**してください。")

if st.sidebar.button("最初からリセット"):
    st.session_state.clear()
    st.rerun()

# 列名 kou または lecture に対応
kou_key = 'kou' if 'kou' in st.session_state.all_questions[0] else 'lecture'
kous = sorted(list(set([str(q[kou_key]) for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択してください", kous)

# 【新機能】出題順の選択
order_type = st.sidebar.radio("出題順を選択", ["順番通り", "ランダム"])

if st.sidebar.button("学習スタート"):
    if selected_kous:
        selected_data = [q for q in st.session_state.all_questions if str(q[kou_key]) in selected_kous]
        if selected_data:
            # 【新機能】ランダム処理
            if order_type == "ランダム":
                random.shuffle(selected_data)
            st.session_state.current_list, st.session_state.current_idx, st.session_state.score = selected_data, 0, 0
            st.session_state.finished, st.session_state.show_feedback = False, False
            st.rerun()

# --- メイン画面 ---
if st.session_state.current_list is None:
    st.info("👈 左側のメニューから「講」を選んで「学習スタート」を押してください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.markdown(f"<div style='text-align:center;'><h2>最終スコア</h2><p style='font-size:3em;color:#e67e22;font-weight:bold;'>{st.session_state.score} / {len(st.session_state.current_list)}</p></div>", unsafe_allow_html=True)
    if st.button("もう一度挑戦"):
        st.session_state.finished, st.session_state.current_idx, st.session_state.current_list = False, 0, None
        st.rerun()
    st.stop()

# 現在の問題（japanese または question に対応）
q = st.session_state.current_list[st.session_state.current_idx]
q_no = q.get('no', st.session_state.current_idx + 1)
q_text = q.get('japanese', q.get('question', '問題文エラー'))
ans_text = q.get('english', q.get('answer', ''))

st.markdown(f"<p style='color:#784212; margin-bottom:5px;'>第{q_no}問 ({st.session_state.current_idx + 1}/{len(st.session_state.current_list)})</p><h3 style='color:#784212; margin-top:0;'>{q_text}</h3>", unsafe_allow_html=True)

# 入力タブ
tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])

cropped_image = None
with tab1:
    st.write("👇 カメラボタンを押して撮影、または下の「画像を選択」からアップしてください。")
    cam_file = st.camera_input("カメラ", key=f"c_{st.session_state.current_idx}")
    img_file = st.file_uploader("画像を選択", type=['png', 'jpg', 'jpeg'], key=f"u_{st.session_state.current_idx}")
    raw = cam_file if cam_file else img_file
    if raw:
        try: cropped_image = st_cropper(Image.open(raw), realtime_update=True, box_color='#f39c12', aspect_ratio=None)
        except: st.info("画像を表示中...")

with tab2: user_text = st.text_input("回答をタイピング", key=f"t_{st.session_state.current_idx}")
with tab3: audio_file = st.audio_input("録音して解答", key=f"a_{st.session_state.current_idx}")

with tab4:
    st.subheader("松尾先生への報告")
    WEB_APP_URL = "https://script.google.com/macros/s/XXXXX/exec" 
    with st.form(key="support_form", clear_on_submit=True):
        sender = st.text_input("お名前")
        msg = st.text_area("メッセージ内容")
        if st.form_submit_button("送信"):
            if WEB_APP_URL.startswith("http"):
                try:
                    requests.post(WEB_APP_URL, json={"name": sender, "message": msg})
                    st.success("送信完了しました！")
                except: st.error("送信エラー")

st.markdown("---")

# 昨日のヒント機能も完備
with st.expander("💡 ヒント（文字または音声）"):
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        if st.button("文字で見る"):
            words = ans_text.split()
            st.info(f"冒頭: {' '.join(words[:3])} ...")
    with h_col2:
        if st.button("音声を聞く"):
            tts_h = gTTS(ans_text, lang='en')
            af_h = io.BytesIO()
            tts_h.write_to_fp(af_h)
            st.audio(af_h, autoplay=True)

# 【新機能】採点とNextボタンの並列配置
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 採点する"):
        if not (cropped_image or user_text or audio_file):
            st.warning("⚠️ 解答を入力してください。")
        else:
            with st.spinner("Pro版AIが添削中..."):
                try:
                    # モデルの指定 (404エラー回避策)
                    try:
                        model = genai.GenerativeModel("gemini-1.5-pro")
                    except:
                        model = genai.GenerativeModel("gemini-1.5-flash")
                        
                    inst = f"""
                    あなたは情熱的な英語講師です。正解例『{ans_text}』と比較してください。
                    
                    【厳守ルール】
                    - 文法的に正しく意味が通じれば別解も正解(Perfect!)とすること。
                    - 「不合格」という言葉は絶対に使わないこと。
                    - 最後は生徒が次も頑張りたくなるような前向きな言葉で締めること。
                    - 記号 ** は一切禁止。
                    - 英文に「」はつけない。
                    - 正解なら『正解です』と必ず含める。
                    """
                    if audio_file: res = model.generate_content([inst, {"mime_type": "audio/wav", "data": audio_file.read()}])
                    elif cropped_image: res = model.generate_content([inst, cropped_image])
                    else: res = model.generate_content(f"{inst}\n生徒：{user_text}")
                    
                    # 物理フィルターで記号を徹底削除
                    f_text = res.text.replace("**", "").replace("「", "").replace("」", "").replace("『", "").replace("』", "")
                    st.session_state.feedback_text, st.session_state.show_feedback = f_text, True
                    if "正解です" in f_text: st.session_state.score += 1; st.balloons()
                except Exception as e: st.error(f"Error: {e}")

with col2:
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list):
            st.session_state.finished = True
        st.session_state.show_feedback = False
        st.rerun()

if st.session_state.show_feedback:
    st.markdown("---")
    st.markdown(f"<div class='feedback-container'><div>{st.session_state.feedback_text}</div><div class='model-answer-text'>模範解答：{ans_text}</div></div>", unsafe_allow_html=True)
    tts = gTTS(ans_text, lang='en')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    st.audio(audio_fp, autoplay=True)
