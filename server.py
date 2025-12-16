from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import base64
import os
from docx import Document

app = Flask(__name__)
CORS(app)

# --------------------------
# 1) إعداد API KEY
# --------------------------
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --------------------------
# 2) تحميل ملف Q/A من Word
# --------------------------
def load_docx():
    qa = {}
    if not os.path.exists("kb.docx"):
        return qa

    doc = Document("kb.docx")
    question = None
    for p in doc.paragraphs:
        t = p.text.strip()
        if t.startswith("Q:") or t.startswith("س:"):
            question = t[2:].strip()
            qa[question] = ""
        elif t.startswith("A:") or t.startswith("ج:"):
            if question:
                qa[question] = t[2:].strip()

    return qa


KB = load_docx()


def best_match(q):
    q = q.lower().strip()
    for k in KB:
        if q in k.lower() or k.lower() in q:
            return KB[k]
    return "لم أجد إجابة مناسبة في ملف المؤتمر."


# --------------------------
# 3) الترجمة (Model: gpt-4o-mini)
# --------------------------
def translate(text):
    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Translate to English."},
            {"role": "user", "content": text}
        ]
    )
    return res.choices[0].message.content


# --------------------------
# 4) توليد صوت باللهجة الأردنية (TTS)
# --------------------------
def tts_ar(text):
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="omar",
        input=f"اقرأ باللهجة الأردنية وبأسلوب محاضر جامعي:\n{text}",
        format="wav"
    )
    audio_bytes = response.read()
    return base64.b64encode(audio_bytes).decode()


# --------------------------
# 5) تحويل كلام إلى نص (STT)
# --------------------------
@app.route("/stt", methods=["POST"])
def stt():
    audio_file = request.files["audio"]

    transcription = client.audio.transcriptions.create(
        model="gpt-4o-transcribe",
        file=audio_file
    )

    return jsonify({"text": transcription.text})


# --------------------------
# 6) استقبال سؤال نصي
# --------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    q_ar = data.get("question", "")

    # جواب عربي
    answer_ar = best_match(q_ar)

    # ترجمة السؤال والجواب
    q_en = translate(q_ar)
    a_en = translate(answer_ar)

    # صوت
    voice_b64 = tts_ar(answer_ar)

    return jsonify({
        "question_en": q_en,
        "answer_ar": answer_ar,
        "answer_en": a_en,
        "voice": voice_b64
    })


# --------------------------
# 7) عرض صفحة HTML
# --------------------------
@app.route("/")
def index():
    return send_from_directory(".", "avatar.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


# --------------------------
# 8) تشغيل الخادم
# --------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
