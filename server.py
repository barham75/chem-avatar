from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from openai import OpenAI
import openpyxl
from docx import Document
import base64
import os

app = Flask(__name__)
CORS(app)

# ------------------------------------------------
# 1) ضع مفتاح OpenAI هنا
# ------------------------------------------------
client = OpenAI(api_key="YOUR_API_KEY_HERE")


# ------------------------------------------------
# 2) قراءة ملف Word واستخراج Q/A
# ------------------------------------------------
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


# ------------------------------------------------
# 3) ترجمة باستخدام GPT-4o
# ------------------------------------------------
def translate_to_english(text):
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Translate to academic English."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print("Translation error:", e)
        return "Translation unavailable."


# ------------------------------------------------
# 4) توليد صوت عربي أردني (TTS)
# ------------------------------------------------
def generate_arabic_voice(text):
    try:
        response = client.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="omar",
            input=f"اقرأ باللهجة الأردنية، أسلوب محاضر جامعي: {text}"
        )

        audio_bytes = response.read()
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")

        return audio_b64

    except Exception as e:
        print("TTS ERROR:", e)
        return None


# ------------------------------------------------
# 5) تفريغ الكلام من الميكروفون (STT)
# ------------------------------------------------
@app.route("/stt", methods=["POST"])
def stt():
    try:
        audio_file = request.files["audio"]
        response = client.audio.transcriptions.create(
            model="gpt-4o-mini-tts",
            file=audio_file
        )
        text = response.text
        return jsonify({"text": text})
    except Exception as e:
        print("STT ERROR:", e)
        return jsonify({"text": ""})


# ------------------------------------------------
# 6) API سؤال الأفاتار
# ------------------------------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question_ar = data.get("question", "")

    answer_ar = best_match(question_ar)
    answer_en = translate_to_english(answer_ar)
    question_en = translate_to_english(question_ar)
    voice_b64 = generate_arabic_voice(answer_ar)

    return jsonify({
        "question_en": question_en,
        "answer_ar": answer_ar,
        "answer_en": answer_en,
        "voice": voice_b64
    })


# ------------------------------------------------
# 7) ملفات الواجهة
# ------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


# ------------------------------------------------
# 8) تشغيل السيرفر
# ------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

