import argparse
import csv
from collections import OrderedDict
from datetime import datetime
from html import escape
import re

INPUT_CSV = "yamol_questions.csv"
OUTPUT_HTML = "yamol_book_print.html"


def prettify_question_text(text: str) -> str:
    """把題目內容做基本排版：選項換行、保留可讀性。"""
    t = (text or "").strip()

    # 題幹中若帶到原站 a 標籤，移除標籤保留內容
    t = re.sub(r"</?a\b[^>]*>", "", t, flags=re.IGNORECASE)

    # 在選項前加換行
    t = re.sub(r"\s*\((A|B|C|D)\)", r"<br><span class='opt'>(\1)</span>", t)

    # 題號後加空格更易讀
    t = re.sub(r"^(\d+)\.", r"\1. ", t)

    return t


def load_data(path: str):
    exams = OrderedDict()
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("exam_title") or "未命名試卷").strip()
            try:
                qno = int(row.get("question_no") or 0)
            except ValueError:
                qno = 0

            qtext = (row.get("question_text") or "").strip()
            qhtml = (row.get("question_html") or "").strip()
            exams.setdefault(title, []).append(
                {
                    "question_no": qno,
                    "question_text": qtext,
                "question_html": qhtml,
                "item_url": (row.get("item_url") or "").strip(),
                "answer": (row.get("answer") or "").strip(),
                "answer_source": (row.get("answer_source") or "").strip(),
                }
            )

    for title in exams:
        exams[title].sort(key=lambda x: x["question_no"])
    return exams


def build_html(exams, book_title: str):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total_exam = len(exams)
    total_q = sum(len(v) for v in exams.values())

    parts = []
    parts.append(
        """<!doctype html>
<html lang="zh-Hant">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <meta name="robots" content="noindex, nofollow, noarchive, nosnippet, noimageindex" />
  <meta name="googlebot" content="noindex, nofollow, noarchive, nosnippet, noimageindex" />
  <title>{escape(book_title)} 題庫列印版</title>
  <style>
    @page {
      size: A4;
      margin: 12mm 12mm 14mm 12mm;
    }

    :root {
      --text: #1b1f24;
      --muted: #5f6b7a;
      --line: #d9e0ea;
      --accent: #1f5faa;
      --accent-soft: #eaf2ff;
      --paper: #ffffff;
      --shadow: 0 8px 28px rgba(20, 41, 71, 0.08);
      --radius: 14px;
    }

    html, body {
      font-family: "Noto Sans TC", "Microsoft JhengHei", sans-serif;
      color: var(--text);
      line-height: 1.75;
      font-size: 11.2pt;
      margin: 0;
      padding: 0;
      background: #f2f5f9;
    }

    .container {
      max-width: 210mm;
      margin: 0 auto;
      padding: 9mm;
      box-sizing: border-box;
    }

    .toolbar {
      position: sticky;
      top: 0;
      background: rgba(255, 255, 255, 0.9);
      border: 1px solid var(--line);
      border-radius: 10px;
      backdrop-filter: blur(6px);
      padding: 8px 10px;
      margin-bottom: 10px;
      z-index: 10;
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
    }

    .btn {
      border: 1px solid #b8c8de;
      background: #fff;
      padding: 6px 12px;
      border-radius: 6px;
      cursor: pointer;
      font-size: 10pt;
      color: #24466f;
    }

    .btn.primary {
      background: linear-gradient(180deg, #2e7ad8 0%, #1f5faa 100%);
      border-color: #1f5faa;
      color: #fff;
    }

    .cover {
      min-height: 250mm;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      text-align: center;
      background: radial-gradient(circle at 30% 20%, #f4f8ff, #ffffff 60%);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      page-break-after: always;
    }

    .cover h1 {
      font-size: 26pt;
      margin: 0 0 6mm 0;
      color: var(--accent);
      letter-spacing: 1px;
    }

    .cover p {
      margin: 1mm 0;
      color: var(--muted);
    }

    .toc {
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 7mm;
      page-break-after: always;
    }

    .toc h2,
    .exam h2 {
      border-bottom: 2px solid var(--accent);
      padding-bottom: 2mm;
      margin: 0 0 4mm 0;
    }

    .toc ol {
      margin: 0;
      padding-left: 6mm;
      columns: 2;
      column-gap: 12mm;
    }

    .toc li {
      margin: 2mm 0;
      break-inside: avoid;
      color: #273243;
    }

    .exam {
      page-break-before: always;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 7mm;
    }

    .q {
      margin: 0 0 5mm 0;
      break-inside: avoid;
      page-break-inside: avoid;
      border: 1px solid #dce5f0;
      border-left: 4px solid #7da8df;
      border-radius: 10px;
      padding: 3.2mm 3.5mm;
      background: #fcfdff;
    }

    .q-no {
      font-weight: 800;
      color: #1e467c;
      margin-bottom: 1mm;
    }

    .answer-box {
      margin-top: 2.2mm;
      display: inline-block;
      background: #eaf5e8;
      border: 1px solid #c6dfc0;
      color: #24572b;
      padding: 1.1mm 2.2mm;
      border-radius: 8px;
      font-size: 10pt;
      font-weight: 700;
    }

    .answer-note {
      color: #5f6f84;
      font-size: 8.8pt;
      margin-top: 1mm;
    }

    .hide-answers .answer-box,
    .hide-answers .answer-note {
      display: none !important;
    }

    .q-text {
      margin-top: 0.5mm;
      white-space: normal;
    }

    .q-text img {
      display: block;
      max-width: 100%;
      height: auto;
      margin: 2.5mm 0;
      border: 1px solid #d7dfea;
      border-radius: 8px;
      break-inside: avoid;
      page-break-inside: avoid;
      box-shadow: 0 4px 12px rgba(20, 41, 71, 0.06);
    }

    .opt {
      display: inline-block;
      width: 6mm;
      font-weight: 700;
      color: #274e86;
    }

    .meta {
      color: var(--muted);
      font-size: 9.7pt;
      margin-bottom: 4mm;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      flex-wrap: wrap;
    }

    .source-link {
      font-size: 9pt;
      color: #6f7f93;
      margin-top: 1.5mm;
    }

    .source-link a {
      color: #2a64ad;
      text-decoration: none;
      border-bottom: 1px dotted #9bb7db;
    }

    .source-link a:hover {
      color: #1f4f8b;
    }

    .practice-lines {
      margin-top: 2.2mm;
      display: none;
      gap: 1.2mm;
      flex-direction: column;
    }

    .practice-lines .line {
      height: 0;
      border-bottom: 1px dashed #c7d3e3;
    }

    .show-lines .practice-lines {
      display: flex;
    }

    .compact .q {
      margin-bottom: 3mm;
      padding: 2.2mm 2.6mm;
    }

    .compact .q-text {
      line-height: 1.58;
    }

    .answers-summary {
      page-break-before: always;
      background: var(--paper);
      border: 1px solid var(--line);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 7mm;
    }

    .answers-summary h2 {
      border-bottom: 2px solid var(--accent);
      padding-bottom: 2mm;
      margin: 0 0 4mm 0;
    }

    .answers-summary h3 {
      margin: 5mm 0 2mm 0;
      color: #24466f;
      font-size: 12pt;
    }

    .answer-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(78px, 1fr));
      gap: 1.6mm;
      margin-bottom: 2mm;
    }

    .answer-chip {
      background: #f3f8ff;
      border: 1px solid #cfddf1;
      border-radius: 7px;
      padding: 1.2mm 1.4mm;
      font-size: 9.4pt;
      color: #24466f;
      white-space: nowrap;
      text-align: center;
    }

    @media print {
      .toolbar { display: none !important; }
      a { color: inherit; text-decoration: none; }
      .container { padding: 0; }
      body { background: #fff; }
      .cover,
      .toc,
      .exam,
      .q {
        box-shadow: none;
      }
      .cover,
      .toc,
      .exam {
        border-color: #cfd8e6;
      }

      /* 列印時採較緊湊版，減少留白 */
      .q {
        margin-bottom: 3mm;
        padding: 2.2mm 2.6mm;
      }

      .q-text {
        line-height: 1.58;
      }

      /* 列印版隱藏超長連結，保持版面乾淨 */
      .source-link {
        display: none !important;
      }

      * {
        -webkit-print-color-adjust: exact;
        print-color-adjust: exact;
      }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="toolbar">
      <button class="btn primary" onclick="window.print()">列印 / 另存 PDF</button>
      <button class="btn" id="toggle-answer-btn" onclick="toggleAnswers()">隱藏答案</button>
      <button class="btn" onclick="document.body.classList.toggle('show-lines')">切換作答線</button>
      <button class="btn" onclick="document.body.classList.toggle('compact')">切換緊湊版</button>
      <span style="color:#5f6b7a;font-size:10pt;">建議：A4、邊界預設、縮放 100%</span>
    </div>
"""
    )

    parts.append(
        f"""
    <section class="cover">
      <h1>{escape(book_title)}</h1>
      <p>題庫列印版</p>
      <p>試卷數：{total_exam} 份</p>
      <p>題目數：{total_q} 題</p>
      <p>產生時間：{escape(now)}</p>
    </section>

    <section class="toc">
      <h2>目錄</h2>
      <ol>
"""
    )

    for title in exams.keys():
        parts.append(f"<li>{escape(title)}</li>\n")

    parts.append("</ol>\n</section>\n")

    for title, questions in exams.items():
      parts.append(f"<section class='exam'>\n<h2>{escape(title)}</h2>\n")
      parts.append(
        f"<div class='meta'><span>共 {len(questions)} 題</span><span>試卷版型：列印友善</span></div>\n"
      )

      for q in questions:
        qno = q["question_no"]
        raw = q["question_html"] if q.get("question_html") else escape(q["question_text"])
        pretty = prettify_question_text(raw)
        item_url = q.get("item_url") or ""

        source_html = (
          f"<div class='source-link'>原題連結：<a href='{escape(item_url)}' target='_blank' rel='noopener noreferrer'>開啟原題頁面</a></div>"
          if item_url
          else ""
        )
        answer = (q.get("answer") or "").strip()
        answer_source = (q.get("answer_source") or "").strip()
        answer_html = ""
        if answer:
          note = "（來源：頁面答案）" if answer_source == "explicit" else "（來源：統計推估）"
          answer_html = f"<div class='answer-box'>答案：{escape(answer)}</div><div class='answer-note'>{note}</div>"
        practice_html = "<div class='practice-lines'><div class='line'></div><div class='line'></div></div>"

        parts.append(
          f"<article class='q'>"
          f"<div class='q-no'>第 {qno} 題</div>"
          f"<div class='q-text'>{pretty}</div>"
          f"{answer_html}"
          f"{source_html}"
          f"{practice_html}"
          f"</article>\n"
        )

      parts.append("</section>\n")

    parts.append("<section class='answers-summary'>\n")
    parts.append("<h2>答案總表（獨立頁）</h2>\n")
    parts.append("<p class='meta'><span>提示：可用上方按鈕切換題目區答案顯示；此頁固定彙整全部答案。</span></p>\n")

    for title, questions in exams.items():
      parts.append(f"<h3>{escape(title)}</h3>\n")
      parts.append("<div class='answer-grid'>\n")
      for q in questions:
        qno = q["question_no"]
        answer = (q.get("answer") or "").strip() or "-"
        parts.append(f"<span class='answer-chip'>第 {qno} 題：{escape(answer)}</span>\n")
      parts.append("</div>\n")

    parts.append("</section>\n")

    parts.append(
      """
  </div>
  <script>
    function toggleAnswers() {
      document.body.classList.toggle('hide-answers');
      const btn = document.getElementById('toggle-answer-btn');
      if (!btn) return;
      btn.textContent = document.body.classList.contains('hide-answers') ? '顯示答案' : '隱藏答案';
    }
  </script>
</body>
</html>
"""
    )
    return "".join(parts)


def main():
    parser = argparse.ArgumentParser(description="把題庫 CSV 轉成列印版 HTML")
    parser.add_argument("--input", default=INPUT_CSV, help="輸入 CSV 路徑")
    parser.add_argument("--output", default=OUTPUT_HTML, help="輸出 HTML 路徑")
    parser.add_argument("--book-title", default="iPAS 無形資產評價概論(一)", help="封面標題")
    args = parser.parse_args()

    exams = load_data(args.input)
    html = build_html(exams, args.book_title)

    with open(args.output, "w", encoding="utf-8") as f:
        f.write(html)

    print(f"已輸出：{args.output}")
    print(f"試卷數：{len(exams)}，題數：{sum(len(v) for v in exams.values())}")


if __name__ == "__main__":
    main()
