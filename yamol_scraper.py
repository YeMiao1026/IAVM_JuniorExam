import argparse
import csv
import re
import time
from html import unescape
from urllib.parse import urljoin, urlparse, parse_qs

import requests
from bs4 import BeautifulSoup

BASE = "https://yamol.tw"
DEFAULT_START_URL = (
    "https://yamol.tw/cat-iPAS%E2%97%86%E7%84%A1%E5%BD%A2%E8%B3%87%E7%94%A2%E8%A9%95"
    "%E5%83%B9%E6%A6%82%E8%AB%96%28%E4%B8%80%29%E2%97%86%E5%88%9D%E7%B4%9A-5261.htm"
    "?userobot=1&page=1"
)


def clean_text(text: str) -> str:
    text = unescape(text or "")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def get_page(session: requests.Session, url: str, timeout: int = 20) -> str:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def collect_exam_links(session: requests.Session, start_url: str, delay: float = 0.5):
    """從分類頁抓所有試卷網址。"""
    seen_pages = set()
    queue = [start_url]
    exam_links = set()

    while queue:
        url = queue.pop(0)
        if url in seen_pages:
            continue
        seen_pages.add(url)

        html = get_page(session, url)
        soup = BeautifulSoup(html, "html.parser")

        for a in soup.select("a.exam-item"):
            href = a.get("href")
            if href:
                exam_links.add(urljoin(BASE, href))

        # 分頁: 抓 rel=next 或 page=xx 連結
        next_links = []
        for a in soup.select(".pagination a[href]"):
            href = a.get("href", "")
            full = urljoin(BASE, href)
            if "page=" in full:
                next_links.append(full)

        for nxt in next_links:
            if nxt not in seen_pages and nxt not in queue:
                queue.append(nxt)

        time.sleep(delay)

    return sorted(exam_links)


def parse_exam_page(session: requests.Session, exam_url: str, delay: float = 0.5):
    """抓一份試卷中的所有題目文字與題目內圖片。"""
    html = get_page(session, exam_url)
    soup = BeautifulSoup(html, "html.parser")

    exam_title = clean_text(soup.select_one("h1.exam-title").get_text(" ")) if soup.select_one("h1.exam-title") else ""

    rows = []
    items = soup.select(".list-block .list-item")

    for idx, item in enumerate(items, start=1):
        a = item.select_one("a[href]")
        p = item.select_one("p")

        href = urljoin(BASE, a.get("href")) if a else ""
        content_tag = p if p else item

        # 把題目中的圖片 src 轉成絕對路徑，避免列印檔抓不到圖
        for img in content_tag.select("img[src]"):
            img["src"] = urljoin(BASE, img.get("src", ""))

        question_html = content_tag.decode_contents().strip()
        image_urls = [urljoin(BASE, img.get("src", "")) for img in content_tag.select("img[src]")]

        question_raw = content_tag.get_text(" ", strip=True)
        question = clean_text(question_raw)

        # 嘗試從前綴抓題號，失敗就用順序號
        m = re.match(r"^(\d+)\.", question)
        q_no = int(m.group(1)) if m else idx

        rows.append(
            {
                "exam_title": exam_title,
                "exam_url": exam_url,
                "question_no": q_no,
                "question_text": question,
                "question_html": question_html,
                "image_urls": "|".join(image_urls),
                "item_url": href,
            }
        )

    time.sleep(delay)
    return rows


def main():
    parser = argparse.ArgumentParser(description="Yamol 題目爬蟲（僅抓題目清單）")
    parser.add_argument("--start-url", default=DEFAULT_START_URL, help="分類起始頁")
    parser.add_argument("--output", default="yamol_questions.csv", help="輸出 CSV 檔名")
    parser.add_argument("--delay", type=float, default=0.6, help="每次請求延遲秒數")
    parser.add_argument("--max-exams", type=int, default=0, help="最多抓幾份試卷（0=全部）")
    args = parser.parse_args()

    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0.0.0 Safari/537.36"
            )
        }
    )

    exam_links = collect_exam_links(session, args.start_url, delay=args.delay)
    if args.max_exams > 0:
        exam_links = exam_links[: args.max_exams]

    all_rows = []
    for i, exam_url in enumerate(exam_links, start=1):
        print(f"[{i}/{len(exam_links)}] {exam_url}")
        try:
            rows = parse_exam_page(session, exam_url, delay=args.delay)
            all_rows.extend(rows)
        except Exception as e:
            print(f"  失敗: {e}")

    all_rows.sort(key=lambda x: (x["exam_title"], x["question_no"]))

    with open(args.output, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "exam_title",
                "exam_url",
                "question_no",
                "question_text",
                "question_html",
                "image_urls",
                "item_url",
            ],
        )
        writer.writeheader()
        writer.writerows(all_rows)

    print(f"完成，共 {len(all_rows)} 題，輸出：{args.output}")


if __name__ == "__main__":
    main()
