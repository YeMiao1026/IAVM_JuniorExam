import argparse
import csv
import re
import time
from typing import Dict, Tuple

import requests
from bs4 import BeautifulSoup


ANSWER_RE = re.compile(r"答案\s*[:：]\s*([A-E])", re.IGNORECASE)
STATS_RE = re.compile(r"([A-E])\((\d+)\)")
ITEM_ID_RE = re.compile(r"#(\d+)")


def parse_item_answer(html: str) -> Tuple[str, str, str, str]:
    """
    回傳: (answer, answer_source, answer_confidence, answer_stats)
    - answer_source: explicit | inferred_from_stats | missing
    - answer_confidence: high | medium | low
    """
    soup = BeautifulSoup(html, "html.parser")
    box = soup.select_one(".item-answer")
    if not box:
        return "", "missing", "low", ""

    box_text = box.get_text(" ", strip=True)
    box_html = str(box)

    # 1) 明確答案
    m = ANSWER_RE.search(box_text)
    if m:
        ans = m.group(1).upper()
        stats = "|".join(f"{k}:{v}" for k, v in STATS_RE.findall(box_text))
        return ans, "explicit", "high", stats

    # 2) 統計推估
    stats_pairs = [(k.upper(), int(v)) for k, v in STATS_RE.findall(box_text)]
    if not stats_pairs:
        stats_pairs = [(k.upper(), int(v)) for k, v in STATS_RE.findall(box_html)]

    if stats_pairs:
        stats_map: Dict[str, int] = {}
        for k, v in stats_pairs:
            stats_map[k] = v

        max_vote = max(stats_map.values())
        best = sorted([k for k, v in stats_map.items() if v == max_vote])
        answer = "/".join(best)
        confidence = "medium" if len(best) == 1 else "low"
        stats = "|".join(f"{k}:{stats_map[k]}" for k in sorted(stats_map.keys()))
        return answer, "inferred_from_stats", confidence, stats

    return "", "missing", "low", ""


def fetch(session: requests.Session, url: str, timeout: int = 20) -> str:
    r = session.get(url, timeout=timeout)
    r.raise_for_status()
    return r.text


def enrich_csv(input_csv: str, output_csv: str, delay: float = 0.2) -> None:
    rows = []
    with open(input_csv, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)

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

    total = len(rows)
    for i, row in enumerate(rows, start=1):
        item_url = (row.get("item_url") or "").strip()
        if not item_url:
            row["answer"] = ""
            row["answer_source"] = "missing"
            row["answer_confidence"] = "low"
            row["answer_stats"] = ""
            row["item_id"] = ""
            continue

        print(f"[{i}/{total}] {item_url}")
        try:
            html = fetch(session, item_url)
            answer, source, confidence, stats = parse_item_answer(html)

            # item_id 取自統計文字中的 #xxxx
            m = ITEM_ID_RE.search(html)
            item_id = m.group(1) if m else ""

            row["answer"] = answer
            row["answer_source"] = source
            row["answer_confidence"] = confidence
            row["answer_stats"] = stats
            row["item_id"] = item_id
        except Exception as e:
            row["answer"] = ""
            row["answer_source"] = "error"
            row["answer_confidence"] = "low"
            row["answer_stats"] = ""
            row["item_id"] = ""
            row["answer_error"] = str(e)

        time.sleep(delay)

    # 欄位順序
    base_fields = list(rows[0].keys()) if rows else []
    for col in ["answer", "answer_source", "answer_confidence", "answer_stats", "item_id", "answer_error"]:
        if col not in base_fields:
            base_fields.append(col)

    with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=base_fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"完成：{output_csv}（共 {total} 題）")


def main():
    parser = argparse.ArgumentParser(description="為題庫 CSV 補上答案欄位")
    parser.add_argument("--input", required=True, help="輸入 CSV")
    parser.add_argument("--output", required=True, help="輸出 CSV")
    parser.add_argument("--delay", type=float, default=0.2, help="請求間隔秒數")
    args = parser.parse_args()

    enrich_csv(args.input, args.output, delay=args.delay)


if __name__ == "__main__":
    main()
