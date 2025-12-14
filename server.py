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
    question = question.strip().lower()
    for q in knowledge_base:
        if question in q.lower() or q.lower() in question:
            return knowledge_base[q]
    return "لم أجد إجابة مناسبة في ملف المؤتمر."

# ----------------------------------------
# 2) صفحة HTML
# ----------------------------------------

@app.route("/")
def index():
    return send_from_directory(".", "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(".", path)

# ----------------------------------------
# 3) API تسجيل الحضور
# ----------------------------------------

EXCEL_FILE = "attendees.xlsx"

def init_excel():
    if not os.path.exists(EXCEL_FILE):
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.append(["الاسم", "الجامعة", "البريد الإلكتروني"])
        wb.save(EXCEL_FILE)

init_excel()

@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    name = data.get("name", "")
    university = data.get("university", "")
    email = data.get("email", "")

    wb = openpyxl.load_workbook(EXCEL_FILE)
    ws = wb.active
    ws.append([name, university, email])
    wb.save(EXCEL_FILE)

    return jsonify({"ok": True})

# ----------------------------------------
# 4) API سؤال الأفاتار
# ----------------------------------------

@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()
    question = data.get("question", "")

    answer_ar = best_match(question)

    return jsonify({
        "answer_ar": answer_ar,
    })

# ----------------------------------------
# تشغيل السيرفر على Render
# ----------------------------------------

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
