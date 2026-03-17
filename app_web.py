import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io
import random
from PIL import Image
from streamlit_cropper import st_cropper
import re

# 1. ページ設定
st.set_page_config(page_title="基礎シリーズ_英語②_T_重要文例", layout="centered")

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
    .feedback-container { background-color: #fff9f0; padding: 20px; border-radius: 15px; border-left: 8px solid #f39c12; margin-top: 15px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ_英語②_T_重要文例</h1>", unsafe_allow_html=True)

# 2. セッション状態の初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text']:
    if key not in st.session_state:
        st.session_state[key] = False if 'finished' in key or 'show' in key else (0 if 'idx' in key or 'score' in key else None)

# 3. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except:
        st.error("questions.csvが見つかりません。")
        st.stop()

# --- サイドバー ---
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

# --- メイン画面 ---
if st.session_state.current_list is None:
    st.info("👈 左側のメニューから講を選んでスタートしてください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.markdown(f"<div style='text-align:center;'><h2>最終スコア</h2><p style='font-size:3em;color:#e67e22;font-weight:bold;'>{st.session_state.score} / {len(st.session_state.current_list)}</p></div>", unsafe_allow_html=True)
    if st.button("最初に戻る"):
        st.session_state.clear()
        st.rerun()
    st.stop()

q = st.session_state.current_list[st.session_state.current_idx]
q_text = q.get('japanese', q.get('question', ''))
ans_text = q.get('english', q.get('answer', ''))

st.markdown(f"<p style='color:#784212; margin-bottom:5px;'>第{q.get('no', st.session_state.current_idx+1)}問 ({st.session_state.current_idx+1}/{len(st.session_state.current_list)})</p><h3 style='color:#784212; margin-top:0;'>{q_text}</h3>", unsafe_allow_html=True)

# --- タブ入力 ---
tab1, tab2, tab3 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声"])

cropped_image = None
with tab1:
    st.write("👇 解答を撮影してください。")
    cam_file = st.camera_input("カメラ", key=f"c_{st.session_state.current_idx}")
    img_file = st.file_uploader("または画像を選択", type=['png', 'jpg', 'jpeg'], key=f"u_{st.session_state.current_idx}")
    raw_img = cam_file if cam_file else img_file
    if raw_img:
        try:
            # st_cropperで画像を処理
            cropped_image = st_cropper(Image.open(raw_img), realtime_update=True, box_color='#f39c12', aspect_ratio=None)
            st.image(cropped_image, caption="この画像を採点します")
        except:
            st.info("画像を表示中...")

with tab2:
    user_typed_text = st.text_input("英文をタイピング", key=f"t_{st.session_state.current_idx}")

with tab3:
    audio_data = st.audio_input("声に出して解答", key=f"a_{st.session_state.current_idx}")

# --- 採点ロジック ---
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 採点する"):
        if not (user_typed_text or audio_data or cropped_image):
            st.warning("⚠️ 解答を入力（入力・録音・撮影）してください。")
        else:
            with st.spinner("AI先生が確認中..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    # 404エラー回避：models/ を外して直接指定
                    model = genai.GenerativeModel('gemini-1.5-pro')
                    
                    prompt = f"""あなたは情熱的な英語講師です。日本文『{q_text}』に対する生徒の解答を添削してください。
                    模範解答：{ans_text}
                    
                    【ルール】
                    - 文法的に正しく意味が通じれば別解も正解(Perfect!)とする。
                    - 不合格という言葉は絶対に使わないこと。
                    - 記号 ** は一切使わない。
                    - 英文をカギカッコ「」で囲まない。
                    - 厳格だが最後は前向きに励ますこと。
                    - 正解なら『正解です』と必ず含める。
                    """

                    # 入力形式の判定と送信
                    if cropped_image:
                        # 写真がある場合（マルチモーダル）
                        response = model.generate_content([prompt, cropped_image])
                    elif audio_data:
                        # 音声がある場合
                        response = model.generate_content([prompt, {"mime_type": "audio/wav", "data": audio_data.read()}])
                    else:
                        # テキストのみ
                        response = model.generate_content(f"{prompt}\n生徒解答：{user_typed_text}")
                    
                    # 記号のクリーニング
                    clean_text = re.sub(r'[\*「」『』]', '', response.text)
                    st.session_state.feedback_text = clean_text
                    st.session_state.show_feedback = True
                    if "正解です" in clean_text or "Perfect" in clean_text:
                        st.session_state.score += 1
                except Exception as e:
                    st.error(f"AIエラー: {e}")

with col2:
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list):
            st.session_state.finished = True
        st.session_state.show_feedback = False
        st.rerun()

if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<br><br><b>模範解答：{ans_text}</b></div>", unsafe_allow_html=True)
    tts = gTTS(ans_text, lang='en')
    af = io.BytesIO()
    tts.write_to_fp(af)
    st.audio(af, autoplay=True)
