from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import openpyxl
from docx import Document
import os

app = Flask(__name__)
CORS(app)

# ----------------------------------------
# 1) قراءة ملف Word وتحويله إلى قاعدة معرفة
# ----------------------------------------

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

        # السؤال
        if text.startswith("Q:") or text.startswith("س:"):
            last_q = text[2:].strip()
            qa[last_q] = ""
        # الجواب
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

# ----------------------------------------
# 2) ترجمة بسيطة للإنجليزية
# ----------------------------------------

def translate_to_english(text):
    dictionary = {
        "هدف المؤتمر": "The goal of the conference",
        "تعزيز البحث العلمي": "To promote scientific research",
        "مكان المؤتمر": "The conference venue",
        "المتحدثون": "The keynote speakers",
        "محاور المؤتمر": "The conference topics",
        "جامعة": "University",
        "افتتاح": "Opening ceremony",
        "بحث": "Research",
        "كيمياء": "Chemistry",
    }
    for ar, en in dictionary.items():
        if ar in text:
            return en
    return "No English translation available."

# ----------------------------------------
# 3) مسارات الصفحات
# ----------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# ----------------------------------------
# 4) API سؤال الأفاتار
# ----------------------------------------

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question_ar = data.get("question", "")

    # الجواب العربي
    answer_ar = best_match(question_ar)

    # ترجمة السؤال والجواب
    question_en = translate_to_english(question_ar)
    answer_en = translate_to_english(answer_ar)

    return jsonify({
        "question_en": question_en,
        "answer_en": answer_en,
        "answer_ar": answer_ar
    })

# ----------------------------------------
# تشغيل السيرفر
# ----------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
