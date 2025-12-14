from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openpyxl
from docx import Document
import os
import openai
import base64

app = Flask(__name__)
CORS(app)

openai.api_key = "YOUR_API_KEY_HERE"


# 1) قراءة ملف الأسئلة والأجوبة
DOCX_PATH = "kb.docx"

def load_docx_text():
    if not os.path.exists(DOCX_PATH):
        return {}

    doc = Document(DOCX_PATH)
    qa = {}
    last_q = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if text.startswith("Q:") or text.startswith("س:"):
            last_q = text[2:].strip()
            qa[last_q] = ""
        elif text.startswith("A:") or text.startswith("ج:"):
            if last_q:
                qa[last_q] = text[2:].strip()

    return qa

knowledge_base = load_docx_text()

def best_match(question):
    q = question.strip().lower()
    for key in knowledge_base:
        if q in key.lower() or key.lower() in q:
            return knowledge_base[key]
    return "لم أجد إجابة مناسبة في ملف المؤتمر."


# 2) الترجمة
def translate_to_english(text):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Translate Arabic to formal English."},
                {"role": "user", "content": text}
            ]
        )
        return response["choices"][0]["message"]["content"].strip()
    except:
        return "No English translation available."


# 3) توليد الصوت العربي
def generate_arabic_voice(text):
    try:
        response = openai.Audio.create(
            model="gpt-4o-mini-tts",
            voice="omar",
            input=f"اقرأ باللهجة الأردنية: {text}",
            format="wav"
        )
        audio_bytes = response["audio"]
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print("TTS ERROR:", e)
        return None


# 4) API — سؤال الأفاتار
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question_ar = data.get("question", "")

    answer_ar = best_match(question_ar)
    question_en = translate_to_english(question_ar)
    answer_en = translate_to_english(answer_ar)

    voice_b64 = generate_arabic_voice(answer_ar)

    return jsonify({
        "answer_ar": answer_ar,
        "answer_en": answer_en,
        "question_en": question_en,
        "voice": voice_b64
    })


# 5) صفحة الأفاتار — الحل المهم
@app.route("/avatar")
def avatar_page():
    return send_from_directory(".", "avatar.html")


# 6) الصفحة الرئيسية
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


# 7) تشغيل السيرفر
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
