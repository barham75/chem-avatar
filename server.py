from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
import os
from docx import Document
import base64

app = Flask(__name__)
CORS(app)

openai.api_key = os.getenv("OPENAI_API_KEY")


# ---------------------------------------
# تحميل ملف المؤتمر
# ---------------------------------------
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


# ---------------------------------------
# الترجمة
# ---------------------------------------
def translate(text):
    try:
        res = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Translate to English"},
                {"role": "user", "content": text}
            ]
        )
        return res["choices"][0]["message"]["content"]
    except:
        return "Translation error."


# ---------------------------------------
# الصوت (TTS)
# ---------------------------------------
def tts_ar(text):
    try:
        response = openai.Audio.create(
            model="gpt-4o-mini-tts",
            voice="omar",
            input=text
        )
        audio_bytes = response["audio"]
        return base64.b64encode(audio_bytes).decode()
    except Exception as e:
        print("TTS ERROR:", e)
        return None


# ---------------------------------------
# API: سؤال نصي
# ---------------------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    q_ar = data.get("question", "")

    answer_ar = best_match(q_ar)
    q_en = translate(q_ar)
    a_en = translate(answer_ar)

    audio_b64 = tts_ar(answer_ar)

    return jsonify({
        "question_en": q_en,
        "answer_ar": answer_ar,
        "answer_en": a_en,
        "voice": audio_b64
    })


# ---------------------------------------
# API: تحويل صوت إلى نص
# ---------------------------------------
@app.route("/stt", methods=["POST"])
def stt():
    audio = request.files["audio"]

    res = openai.Audio.transcribe(
        model="gpt-4o-mini-tts",
        file=audio
    )

    return jsonify({"text": res["text"]})


# ---------------------------------------
# رفع الملفات
# ---------------------------------------
@app.route("/")
def index():
    return send_from_directory(".", "avatar.html")


@app.route("/<path:path>")
def files(path):
    return send_from_directory(".", path)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
