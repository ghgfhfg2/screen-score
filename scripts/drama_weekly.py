#!/usr/bin/env python3
import csv
import datetime as dt
import re
import urllib.request
from pathlib import Path

URL = "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blUw&qvt=0&query=%EC%A3%BC%EA%B0%84%EB%93%9C%EB%9D%BC%EB%A7%88%20%EC%8B%9C%EC%B2%AD%EB%A5%A0"
ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "drama"
POSTS_DIR = ROOT / "_posts"

ROW_RE = re.compile(
    r"순위:\s*(\d+)\s*,\s*채널:\s*([^,;]+)\s*,\s*프로그램:\s*([^,;]+)\s*,\s*시청률:\s*([0-9]+(?:\.[0-9]+)?)"
)


def current_week_label(today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    y, w, _ = today.isocalendar()
    return f"{y}-{w:02d}"


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as res:
        raw = res.read().decode("utf-8", errors="ignore")
    # remove tags to improve regex hit chance
    text = re.sub(r"<[^>]+>", " ", raw)
    text = re.sub(r"\s+", " ", text)
    return text


def collect_rows(text: str):
    seen = set()
    out = []
    for m in ROW_RE.finditer(text):
        rank = int(m.group(1))
        channel = m.group(2).strip()
        title = m.group(3).strip()
        rating = float(m.group(4))

        # '(재방송)' 표기 항목 제외
        if "재방송" in title:
            continue

        key = (rank, channel, title)
        if key in seen:
            continue
        seen.add(key)
        out.append({"rank": rank, "channel": channel, "title": title, "rating": rating})
    return sorted(out, key=lambda x: x["rank"])


def read_prev(week_label: str):
    y, w = map(int, week_label.split("-"))
    d = dt.date.fromisocalendar(y, w, 1) - dt.timedelta(days=7)
    py, pw, _ = d.isocalendar()
    prev_label = f"{py}-{pw:02d}"
    p = DATA_DIR / f"{prev_label}.csv"
    if not p.exists():
        return prev_label, {}
    m = {}
    with p.open("r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            m[row["title"]] = float(row["rating"])
    return prev_label, m


def write_csv(week_label: str, rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = DATA_DIR / f"{week_label}.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["week", "rank", "channel", "title", "rating"])
        wr.writeheader()
        for r in rows:
            wr.writerow({"week": week_label, **r})
    return p


def make_post(week_label: str, prev_label: str, rows, prev_map):
    today = dt.date.today().isoformat()
    post_path = POSTS_DIR / f"{today}-weekly-drama-ratings-{week_label}.md"

    lines = []
    lines.append("| 순위 | 채널 | 드라마 | 시청률(%) | 전주 대비 |")
    lines.append("|---:|---|---|---:|---:|")
    for r in rows:
        prev = prev_map.get(r["title"])
        if prev is None:
            diff = "NEW"
        else:
            d = r["rating"] - prev
            sign = "+" if d > 0 else ""
            diff = f"{sign}{d:.3f}%p"
        lines.append(f"| {r['rank']} | {r['channel']} | {r['title']} | {r['rating']:.3f} | {diff} |")

    content = f"""---
layout: post
title: \"주간 드라마 시청률 ({week_label})\"
date: {today} 09:00:00 +0900
categories: [drama-ratings]
tags: [weekly, naver, nielsen]
---

이번 주 드라마/방송 시청률 요약입니다. (기준: 네이버 주간드라마 시청률)

- 기준 주차: **{week_label}**
- 비교 주차: **{prev_label}**

{chr(10).join(lines)}

> 자동 생성 포스트입니다. 수집 소스 구조 변경 시 값이 누락될 수 있습니다.
"""
    post_path.write_text(content, encoding="utf-8")
    return post_path


def main():
    week = current_week_label()
    text = fetch_text(URL)
    rows = collect_rows(text)
    if not rows:
        raise SystemExit("수집 실패: 패턴 매칭 결과가 없습니다. 소스 구조가 바뀌었을 수 있습니다.")
    prev_label, prev_map = read_prev(week)
    csv_path = write_csv(week, rows)
    post_path = make_post(week, prev_label, rows, prev_map)
    print(f"saved: {csv_path}")
    print(f"saved: {post_path}")


if __name__ == "__main__":
    main()
