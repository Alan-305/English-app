import streamlit as st
import pandas as pd
import google.generativeai as genai
from gtts import gTTS
import io
import random
import requests
from PIL import Image
from streamlit_cropper import st_cropper

# --- ページ設定とデザイン ---
st.set_page_config(page_title="English Learning Builder", layout="centered")

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    .stButton>button {width: 100%; border-radius: 20px;}
    </style>
    """, unsafe_allow_html=True)

st.title("🍊 English Learning Builder")
st.subheader("3年後の完成を目指して：第110問への道")

# --- セッション状態の初期化 ---
if "current_idx" not in st.session_state:
    st.session_state.current_idx = 0
if "current_list" not in st.session_state:
    st.session_state.current_list = None
if "finished" not in st.session_state:
    st.session_state.finished = False
if "score" not in st.session_state:
    st.session_state.score = 0

# --- サイドバー：設定とスタート ---
st.sidebar.title("🛠 設定")

try:
    df = pd.read_csv("questions.csv")
    # CSVの列名が 'lecture' だと想定しています
    lectures = sorted(df["lecture"].unique())
    selected_lecture = st.sidebar.selectbox("講を選択", lectures)
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

except Exception as e:
    st.sidebar.error("questions.csvの読み込みに失敗しました。ファイルが存在するか確認してください。")
    st.stop()

# --- メイン画面 ---
if st.session_state.current_list is None:
    st.info("👈 左側のメニューから「講」を選んで「学習スタート」を押してください。")
    st.stop()

if st.session_state.finished:
    st.markdown(f"<div style='text-align:center;'><h2>最終スコア</h2><p style='font-size:3em;color:#e67e22;font-weight:bold;'>{st.session_state.score} / {len(st.session_state.current_list)}</p></div>", unsafe_allow_html=True)
    if st.button("もう一度挑戦"):
        st.session_state.finished, st.session_state.current_idx, st.session_state.current_list = False, 0, None
        st.rerun()
    st.stop()

# 現在の問題データを取得（列名 japanese または question に対応）
q = st.session_state.current_list[st.session_state.current_idx]
q_no = q.get('no', st.session_state.current_idx + 1)
q_text = q.get('japanese', q.get('question', '問題文エラー'))
ans_text = q.get('answer', '')

st.markdown(f"<p style='color:#784212; margin-bottom:5px;'>第{q_no}問 ({st.session_state.current_idx + 1}/{len(st.session_state.current_list)})</p><h3 style='color:#784212; margin-top:0;'>{q_text}</h3>", unsafe_allow_html=True)

# --- 入力タブ ---
tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])

user_answer = ""

with tab1:
    st.write("👇 カメラボタンを押して撮影、または下の「画像を選択」からアップしてください。")
    cam_file = st.camera_input("カメラ", key=f"c_{st.session_state.current_idx}")
    img_file = st.file_uploader("画像を選択", type=['png', 'jpg', 'jpeg'], key=f"u_{st.session_state.current_idx}")
    raw = cam_file if cam_file else img_file
    if raw:
        try:
            cropped_image = st_cropper(Image.open(raw), realtime_update=True, box_color='#f39c12', aspect_ratio=None)
            st.info("📝 画像を切り抜きました。採点するには、下の「打ち込み」タブに英文を入力してください。（画像自動読み取り機能は準備中です）")
        except:
            st.info("画像を表示中...")

with tab2:
    user_answer = st.text_input("回答をタイピング", key=f"t_{st.session_state.current_idx}")

with tab3:
    audio_file = st.audio_input("録音して解答", key=f"a_{st.session_state.current_idx}")
    if audio_file:
        st.info("🎤 録音完了。※音声自動認識は準備中です。現在は「打ち込み」タブから入力して採点してください。")

with tab4:
    st.subheader("松尾先生への報告")
    WEB_APP_URL = "https://script.google.com/macros/s/XXXXX/exec" # ← GASのURLに書き換えてください
    with st.form(key="support_form", clear_on_submit=True):
        sender = st.text_input("お名前")
        msg = st.text_area("メッセージ内容")
        if st.form_submit_button("送信"):
            if WEB_APP_URL.startswith("http"):
                try:
                    requests.post(WEB_APP_URL, json={"name": sender, "message": msg})
                    st.success("送信完了しました！")
                except:
                    st.error("送信に失敗しました。URLを確認してください。")

# --- 採点・Nextボタン ---
col1, col2 = st.columns(2)

with col1:
    if st.button("🌟 採点する"):
        if user_answer:
            try:
                # APIキーの読み込みとProモデルの指定
                api_key = st.secrets["GEMINI_API_KEY"]
                genai.configure(api_key=api_key)
                model = genai.GenerativeModel('gemini-1.5-pro') # Proモデルを使用
                
                # 松尾先生の指導方針を完全再現するプロンプト
                prompt = f"""
                あなたは情熱的で生徒想いの、予備校のベテラン英語教師です。以下の日本文に対する生徒の英文を添削してください。
                
                【厳守するルール】
                1. 文法的に正しく意味が通じれば、模範解答と異なっても別解として正解として扱うこと。
                2. 「不合格」という言葉は絶対に使わないこと。
                3. 厳格に間違いを指摘しつつも、最後は生徒が次も頑張りたくなるような前向きで励ます言葉で締めること。
                4. 回答の中にアスタリスクのような記号を絶対に入れないこと。
                5. 英文にカギカッコを絶対につけないこと。
                
                日本文: {q_text}
                模範解答: {ans_text}
                生徒の解答: {user_answer}
                """
                
                response = model.generate_content(prompt)
                st.write("---")
                st.write(response.text)
                st.session_state.score += 1 # 簡易的な加点処理
                
                # 音声合成（gTTS）で模範解答を再生
                tts = gTTS(text=ans_text, lang='en')
                fp = io.BytesIO()
                tts.write_to_fp(fp)
                st.audio(fp)
                
            except Exception as e:
                st.error("通信エラーが発生しました。APIキー（Secrets）の設定を確認してください。")
        else:
            st.warning("回答が入力されていません。「打ち込み」タブから英文を入力してください。")

with col2:
    if st.button("Next (次へ) ➡️"):
        if st.session_state.current_idx + 1 < len(st.session_state.current_list):
            st.session_state.current_idx += 1
            st.rerun()
        else:
            st.session_state.finished = True
            st.rerun()
