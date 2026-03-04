#!/usr/bin/env python3
import csv
import datetime as dt
import html
import re
import urllib.request
from pathlib import Path

URLS = {
    "지상파": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blUw&qvt=0&query=02%EC%9B%9423%EC%9D%BC%EC%A3%BC%20%EB%93%9C%EB%9D%BC%EB%A7%88%20%EC%8B%9C%EC%B2%AD%EB%A5%A0",
    "종합편성": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blUw&qvt=0&query=02%EC%9B%9423%EC%9D%BC%EC%A3%BC%20%EB%93%9C%EB%9D%BC%EB%A7%88%20%EC%A2%85%ED%95%A9%ED%8E%B8%EC%84%B1%EC%8B%9C%EC%B2%AD%EB%A5%A0",
    "케이블": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blUw&qvt=0&query=02%EC%9B%9423%EC%9D%BC%EC%A3%BC%20%EC%BC%80%EC%9D%B4%EB%B8%94%20%EC%8B%9C%EC%B2%AD%EB%A5%A0",
}

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "drama"
POSTS_DIR = ROOT / "_posts"

ROW_RE = re.compile(
    r"<tr>\s*"
    r".*?<span class=\"blind\">(\d+)</span>.*?"
    r"<td><p><a[^>]*>(.*?)</a></p></td>.*?"
    r"<td class=\"ct\"><p><a[^>]*>(.*?)</a></p></td>.*?"
    r"<td class=\"ct scroll_p\"><p class=\"rate[^\"]*\">([0-9]+(?:\.[0-9]+)?)%?</p>"
    r".*?</tr>",
    flags=re.S,
)


def current_week_label(today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    y, w, _ = today.isocalendar()
    return f"{y}-{w:02d}"


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as res:
        raw = res.read().decode("utf-8", errors="ignore")

    # 요청한 대로 div.scroll_bx 내부만 수집
    block_match = re.search(r"<div class=\"scroll_bx\">.*?</div>\s*</div>", raw, flags=re.S)
    if not block_match:
        raise SystemExit(f"수집 실패: div.scroll_bx 블록을 찾지 못했습니다. url={url}")

    return block_match.group(0)


def collect_rows(segment: str, text: str):
    seen = set()
    seen_rank = set()
    out = []
    for m in ROW_RE.finditer(text):
        rank = int(m.group(1))
        title = html.unescape(re.sub(r"<[^>]+>", "", m.group(2))).strip()
        channel = html.unescape(re.sub(r"<[^>]+>", "", m.group(3))).strip()
        rating = float(m.group(4))

        if "재방송" in title:
            continue

        key = (rank, channel, title)
        if key in seen or rank in seen_rank:
            continue
        seen.add(key)
        seen_rank.add(rank)
        out.append({"segment": segment, "rank": rank, "channel": channel, "title": title, "rating": rating})

        if len(out) >= 10:
            break

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
            seg = row.get("segment", "전체")
            m[(seg, row["title"])] = float(row["rating"])
    return prev_label, m


def write_csv(week_label: str, rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = DATA_DIR / f"{week_label}.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["week", "segment", "rank", "channel", "title", "rating"])
        wr.writeheader()
        for r in rows:
            wr.writerow({"week": week_label, **r})
    return p


def render_table(rows, prev_map):
    lines = []
    lines.append("| 순위 | 채널 | 드라마 | 시청률(%) | 전주 대비 |")
    lines.append("|---:|---|---|---:|---:|")
    for r in rows:
        prev = prev_map.get((r["segment"], r["title"]))
        if prev is None:
            diff = "NEW"
        else:
            d = r["rating"] - prev
            sign = "+" if d > 0 else ""
            diff = f"{sign}{d:.3f}%p"
        lines.append(f"| {r['rank']} | {r['channel']} | {r['title']} | {r['rating']:.3f} | {diff} |")
    return "\n".join(lines)


def make_post(week_label: str, prev_label: str, rows, prev_map):
    today = dt.date.today().isoformat()
    post_path = POSTS_DIR / f"{today}-weekly-drama-ratings-{week_label}.md"

    sections = []
    for seg in ["지상파", "종합편성", "케이블"]:
        seg_rows = [r for r in rows if r["segment"] == seg]
        if not seg_rows:
            continue
        sections.append(f"## {seg}\n\n" + render_table(seg_rows, prev_map))

    content = f"""---
layout: post
title: \"주간 드라마 시청률 ({week_label})\"
date: {today} 09:00:00 +0900
categories: [drama-ratings]
tags: [weekly, naver, nielsen]
---

이번 주 드라마 시청률 요약입니다. (기준: 네이버 검색 결과)

- 기준 주차: **{week_label}**
- 비교 주차: **{prev_label}**
- 수집 소스: 지상파 / 종합편성 / 케이블 3개 URL

{chr(10).join(sections)}

> 자동 생성 포스트입니다. 소스 구조 변경 시 값이 누락될 수 있습니다.
"""
    post_path.write_text(content, encoding="utf-8")
    return post_path


def main():
    week = current_week_label()
    all_rows = []

    for segment, url in URLS.items():
        text = fetch_text(url)
        rows = collect_rows(segment, text)
        if not rows:
            raise SystemExit(f"수집 실패: {segment} 패턴 매칭 결과가 없습니다.")
        all_rows.extend(rows)

    prev_label, prev_map = read_prev(week)
    csv_path = write_csv(week, all_rows)
    post_path = make_post(week, prev_label, all_rows, prev_map)
    print(f"saved: {csv_path}")
    print(f"saved: {post_path}")


if __name__ == "__main__":
    main()
