import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io
import random
import requests
from PIL import Image
from streamlit_cropper import st_cropper

# --- ページ設定 ---
st.set_page_config(page_title="基礎シリーズ_英語②_T_重要文例", layout="centered")

# --- タイトル ---
st.title("基礎シリーズ_英語②_T_重要文例")

# --- セッション状態の初期化 ---
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "current_list" not in st.session_state:
    st.session_state.current_list = None
if "finished" not in st.session_state:
    st.session_state.finished = False
if "score" not in st.session_state:
    st.session_state.score = 0

# --- サイドバー ---
try:
    df = pd.read_csv("questions.csv")
    lectures = sorted(df["lecture"].unique())
    selected_lecture = st.sidebar.selectbox("講を選択", lectures)
    
    # ランダム選択の追加
    order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

    if st.sidebar.button("学習スタート"):
        filtered_df = df[df["lecture"] == selected_lecture].to_dict('records')
        if order_type == "ランダム":
            random.shuffle(filtered_df)
        st.session_state.current_list = filtered_df
        st.session_state.current_idx = 0
        st.session_state.score = 0
        st.session_state.finished = False
        st.rerun()
except:
    st.sidebar.error("questions.csvが読み込めません")

# --- メイン画面 ---
if st.session_state.current_list is None:
    st.info("左側のメニューから「講」を選んで「学習スタート」を押してください。")
    st.stop()

if st.session_state.finished:
    st.markdown(f"<div style='text-align:center;'><h2>最終スコア</h2><p style='font-size:3em;color:#e67e22;font-weight:bold;'>{st.session_state.score} / {len(st.session_state.current_list)}</p></div>", unsafe_allow_html=True)
    if st.button("もう一度挑戦"):
        st.session_state.finished, st.session_state.current_idx, st.session_state.current_list = False, 0, None
        st.rerun()
    st.stop()

# データの取得
q = st.session_state.current_list[st.session_state.current_idx]
ans = q.get('english', q.get('answer', ''))

st.markdown(f"<p style='color:#784212; margin-bottom:5px;'>第{q['no']}問 ({st.session_state.current_idx + 1}/{len(st.session_state.current_list)})</p><h3 style='color:#784212; margin-top:0;'>{q['japanese']}</h3>", unsafe_allow_html=True)

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
                requests.post(WEB_APP_URL, json={"name": sender, "message": msg})
                st.success("送信完了しました！")

# 採点とNextボタン
col1, col2 = st.columns(2)
with col1:
    if st.button("🌟 採点する"):
        if user_text:
            try:
                api_key = st.secrets["GEMINI_API_KEY"]
                genai.configure(api_key=api_key)
                
                # Pro版を使用
                model = genai.GenerativeModel('gemini-1.5-pro')
                
                # 厳格かつ前向きな添削ルール
                prompt = f"""
                あなたは情熱的で厳格な英語教師です。以下の日本文に対する生徒の英文を添削してください。
                
                【ルール】
                1. 文法的に正しく意味が通じれば、模範解答と異なっても別解として正解(Perfect!)とすること。
                2. 「不合格」という言葉は絶対に使わないこと。
                3. 厳格に間違いを指摘しつつも、最後は生徒が次も頑張りたくなるような前向きで励ます言葉で締めること。
                4. 回答の中に**のような記号を入れない。
                5. 英文に「」をつけない。
                
                日本文: {q['japanese']}
                模範解答: {ans} 
                生徒の解答: {user_text}
                """
                
                response = model.generate_content(prompt)
                st.write("---")
                st.write(response.text)
                st.session_state.score += 1
                
                tts = gTTS(text=ans, lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)
            except Exception as e:
                st.error("通信エラーが発生しました。APIキーの設定を確認してください。")
        else:
            st.warning("回答を入力してください。")

with col2:
    if st.button("Next (次へ) ➡️"):
        if st.session_state.current_idx + 1 < len(st.session_state.current_list):
            st.session_state.current_idx += 1
            st.rerun()
        else:
            st.session_state.finished = True
            st.rerun()
