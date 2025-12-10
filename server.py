from flask import Flask, request, jsonify, send_from_directory
from docx import Document
import difflib
import os
import pandas as pd

app = Flask(__name__)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# مسارات الملفات
DOCX_PATH = os.path.join(BASE_DIR, "kb.docx")         # ملف الوورد
EXCEL_PATH = os.path.join(BASE_DIR, "attendees.xlsx") # ملف الحضور

# تحميل محتوى الوورد (عربي + إنجليزي في أزواج)
def load_docx_pairs():
    doc = Document(DOCX_PATH)
    paras = [p.text.strip() for p in doc.paragraphs if p.text.strip()]
    arabic_list = []
    english_list = []

    # نفترض: فقرة عربية ثم التي بعدها إنجليزية
    i = 0
    while i < len(paras):
        ar = paras[i]
        en = ""
        if i + 1 < len(paras):
            en = paras[i + 1]
        arabic_list.append(ar)
        english_list.append(en)
        i += 2

    return arabic_list, english_list

arabic_paras, english_paras = load_docx_pairs()


def get_answer_from_docx(user_question: str):
    """
    نبحث عن أقرب فقرة عربية للسؤال، ونعيد العربية + الإنجليزية المقابلة.
    """
    if not arabic_paras:
        return "لا توجد بيانات في ملف المؤتمر.", ""

    match = difflib.get_close_matches(user_question, arabic_paras, n=1, cutoff=0.2)
    if match:
        idx = arabic_paras.index(match[0])
        ar = arabic_paras[idx]
        en = english_paras[idx] if idx < len(english_paras) else ""
        return ar, en
    else:
        return "عذراً، لا أجد معلومة مناسبة لهذا السؤال في ملف المؤتمر.", ""


@app.route("/")
def index():
    return send_from_directory(BASE_DIR, "index.html")


@app.route("/ask", methods=["POST"])
def ask():
    """
    نقطة الأفاتار: تستقبل سؤال وترجع إجابة عربية + ترجمة إنجليزية.
    """
    data = request.get_json(force=True)
    user_question = data.get("question", "").strip()
    if not user_question:
        return jsonify({"answer_ar": "الرجاء كتابة سؤال.", "answer_en": ""})
    answer_ar, answer_en = get_answer_from_docx(user_question)
    return jsonify({"answer_ar": answer_ar, "answer_en": answer_en})


@app.route("/register", methods=["POST"])
def register():
    """
    تسجيل الحضور: الاسم + الجامعة + الإيميل → إلى ملف attendees.xlsx
    """
    data = request.get_json(force=True)
    name = data.get("name", "").strip()
    university = data.get("university", "").strip()
    email = data.get("email", "").strip()

    if not name or not university or not email:
        return jsonify({"ok": False, "message": "الرجاء تعبئة جميع الحقول."})

    row = {"الاسم": name, "الجامعة": university, "الإيميل": email}

    # إذا الملف موجود: نقرأه ونضيف الصف، إذا لا: ننشئ ملف جديد
    if os.path.exists(EXCEL_PATH):
        df = pd.read_excel(EXCEL_PATH)
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    else:
        df = pd.DataFrame([row])

    df.to_excel(EXCEL_PATH, index=False)

    return jsonify({"ok": True, "message": "تم تسجيل حضورك بنجاح. شكراً لك!"})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
