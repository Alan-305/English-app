import os
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import streamlit as st
import google.generativeai as genai
import pandas as pd
import random
from gtts import gTTS
import io
from PIL import Image
from streamlit_cropper import st_cropper
import re

# 1. ページ設定
st.set_page_config(page_title="基礎シリーズ_英語②_T_重要文例", layout="centered")

# CSS: 英文サイズとレイアウトの調整
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
    .feedback-container { background-color: #fff9f0; padding: 20px; border-radius: 15px; border-left: 8px solid #f39c12; margin-top: 15px; white-space: pre-wrap; }
    
    /* 解説中の英文引用(bタグ)を模範解答と同じ1.4emにする */
    .feedback-container b, .feedback-container strong { 
        font-family: 'serif'; font-size: 1.4em; color: #784212; 
        background-color: #fff3e0; padding: 0 4px; font-weight: bold;
    }
    .model-answer-text { font-family: 'serif'; font-size: 1.4em; font-weight: bold; margin-top: 15px; color: #784212; border-top: 1px dashed #ffcc80; padding-top: 10px; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ_英語②_T_重要文例</h1>", unsafe_allow_html=True)

# 2. 変数の初期化
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
        st.error("questions.csvが読み込めません。")
        st.stop()

# 4. サイドバー
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
        if order_type == "ランダム":
            random.shuffle(data)
        st.session_state.current_list, st.session_state.current_idx, st.session_state.score = data, 0, 0
        st.session_state.finished, st.session_state.show_feedback = False, False
        st.rerun()

# 5. メイン画面制御
if st.session_state.current_list is None:
    st.info("👈 左のメニューから講を選んでスタートしてください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.success(f"全問終了！ スコア: {st.session_state.score} / {len(st.session_state.current_list)}")
    if st.button("最初に戻る"):
        st.session_state.clear()
        st.rerun()
    st.stop()

q = st.session_state.current_list[st.session_state.current_idx]
ans_text = q.get('english', q.get('answer', ''))

st.write(f"### 第{st.session_state.current_idx + 1}問 / {len(st.session_state.current_list)}")
st.write(f"## {q.get('japanese', '')}")

# 6. ヒント機能
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
            st.audio(af_h, autoplay=False) # ヒントは自動再生しない

# 7. タブ機能
tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])

img_for_ai = None
with tab1:
    raw_img = st.camera_input("撮影", key=f"c_{st.session_state.current_idx}")
    if raw_img:
        img_for_ai = st_cropper(Image.open(raw_img), realtime_update=True, box_color='#f39c12')

with tab2:
    typed_ans = st.text_input("回答を入力", key=f"t_{st.session_state.current_idx}")

with tab3:
    audio_data = st.audio_input("声に出して解答", key=f"a_{st.session_state.current_idx}")

with tab4:
    st.subheader("先生への報告")
    with st.form(key="report"):
        st.text_input("お名前")
        st.text_area("メッセージ")
        if st.form_submit_button("送信"): st.success("報告を受け付けました！")

# 8. 操作ボタン（採点 & 次へ）
st.markdown("---")
col1, col2 = st.columns(2)

with col1:
    if st.button("🚀 採点する"):
        if not (typed_ans or audio_data or img_for_ai):
            st.warning("⚠️ 解答を入力してください。")
        else:
            with st.spinner("添削中..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    # 404対策：直接シンプルな名前を指定
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"""経験豊富な英語講師として添削してください。
                    日本文：『{q.get('japanese','')}』
                    模範解答：『{ans_text}』
                    
                    【出力構成】
                    1行目：評価の言葉（例：正解です！、惜しい！など）
                    2行目：あなたの解答：[ここに生徒の解答を表示]
                    3行目以降：解説

                    【ルール】
                    - 解説の中の英文引用は必ず <b> </b> タグで囲むこと。
                    - 「英文」という文字は出力しない。
                    - 英文に「」や『』はつけない。
                    - 文法的に正しければ別解も正解(Perfect!)とする。
                    - 「不合格」という言葉、記号 ** は絶対に使用禁止。
                    - 前向きに励ますこと。正解なら「正解です」を含める。"""

                    input_content = [prompt]
                    if img_for_ai: input_content.append(img_for_ai)
                    elif audio_data: input_content.append({"mime_type": "audio/wav", "data": audio_data.read()})
                    else: input_content.append(f"生徒の解答：{typed_ans}")

                    response = model.generate_content(input_content)
                    f_text = response.text.replace("**", "").replace("「英文」", "").replace("英文：", "")
                    
                    st.session_state.feedback_text, st.session_state.show_feedback = f_text, True
                    if any(word in f_text for word in ["正解", "Perfect", "お見事"]):
                        st.session_state.score += 1
                        st.balloons()
                except Exception as e:
                    st.error(f"接続エラー: {e}")

with col2:
    # 指示2：解答前でも機能するNextボタン
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list):
            st.session_state.finished = True
        st.session_state.show_feedback = False
        st.rerun()

# 9. 結果表示
if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<div class='model-answer-text'>模範解答：{ans_text}</div></div>", unsafe_allow_html=True)
    # 指示1：autoplayをFalseにして勝手に読み上げないように修正
    tts = gTTS(ans_text, lang='en')
    af = io.BytesIO()
    tts.write_to_fp(af)
    st.audio(af, autoplay=False)
