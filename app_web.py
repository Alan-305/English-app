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

# CSS: 先生こだわりのデザイン（タイトル1.2em / 明朝・Century / 行間圧縮）
st.markdown("""
<style>
    html, body, [class*="css"] { font-family: "MS PMincho", "Hiragino Mincho ProN", serif; }
    .stApp { background: linear-gradient(135deg, #ffffff 0%, #fff3e0 100%); }
    .main-title { color: #e67e22; text-align: center; font-weight: 700; font-size: 1.2em; padding: 8px 0; border-bottom: 3px solid #ffcc80; margin-bottom: 12px; }
    .q-label, .q-text { font-size: 1.2em; color: #784212; font-weight: bold; }
    
    .feedback-container { 
        background-color: #fff9f0; padding: 12px 18px; border-radius: 15px; 
        border-left: 8px solid #f39c12; margin-top: 10px; white-space: pre-line; 
        line-height: 1.25 !important; font-size: 1.05em; color: #4e342e; 
    }
    .feedback-container * { margin-top: 0px !important; margin-bottom: 2px !important; }
    
    /* 英文(bタグ)および「あなたの解答」はCenturyを指定 */
    .feedback-container b, .feedback-container strong { 
        font-family: "Century", "Times New Roman", serif; font-size: 1.05em; 
        color: #784212; background-color: #fff3e0; padding: 0 2px; 
    }
    .model-answer-text { 
        font-family: "Century", serif; font-size: 1.05em; font-weight: bold; 
        margin-top: 8px !important; color: #784212; border-top: 1px dashed #ffcc80; padding-top: 5px; 
    }
    div.stButton > button { background-color: #f39c12 !important; color: white !important; border-radius: 15px !important; height: 3.5em !important; font-weight: bold !important; width: 100%; }
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='main-title'>基礎シリーズ_英語②_T_重要文例</h1>", unsafe_allow_html=True)

# 2. 変数初期化
for key in ['finished', 'score', 'current_idx', 'show_feedback', 'current_list', 'feedback_text']:
    if key not in st.session_state:
        st.session_state[key] = False if 'finished' in key or 'show' in key else (0 if 'idx' in key or 'score' in key else None)

# 3. データ読み込み
if 'all_questions' not in st.session_state:
    try:
        df = pd.read_csv('questions.csv')
        df.columns = df.columns.str.strip().str.lower()
        st.session_state.all_questions = df.to_dict('records')
    except:
        st.error("questions.csvが見つかりません。")
        st.stop()

# 4. サイドバー：ランダム出題設定を再配置
st.sidebar.title("📚 Menu")
if st.sidebar.button("リセット"):
    st.session_state.clear(); st.rerun()

all_kous = sorted(list(set([str(q.get('kou', '1')) for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択", all_kous)
# 指示：ランダムの選択肢を復活
order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

if st.sidebar.button("学習スタート"):
    if selected_kous:
        data = [q for q in st.session_state.all_questions if str(q.get('kou', '1')) in selected_kous]
        # 指示：ランダムならシャッフルする
        if order_type == "ランダム":
            random.shuffle(data)
        st.session_state.current_list, st.session_state.current_idx, st.session_state.score = data, 0, 0
        st.session_state.finished, st.session_state.show_feedback = False, False; st.rerun()

if st.session_state.current_list is None:
    st.info("👈 左のメニューから講を選んでスタートしてください。"); st.stop()

if st.session_state.finished:
    st.balloons(); st.success(f"終了！ スコア: {st.session_state.score} / {len(st.session_state.current_list)}")
    if st.button("最初に戻る"): st.session_state.clear(); st.rerun()
    st.stop()

q = st.session_state.current_list[st.session_state.current_idx]
ans_text = q.get('english', q.get('answer', ''))

st.markdown(f"<div class='q-label'>第{st.session_state.current_idx + 1}問</div>", unsafe_allow_html=True)
st.markdown(f"<div class='q-text'>{q.get('japanese', '')}</div>", unsafe_allow_html=True)

# 5. ヒント
with st.expander("💡 ヒント"):
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        if st.button("文字で見る"): st.info(f"冒頭: {' '.join(ans_text.split()[:3])} ...")
    with h_col2:
        if st.button("音声を聞く"):
            tts_h = gTTS(ans_text, lang='en'); af_h = io.BytesIO(); tts_h.write_to_fp(af_h)
            st.audio(af_h, autoplay=False)

# 6. タブ
tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])
img_for_ai = None; input_type = "typed"
with tab1:
    raw = st.camera_input("撮影", key=f"c_{st.session_state.current_idx}")
    if raw: img_for_ai = st_cropper(Image.open(raw), realtime_update=True, box_color='#f39c12'); input_type = "image"
with tab2:
    typed_ans = st.text_input("回答を入力", key=f"t_{st.session_state.current_idx}")
with tab3:
    audio_data = st.audio_input("録音ボタンを押して解答", key=f"a_{st.session_state.current_idx}")
    if audio_data: input_type = "voice"

# 7. 報告タブ
with tab4:
    st.subheader("先生への報告")
    with st.form("report"):
        user_name = st.text_input("お名前")
        report_msg = st.text_area("メッセージ")
        if st.form_submit_button("送信"):
            if user_name and report_msg:
                with st.spinner("先生に送信中..."):
                    try:
                        gas_url = st.secrets.get("GAS_WEBAPP_URL")
                        payload = {"name": user_name, "message": report_msg, "question": q.get('japanese', '')}
                        response = requests.post(gas_url, json=payload, timeout=10)
                        if response.status_code == 200:
                            st.success("先生にメッセージを送信しました。")
                        else: st.error(f"送信失敗。URL設定を確認してください。")
                    except Exception as e: st.error(f"エラー: {e}")
            else: st.warning("名前とメッセージを入力してください。")

# 8. 採点
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 採点する"):
        if not (typed_ans or audio_data or img_for_ai): st.warning("⚠️ 録音中の場合は **⏹️** を押してから採点に進んでください。")
        else:
            with st.spinner("添削中..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model = genai.GenerativeModel(next((m for m in available if 'flash' in m), 'gemini-1.5-flash'))
                    
                    # 音声採点ルール（句読点不問） [cite: 2026-03-17]
                    voice_rule = "音声入力時は大文字小文字・句読点を一切不問とせよ。" if input_type == "voice" else ""
                    
                    prompt = f"""英語講師として添削。日本文『{q.get('japanese','')}』、模範解答『{ans_text}』。{voice_rule}
                    【構成】
                    1行目:評価
                    2行目:あなたの解答：<b>[生徒の解答をCentury体で表示]</b>
                    (※2行目の後は必ず1行空ける)
                    3行目以降:解説(和訳は「 」付)
                    不合格禁止。正解なら「正解です」を含める。"""
                    
                    inp = [prompt]
                    if img_for_ai: inp.append(img_for_ai)
                    elif audio_data: inp.append({"mime_type": "audio/wav", "data": audio_data.read()})
                    else: inp.append(f"生徒の解答：{typed_ans}")
                    res = model.generate_content(inp)
                    f_text = res.text.replace("**", "")
                    st.session_state.feedback_text, st.session_state.show_feedback = f_text, True
                    if any(w in f_text for w in ["正解", "Perfect"]): st.session_state.score += 1; st.balloons()
                except: st.error("接続エラー。")

with c2:
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list): st.session_state.finished = True
        st.session_state.show_feedback = False; st.rerun()

if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<div class='model-answer-text'>模範解答：{ans_text}</div></div>", unsafe_allow_html=True)
    tts_ans = gTTS(ans_text, lang='en'); af_ans = io.BytesIO(); tts_ans.write_to_fp(af_ans); st.audio(af_ans, autoplay=False)
