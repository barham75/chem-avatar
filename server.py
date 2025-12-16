from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import base64
import os
from docx import Document

app = Flask(__name__)
CORS(app)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# --------------------------
# تحميل ملف المؤتمر
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
# الترجمة (Chat Completions)
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
# توليد صوت عربي جديد API
# --------------------------
def tts_ar(text):
    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="omar",
        input=text,
        format="wav"
    )

    audio_bytes = response.read()
    return base64.b64encode(audio_bytes).decode()


# --------------------------
# تحويل كلام إلى نص STT الجديد
# --------------------------
@app.route("/stt", methods=["POST"])
def stt():
    audio_file = request.files["audio"]

    transcription = client.audio.transcriptions.create(
        model="gpt-4o-mini-transcribe",
        file=audio_file
    )

    return jsonify({"text": transcription.text})


# --------------------------
# إدخال سؤال نصي
# --------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    q_ar = data.get("question", "")

    answer_ar = best_match(q_ar)
    q_en = translate(q_ar)
    a_en = translate(answer_ar)
    voice_b64 = tts_ar(answer_ar)

    return jsonify({
        "question_en": q_en,
        "answer_ar": answer_ar,
        "answer_en": a_en,
        "voice": voice_b64
    })


# --------------------------
# استضافة الملفات
# --------------------------
@app.route("/")
def index():
    return send_from_directory(".", "avatar.html")


@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
