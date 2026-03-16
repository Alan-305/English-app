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

# 1. ページ設定とスマホ特化デザイン（カメラ画面最大化）
st.set_page_config(page_title="基礎シリーズ 英語②T", layout="centered")

st.markdown("""
<style>
    .stApp { background: linear-gradient(135deg, #ffffff 0%, #fff3e0 100%); }
    .main-title { 
        color: #e67e22; text-align: center; font-weight: 700; 
        font-size: 1.5em; padding: 10px 0; border-bottom: 3px solid #ffcc80; 
        font-family: 'serif'; margin-bottom: 15px;
    }

    /* カメラ画面を大きく表示 */
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
    
    /* 解説文・英文表示の統一（記号なしで大きく表示） */
    .feedback-container b, .feedback-container strong { 
        font-family: 'serif'; font-size: 1.35em; color: #784212; 
        background-color: #fff3e0; padding: 0 4px; font-weight: bold;
    }

    .model-answer-text { font-family: 'serif'; font-size: 1.4em; font-weight: bold; margin-top: 15px; color: #784212; border-top: 1px dashed #ffcc80; padding-top: 10px; }
</style>
""", unsafe_allow_html=True)

# 2. 変数の初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text']:
    if key not in st.session_state:
        st.session_state[key] = False if key in ['finished', 'show_feedback'] else (0 if key not in ['current_list', 'feedback_text'] else None)

# 3. AI設定
if 'target_model' not in st.session_state or st.session_state.target_model is None:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_models = [m for m in available_models if 'flash' in m]
        st.session_state.target_model = flash_models[0] if flash_models else available_models[0]
    except: st.session_state.target_model = "models/gemini-1.5-flash"

# 4. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except: st.stop()

# --- サイドバー ---
st.sidebar.title("📚 Menu")
if st.sidebar.button("最初からリセット"):
    st.session_state.clear()
    st.rerun()

kous = sorted(list(set([q['kou'] for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択してください", kous)

if st.sidebar.button("学習スタート"):
    if selected_kous:
        selected_data = [q for q in st.session_state.all_questions if q['kou'] in selected_kous]
        if selected_data:
            st.session_state.current_list, st.session_state.current_idx, st.session_state.score = selected_data, 0, 0
            st.session_state.finished, st.session_state.show_feedback = False, False
            st.rerun()

# --- メイン画面 ---
if st.session_state.current_list is None:
    st.markdown("<h1 class='main-title'>基礎シリーズ 英語②T（表現）</h1>", unsafe_allow_html=True)
    st.info("メニューから「講」を選んで「学習スタート」を押してください。")
    st.stop()

if st.session_state.finished:
    st.markdown("<h1 class='main-title'>Result 🎉</h1>", unsafe_allow_html=True)
    st.markdown(f"<div style='text-align:center;'><h2>最終スコア</h2><p style='font-size:3em;color:#e67e22;font-weight:bold;'>{st.session_state.score} / {len(st.session_state.current_list)}</p></div>", unsafe_allow_html=True)
    if st.button("もう一度挑戦"):
        st.session_state.finished, st.session_state.current_idx, st.session_state.current_list = False, 0, None
        st.rerun()
    st.stop()

st.markdown("<h1 class='main-title'>基礎シリーズ 英語②T（表現）</h1>", unsafe_allow_html=True)
q = st.session_state.current_list[st.session_state.current_idx]
st.markdown(f"<p style='color:#784212; margin-bottom:5px;'>第{q['no']}問 ({st.session_state.current_idx + 1}/{len(st.session_state.current_list)})</p><h3 style='color:#784212; margin-top:0;'>{q['japanese']}</h3>", unsafe_allow_html=True)

# --- 入力タブ ---
tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])

cropped_image = None
with tab1:
    cam_file = st.camera_input("カメラ", key=f"c_{st.session_state.current_idx}")
    img_file = st.file_uploader("画像から選択", type=['png', 'jpg', 'jpeg'], key=f"u_{st.session_state.current_idx}")
    raw = cam_file if cam_file else img_file
    if raw:
        try: cropped_image = st_cropper(Image.open(raw), realtime_update=True, box_color='#f39c12', aspect_ratio=None)
        except: st.empty()

with tab2: user_text = st.text_input("回答をタイピング", key=f"t_{st.session_state.current_idx}")
with tab3: audio_file = st.audio_input("録音して提出", key=f"a_{st.session_state.current_idx}")

with tab4:
    st.subheader("松尾先生への報告")
    WEB_APP_URL = "ここにあなたのGASのURLを貼り付けてください" 
    with st.form(key="support_form", clear_on_submit=True):
        sender = st.text_input("お名前")
        msg = st.text_area("メッセージ")
        if st.form_submit_button("送信"):
            if WEB_APP_URL.startswith("http"):
                requests.post(WEB_APP_URL, json={"name": sender, "message": msg})
                st.success("送信しました！")

# --- ヒント機能 ---
st.markdown("---")
with st.expander("💡 ヒント（文字または音声）"):
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        if st.button("文字で見る"):
            words = q['english'].split()
            st.info(f"冒頭: {' '.join(words[:3])} ...")
    with h_col2:
        if st.button("音声を聞く"):
            tts_h = gTTS(q['english'], lang='en')
            af_h = io.BytesIO()
            tts_h.write_to_fp(af_h)
            st.audio(af_h)

# --- 採点アクション ---
# 録音データがある場合、停止ボタンを押していなくても「採点する」で進めるようロジックを構成
if st.button("🚀 採点する"):
    if not (cropped_image or user_text or audio_file):
        st.warning("解答を提出してください。")
    else:
        with st.spinner("添削中..."):
            try:
                model = genai.GenerativeModel(st.session_state.target_model)
                inst = f"""
                あなたは経験豊富な英語予備校講師です。正解例『{q['english']}』と比較し、以下の通り添削してください。
                - 1行目は必ず『あなたの英語：<b>[文字起こし結果]</b>』としてください。アスタリスク(**)や記号は絶対に使わないこと。
                - 文法的に正しく、意味が完全に通じる別解であれば、正解例と単語が異なっても正解としてください。
                - ミスがある場合は『惜しいです！ここを見直しましょう』と前向きに。不合格という言葉は禁止。
                - 解説の英文は <b>英文</b> とタグで囲み、それ以外の記号（**や「」『』）は絶対に使わないこと。
                - 正解または妥当な別解の場合は、必ず文中に『正解です』と含めてください。
                """
                if audio_file: res = model.generate_content([inst, {"mime_type": "audio/wav", "data": audio_file.read()}])
                elif cropped_image: res = model.generate_content([inst, cropped_image])
                else: res = model.generate_content(f"{inst}\n生徒：{user_text}")
                
                # 強制フィルタ：記号や引用符を徹底排除
                cleaned = res.text.replace("**", "").replace("「", "").replace("」", "").replace("『", "").replace("』", "")
                st.session_state.feedback_text, st.session_state.show_feedback = cleaned, True
                if "正解です" in cleaned: st.session_state.score += 1; st.balloons()
            except Exception as e: st.error(f"Error: {e}")

if st.session_state.show_feedback:
    st.markdown("---")
    st.markdown(f"<div class='feedback-container'><div>{st.session_state.feedback_text}</div><div class='model-answer-text'>模範解答：{q['english']}</div></div>", unsafe_allow_html=True)
    tts = gTTS(q['english'], lang='en')
    audio_fp = io.BytesIO()
    tts.write_to_fp(audio_fp)
    st.audio(audio_fp)
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list): st.session_state.finished = True
        st.session_state.show_feedback = False
        st.rerun()
