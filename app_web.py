import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image

# 1. ページ設定
st.set_page_config(page_title="基礎S_英語表現T_重要文例Lab", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #D6EAF8; }
    .stButton>button { width: 100%; border-radius: 10px; height: 3.5em; font-weight: bold; font-size: 1.1em; }
    h1, h2, h3 { color: #1B4F72; }
    .stTextInput>div>div>input { font-size: 1.2em; }
    </style>
    """, unsafe_allow_html=True)

# 2. AIの初期設定（診断＆自動選択機能）
if 'target_model' not in st.session_state:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        
        # 利用可能な全モデルを取得してリスト化
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        st.session_state.all_available = available_models
        
        # 優先順位をつけてモデルを探す
        # 2026年の標準的なモデル名を網羅
        priority_list = [
            'models/gemini-3-flash',
            'models/gemini-3.0-flash',
            'models/gemini-2.0-flash',
            'models/gemini-1.5-flash-latest'
        ]
        
        selected = None
        for model_name in priority_list:
            if model_name in available_models:
                selected = model_name
                break
        
        # もしリストにない場合は、'flash'と名のつく最新のものを自動選択
        if not selected:
            flash_models = [m for m in available_models if 'flash' in m]
            selected = flash_models[0] if flash_models else available_models[0]
            
        st.session_state.target_model = selected
        st.session_state.ai_configured = True
    except Exception as e:
        st.error(f"AI設定中にエラーが発生しました: {e}")

# 3. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except Exception as e:
        st.error(f"CSVエラー: {e}")
        st.stop()

# --- サイドバー：診断ツール ---
st.sidebar.title("🛠️ システム診断")
st.sidebar.info(f"**現在使用中のAI:**\n`{st.session_state.get('target_model')}`")

with st.sidebar.expander("利用可能なモデル一覧"):
    for m in st.session_state.get('all_available', []):
        st.write(f"- `{m}`")

if st.sidebar.button("AIを再起動・モデル更新"):
    st.session_state.clear()
    st.rerun()

st.sidebar.markdown("---")
kous = sorted(list(set([q['kou'] for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("学習する講を選択", kous, default=[kous[0]] if kous else [])
order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

if st.sidebar.button("この設定で開始/リセット"):
    selected_data = [q for q in st.session_state.all_questions if q['kou'] in selected_kous]
    if order_type == "ランダム":
        random.shuffle(selected_data)
    st.session_state.current_list = selected_data
    st.session_state.current_idx = 0
    st.session_state.show_feedback = False
    st.session_state.ocr_text = ""
    st.rerun()

# --- メイン画面 ---
if 'current_list' not in st.session_state:
    st.info("左のサイドバーから講を選んで「開始」ボタンを押してください。")
    st.stop()

st.title("基礎S_英語表現T_重要文例Lab")

q = st.session_state.current_list[st.session_state.current_idx]
st.subheader(f"問 {q['no']}: {q['japanese']}")
st.caption(f"（{q['kou']} - {st.session_state.current_idx + 1} / {len(st.session_state.current_list)} 問目）")

# --- OCR機能 ---
with st.expander("📷 写真から解答を入力"):
    target = st.file_uploader("写真をアップ", type=['png', 'jpg', 'jpeg'], key="ocr_up")
    cam = st.camera_input("カメラで撮影", key="ocr_cam")
    input_data = cam if cam else target
    
    if input_data and st.button("AIで文字起こしを実行"):
        with st.spinner("AIが画像から英文を読み取っています..."):
            try:
                img = Image.open(input_data)
                model = genai.GenerativeModel(st.session_state.target_model)
                res = model.generate_content(["画像内の英文のみを抽出してください。解説不要。", img])
                st.session_state.ocr_text = res.text.strip()
                st.success("成功！解答欄に反映しました。")
            except Exception as e:
                st.error(f"OCR読み取りエラー: {e}")

# 解答入力
user_ans = st.text_input("あなたの答え:", value=st.session_state.get('ocr_text', ""), key=f"input_{st.session_state.current_idx}")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("採点"):
        try:
            model = genai.GenerativeModel(st.session_state.target_model)
            prompt = f"英語教師として回答『{user_ans}』を正解例『{q['english']}』と比較し、日本語で丁寧に解説してください。"
            res = model.generate_content(prompt)
            st.session_state.feedback_text = res.text
            st.session_state.show_feedback = True
            
            # バルーン判定
            user_clean = "".join(e for e in user_ans if e.isalnum()).lower()
            correct_clean = "".join(e for e in q['english'] if e.isalnum()).lower()
            if user_clean == correct_clean:
                st.balloons()
        except Exception as e:
            st.error(f"採点エラー: {e}")

with col2:
    if st.button("正解と音声"):
        st.session_state.show_feedback = True
        st.session_state.feedback_text = "正解例を確認して練習しましょう。"

with col3:
    if st.button("次へ"):
        if st.session_state.current_idx < len(st.session_state.current_list) - 1:
            st.session_state.current_idx += 1
            st.session_state.show_feedback = False
            st.session_state.ocr_text = ""
            st.rerun()
        else:
            st.success("全問終了！お疲れ様でした！")

if st.session_state.show_feedback:
    st.info(st.session_state.feedback_text)
    st.write(f"**【正解例】** {q['english']}")
    tts = gTTS(q['english'], lang='en')
    fp = io.BytesIO()
    tts.write_to_fp(fp)
    st.audio(fp)
