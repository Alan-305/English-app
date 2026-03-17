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

# CSS: フォント（明朝/Century）・サイズ・行間の詰めをすべて適用
st.markdown("""
<style>
    html, body, [class*="css"] {
        font-family: "MS PMincho", "Hiragino Mincho ProN", serif;
    }
    .stApp { background: linear-gradient(135deg, #ffffff 0%, #fff3e0 100%); }
    .main-title { 
        color: #e67e22; text-align: center; font-weight: 700; 
        font-size: 1.2em; padding: 8px 0; border-bottom: 3px solid #ffcc80; 
        font-family: 'serif'; margin-bottom: 12px;
    }
    .q-label, .q-text { font-size: 1.2em; color: #784212; font-weight: bold; }
    .q-label { margin-bottom: 2px; }
    .q-text { margin-top: 0px; margin-bottom: 15px; }

    .feedback-container { 
        background-color: #fff9f0; padding: 12px 18px; border-radius: 15px; 
        border-left: 8px solid #f39c12; margin-top: 10px; white-space: pre-line;
        line-height: 1.25 !important; font-size: 1.05em; color: #4e342e;
    }
    .feedback-container * { margin-top: 0px !important; margin-bottom: 2px !important; }
    .feedback-container b, .feedback-container strong { 
        font-family: "Century", "Times New Roman", serif; font-size: 1.05em;
        color: #784212; background-color: #fff3e0; padding: 0 2px;
    }
    .model-answer-text { 
        font-family: "Century", "Times New Roman", serif; font-size: 1.05em;
        font-weight: bold; margin-top: 8px !important; color: #784212; 
        border-top: 1px dashed #ffcc80; padding-top: 5px; 
    }
    div.stButton > button { 
        background-color: #f39c12 !important; color: white !important; 
        border-radius: 15px !important; height: 3.5em !important; 
        font-size: 1.1em !important; font-weight: bold !important; width: 100%;
    }
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
        st.error("questions.csvが見つかりません。")
        st.stop()

# 4. サイドバー
st.sidebar.title("📚 Menu")
if st.sidebar.button("リセット"):
    st.session_state.clear()
    st.rerun()

all_kous = sorted(list(set([str(q.get('kou', q.get('lecture', '1'))) for q in st.session_state.all_questions])))
selected_kous = st.sidebar.multiselect("講を選択", all_kous)
order_type = st.sidebar.radio("出題順", ["順番通り", "ランダム"])

if st.sidebar.button("学習スタート"):
    if selected_kous:
        data = [q for q in st.session_state.all_questions if str(q.get('kou', q.get('lecture', '1'))) in selected_kous]
        if order_type == "ランダム": random.shuffle(data)
        st.session_state.current_list, st.session_state.current_idx, st.session_state.score = data, 0, 0
        st.session_state.finished, st.session_state.show_feedback = False, False
        st.rerun()

if st.session_state.current_list is None:
    st.info("👈 講を選んでスタートしてください。")
    st.stop()

if st.session_state.finished:
    st.balloons()
    st.success(f"終了！ スコア: {st.session_state.score} / {len(st.session_state.current_list)}")
    if st.button("最初に戻る"):
        st.session_state.clear()
        st.rerun()
    st.stop()

q = st.session_state.current_list[st.session_state.current_idx]
ans_text = q.get('english', q.get('answer', ''))

st.markdown(f"<div class='q-label'>第{st.session_state.current_idx + 1}問 / {len(st.session_state.current_list)}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='q-text'>{q.get('japanese', '')}</div>", unsafe_allow_html=True)

# 6. ヒント機能（再生の競合を物理的に解決）
with st.expander("💡 ヒント"):
    h_col1, h_col2 = st.columns(2)
    with h_col1:
        if st.button("文字で見る"): st.info(f"冒頭: {' '.join(ans_text.split()[:3])} ...")
    with h_col2:
        # 指示通り「押したときだけ」再生し、他の操作では消える仕組み
        if st.button("音声を聞く"):
            tts_h = gTTS(ans_text, lang='en')
            af_h = io.BytesIO(); tts_h.write_to_fp(af_h)
            st.audio(af_h, autoplay=True)

# 7. タブ
tab1, tab2, tab3, tab4 = st.tabs(["📷 写真", "⌨️ 打ち込み", "🎤 音声", "💬 報告"])
img_for_ai = None
with tab1:
    raw = st.camera_input("撮影", key=f"c_{st.session_state.current_idx}")
    if raw: img_for_ai = st_cropper(Image.open(raw), realtime_update=True, box_color='#f39c12')
with tab2: typed_ans = st.text_input("回答を入力", key=f"t_{st.session_state.current_idx}")
with tab3: audio_data = st.audio_input("録音ボタンを押して解答", key=f"a_{st.session_state.current_idx}")
with tab4:
    with st.form("report"):
        st.text_input("名前"); st.text_area("メッセージ")
        if st.form_submit_button("送信"): st.success("送信しました。")

# 8. 操作ボタン
st.markdown("---")
c1, c2 = st.columns(2)
with c1:
    if st.button("🚀 採点する"):
        if not (typed_ans or audio_data or img_for_ai): st.warning("解答してください。")
        else:
            with st.spinner("添削中..."):
                try:
                    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
                    # 404対策：最新のモデル名を自動取得
                    available = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
                    model_name = next((m for m in available if 'flash' in m), 'gemini-1.5-flash')
                    model = genai.GenerativeModel(model_name)
                    
                    prompt = f"""英語講師として添削してください。
                    日本文：『{q.get('japanese','')}』
                    模範解答：『{ans_text}』
                    
                    【出力構成】
                    1行目：評価の言葉
                    2行目：あなたの解答：[ここに生徒の解答を表示]
                    3行目以降：解説

                    【ルール】
                    - 解説内の英文引用は <b> </b> タグで囲む。
                    - 「英文」という文字は絶対に出力しない。
                    - 文法的に正しければ別解も正解(Perfect!)とする。
                    - 「不合格」は禁止。前向きに励ます。
                    - 英文に「」はつけない。
                    - 正解なら「正解です」を含める。"""

                    input_data = [prompt]
                    if img_for_ai: input_data.append(img_for_ai)
                    elif audio_data: input_data.append({"mime_type": "audio/wav", "data": audio_data.read()})
                    else: input_data.append(f"生徒の解答：{typed_ans}")

                    res = model.generate_content(input_data)
                    f_text = re.sub(r'[\*「」『』]', '', res.text).replace("英文：", "").replace("英文", "")
                    st.session_state.feedback_text, st.session_state.show_feedback = f_text, True
                    if any(w in f_text for w in ["正解", "Perfect", "お見事"]):
                        st.session_state.score += 1; st.balloons()
                except Exception as e: st.error(f"エラー: {e}")

with c2:
    if st.button("次へ進む ➔"):
        st.session_state.current_idx += 1
        if st.session_state.current_idx >= len(st.session_state.current_list): st.session_state.finished = True
        st.session_state.show_feedback = False; st.rerun()

# 9. 結果表示
if st.session_state.show_feedback:
    st.markdown(f"<div class='feedback-container'>{st.session_state.feedback_text}<div class='model-answer-text'>模範解答：{ans_text}</div></div>", unsafe_allow_html=True)
    tts_ans = gTTS(ans_text, lang='en'); af_ans = io.BytesIO(); tts_ans.write_to_fp(af_ans)
    st.audio(af_ans, autoplay=False)
