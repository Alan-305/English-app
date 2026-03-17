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
import requests
import re

# 1. ページ設定
st.set_page_config(page_title="基礎シリーズ_英語②_T_重要文例", layout="centered")

# --- CSS: ライトモード強制・ブランディング非表示・フォント指定 ---
st.markdown("""
<style>
    /* 1. ツールバー、メニュー、フッターを完全に隠す */
    [data-testid="stToolbar"] {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header {visibility: hidden !important;}
    [data-testid="stSidebar"] {display: none !important;} /* サイドバー自体を無効化 */

    /* 2. ライトモード強制固定 */
    .stApp { background: #ffffff !important; color: #000000 !important; }
    
    /* 3. フォント指定（日本語：明朝、英語：Century） */
    html, body, [class*="css"], .stMarkdown {
        font-family: "MS PMincho", "Hiragino Mincho ProN", serif !important;
        color: #000000 !important;
    }

    /* 4. タイトルとデザイン */
    .main-title { 
        color: #e67e22 !important; text-align: center; font-weight: 700; 
        font-size: 1.2em; padding: 10px 0; border-bottom: 3px solid #ffcc80; 
        margin-bottom: 20px; 
    }
    .setup-box {
        background-color: #fffaf0; padding: 20px; border-radius: 15px;
        border: 2px solid #ffcc80; margin-bottom: 20px;
    }
    .q-label { color: #784212 !important; font-weight: bold; font-size: 1.2em; }
    .q-text { color: #000000 !important; font-weight: bold; font-size: 1.2em; margin-bottom: 15px; }
    
    /* 5. 解説エリア */
    .feedback-container { 
        background-color: #fff9f0 !important; padding: 12px 18px; border-radius: 15px; 
        border-left: 8px solid #f39c12; margin-top: 10px; white-space: pre-line; 
        line-height: 1.3 !important; font-size: 1.05em; color: #4e342e !important; 
    }
    .feedback-container b, .feedback-container strong { 
        font-family: "Century", serif !important; color: #784212 !important; 
        background-color: #fff3e0 !important; padding: 0 2px; 
    }
    .model-answer-text { 
        font-family: "Century", serif !important; font-size: 1.05em; font-weight: bold; 
        margin-top: 8px !important; color: #784212 !important; 
        border-top: 1px dashed #ffcc80; padding-top: 5px; 
    }
    
    /* 6. ボタン */
    div.stButton > button { 
        background-color: #f39c12 !important; color: white !important; 
        border-radius: 15px !important; height: 3.5em !important; 
        font-weight: bold !important; width: 100%; 
    }

    /* 7. チャット */
    .chat-bubble { padding: 10px 15px; border-radius: 15px; margin-bottom: 10px; line-height: 1.4; font-size: 1.05em; }
    .user-bubble { background-color: #ffe0b2 !important; color: #784212 !important; border: 1px solid #ffcc80; }
    .ai-bubble { background-color: #ffffff !important; border: 1px solid #ffcc80; color: #4e342e !important; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ_英語②_T_重要文例</h1>", unsafe_allow_html=True)

# 2. 変数初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text', 'chat_history']:
    if key not in st.session_state:
        if key == 'chat_history': st.session_state[key] = []
        else: st.session_state[key] = False if 'finished' in key or 'show' in key else (0 if 'idx' in key or 'score' in key else None)

def get_best_model():
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        target = next((m for m in models if 'flash' in m), 'gemini-1.5-flash')
        return target
    except: return 'gemini-1.5-flash'

# 3. データの読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except: st.error("questions.csvが見つかりません。"); st.stop()

# --- 💡 修正ポイント：セットアップ画面（メインページ上部） ---
if st.session_state.current_list is None:
    st.markdown("<div class='setup-box'>", unsafe_allow_html=True)
    st.subheader("📚 学習設定")
    all_kous = sorted(list(set([str(q.get('kou', '1')) for q in st.session_state.all_questions])))
    selected_kous = st.multiselect("学習する講を選択してください", all_kous)
    order_type = st.radio("出題順を選択してください", ["順番通り", "ランダム"], horizontal=True)
    
    if st.button("🚀 学習スタート"):
        if selected_kous:
            data = [q for q in st.session_state.all_questions if str(q.get('kou', '1')) in selected_kous]
            if order_type == "ランダム": random.shuffle(data)
            st.session_state.current_list, st.session_state.current_idx, st.session_state.score = data, 0, 0
            st.session_state.finished, st.session_state.show_feedback, st.session_state.chat_history = False, False, []
            st.rerun()
        else:
            st.warning("講を1つ以上選択してください。")
    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# --- 4. 学習中の画面 ---
if st.session_state.finished:
    st.balloons(); st.success(f"終了！ スコア: {st.session_state.score} / {len(st.session_state.current_list)}")
    if st.button("設定画面に戻る"):
        st.session_state.current_list = None
        st.rerun()
    st.stop()

q = st.session_state.current_list[st.session_state.current_idx]
ans_text = q.get('english', q.get('answer', ''))

col_header_1, col_header_2 = st.columns([3, 1])
with col_header_1:
    st.markdown(f"<div class='q-label'>第{st.session_state.current_idx + 1}問 / {len(st.session_state.current_list)}</div>", unsafe_allow_html=True)
with col_header_2:
    if st.button("最初からやり直す", key="reset_btn"):
        st.session_state.current_list = None; st.rerun()

# 修正箇所: 88行目付近の f-string の開始クォーテーションを追加
st.markdown(f"<div class='q-text'>{q.get('japanese', '')}</div>", unsafe_allow_html=True)

# 5. ヒント
with st.expander("💡 ヒント"):
    h_c1, h_c2 = st.columns(2)
    with h_c1:
        if st.button("文字で見る"): st.info(f"冒頭: {' '.join(ans_text.split()[:3])} ...")
    with h_c2:
        if st.button("音声を聞く"):
            tts_h = gTTS(ans_text, lang='en'); af_h = io.BytesIO(); tts_h.write_to_fp(af_h); st.audio(af_h)

# 6. タブ
tab1, tab2, tab3, tab4, tab5 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告", "❓ 質問コーナー"])

img_for_ai = None; input_type = "typed"
with tab1:
    raw = st.camera_input("撮影", key=f"c_{st.session_state.current_idx}")
    if raw: img_for_ai = st_cropper(Image.open(raw), realtime_update=True, box_color='#f39c12'); input_type = "image"
with tab2: typed_ans = st.text_input("回答を入力", key=f"t_{st.session_state.current_idx}")
with tab3:
    audio_data = st.audio_input("録音ボタンを押して解答", key=f"a_{st.session_state.current_idx}")
    if audio_data: input_type = "voice"

with tab4:
    with st.form("report_form"):
        u_name = st.text_input("お名前"); r_msg = st.text_area("メッセージ")
        if st.form_submit_button("送信"):
            if u_name and r_msg:
                try:
                    res = requests.post(st.secrets["GAS_WEBAPP_URL"], json={"name": u_name, "message": r_msg, "question": q.get('japanese', '')}, timeout=10)
                    if res.status_code == 200: st.success("先生に送信しました。")
                except: st.error("送信失敗。")

with tab5:
    st.subheader("🤖 AI講師に質問")
    for chat in st.session_state.chat_history:
        r_label = "👤 生徒" if chat["role"] == "user" else "🤖 先生"
        r_class = "user-bubble" if chat["role"] == "user" else "ai-bubble"
        st.markdown(f"<div class='chat-bubble {r_class}'><b>{r_label}:</b><br>{chat['content']}</div>", unsafe_allow_html=True)
    with st.form("chat_form", clear_on_submit=True):
        user_msg = st.text_area("質問内容（リターンキーで改行できます）", height=100)
        if st.form_submit_button("⬆️ 質問を送信する") and user_msg:
            st.session_state.chat_history.append({"role": "user", "content": user_msg}); st.rerun()

if st.session_state.chat_history and st.session_state.chat_history[-1]["role"] == "user":
    with st.spinner("考え中..."):
        try:
            model = genai.GenerativeModel(get_best_model())
            inst = f"英語講師。問題『{q.get('japanese','')}』について解説。和訳は「」付。記号**禁止。"
            resp = model.generate_content([inst, st.session_state.chat_history[-1]["content"]])
            st.session_state.chat_history.append({"role": "ai", "content": resp.text.replace("**", "")}); st.rerun()
        except Exception as e: st.error(f"質問回答エラー: {str(e)}")

# 7. 採点
st.markdown("---")
if st.button("🚀 採点する"):
    if not (typed_ans or audio_data or img_for_ai): st.warning("⚠️ 録音中の場合は **⏹️** を押してから採点に進んでください。")
    else:
        with st.spinner("添削中..."):
            try:
                model = genai.GenerativeModel(get_best_model())
                v_rule = "音声入力時は大文字小文字・句読点を一切不問とし、語順が合っていれば正解とせよ。" if input_type == "voice" else ""
                prompt = f"""英語講師。日本文『{q.get('japanese','')}』、模範解答『{ans_text}』。{v_rule}
                【構成】1:評価、2:あなたの解答：<b>[生徒の解答をCentury]</b>、(空行)、3:解説(和訳「 」付)。不合格禁止。**禁止。"""
                inp = [prompt]
                if img_for_ai: inp.append(img_for_ai)
                elif audio_data: inp.append({"mime_type": "audio/wav", "data": audio_data.read()})
                else: inp.append(f"解答：{typed_ans}")
                res = model.generate_content(inp)
                f_text = res.text.replace("**", "")
                st.session_state.feedback_text, st.session_state.show_feedback = f_text, True
                if any(w in f_text for w in ["正解", "Perfect", "お見事"]): st.session_state.score += 1; st.balloons()
            except Exception as e: st.error(f"採点エラー: {str(e)}")

if st.button("次へ進む ➔"):
    st.session_state.current_idx += 1
    if st.session_state.current_idx >= len(st.session_state.current_list): st.session_state.finished = True
    st.session_state.show_feedback = False; st.session_state.chat_history = []; st.rerun()

if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<div class='model-answer-text'>模範解答：{ans_text}</div></div>", unsafe_allow_html=True)
    tts_ans = gTTS(ans_text, lang='en'); af_ans = io.BytesIO(); tts_ans.write_to_fp(af_ans); st.audio(af_ans)
