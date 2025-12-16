from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openai
from docx import Document
import base64
import os

app = Flask(__name__)
CORS(app)

# ------------------------------------------------
# 1) ضع مفتاح OpenAI هنا فقط
# ------------------------------------------------
openai.api_key = "YOUR_OPENAI_KEY_HERE"


# ------------------------------------------------
# 2) قراءة ملف Word واستخراج أسئلة وأجوبة Q/A
# ------------------------------------------------

DOCX_PATH = "kb.docx"

def load_docx_text():
    if not os.path.exists(DOCX_PATH):
        print("⚠️ ملف kb.docx غير موجود!")
        return {}

    doc = Document(DOCX_PATH)
    qa = {}
    last_q = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        # سؤال بالعربية أو الإنجليزية
        if text.startswith("Q:") or text.startswith("س:"):
            last_q = text[2:].strip()
            qa[last_q] = ""

        # جواب بالعربية أو الإنجليزية
        elif text.startswith("A:") or text.startswith("ج:"):
            if last_q:
                qa[last_q] = text[2:].strip()

    return qa


knowledge_base = load_docx_text()


# ------------------------------------------------
# 3) إيجاد أفضل جواب مطابق للسؤال
# ------------------------------------------------

def best_match(question):
    q = question.lower().strip()

    for key in knowledge_base:
        if q in key.lower() or key.lower() in q:
            return knowledge_base[key]

    return "لم أجد إجابة مناسبة في ملف المؤتمر."


# ------------------------------------------------
# 4) ترجمة احترافية AR → EN
# ------------------------------------------------

def translate_to_english(text):
    try:
        completion = openai.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Translate Arabic to formal English."},
                {"role": "user", "content": text}
            ]
        )
        return completion.choices[0].message.content
    except:
        return "No translation available."


# ------------------------------------------------
# 5) توليد صوت عربي أردني TTS
# ------------------------------------------------

def generate_voice(text):
    try:
        audio = openai.audio.speech.create(
            model="gpt-4o-mini-tts",
            voice="omar",
            input=f"اقرأ باللهجة الأردنية وبنبرة أكاديمية: {text}",
        )
        audio_bytes = audio.read()
        return base64.b64encode(audio_bytes).decode("utf-8")
    except Exception as e:
        print("VOICE ERROR:", e)
        return None


# ------------------------------------------------
# 6) تحويل الكلام إلى نص STT
# ------------------------------------------------

@app.route("/stt", methods=["POST"])
def stt():
    if "audio" not in request.files:
        return jsonify({"error": "no audio received"})

    file = request.files["audio"]

    try:
        transcript = openai.audio.transcriptions.create(
            model="gpt-4o-mini-transcribe",
            file=file
        )
        text = transcript.text
    except Exception as e:
        print("STT ERROR:", e)
        text = ""

    return jsonify({"text": text})


# ------------------------------------------------
# 7) API جواب الأفاتار
# ------------------------------------------------

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question_ar = data.get("question", "")

    # الجواب من ملف Word فقط (كما طلبت)
    answer_ar = best_match(question_ar)

    # الترجمة الإنجليزية
    question_en = translate_to_english(question_ar)
    answer_en = translate_to_english(answer_ar)

    # الصوت باللهجة الأردنية
    voice_b64 = generate_voice(answer_ar)

    return jsonify({
        "question_en": question_en,
        "answer_ar": answer_ar,
        "answer_en": answer_en,
        "voice": voice_b64
    })


# ------------------------------------------------
# 8) الصفحة الرئيسية والملفات الثابتة
# ------------------------------------------------

@app.route("/")
def home():
    return send_from_directory(".", "index.html")

@app.route("/avatar")
def avatar():
    return send_from_directory(".", "avatar.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)


# ------------------------------------------------
# 9) تشغيل السيرفر
# ------------------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
