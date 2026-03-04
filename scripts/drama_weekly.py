#!/usr/bin/env python3
import csv
import datetime as dt
import html
import re
import urllib.parse
import urllib.request
from pathlib import Path

URLS = {
    "지상파": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blUw&qvt=0&query=02%EC%9B%9423%EC%9D%BC%EC%A3%BC%20%EB%93%9C%EB%9D%BC%EB%A7%88%20%EC%8B%9C%EC%B2%AD%EB%A5%A0",
    "종합편성": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blUw&qvt=0&query=02%EC%9B%9423%EC%9D%BC%EC%A3%BC%20%EB%93%9C%EB%9D%BC%EB%A7%88%20%EC%A2%85%ED%95%A9%ED%8E%B8%EC%84%B1%EC%8B%9C%EC%B2%AD%EB%A5%A0",
    "케이블": "https://search.naver.com/search.naver?where=nexearch&sm=tab_etc&mra=blUw&qvt=0&query=02%EC%9B%9423%EC%9D%BC%EC%A3%BC%20%EB%93%9C%EB%9D%BC%EB%A7%88%20%EC%BC%80%EC%9D%B4%EB%B8%94%EC%8B%9C%EC%B2%AD%EB%A5%A0",
}

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "drama"
POSTS_DIR = ROOT / "_posts"
THUMBNAIL_MAP_PATH = ROOT / "_data" / "drama_thumbnails.yml"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "ko-KR,ko;q=0.9,en-US;q=0.8,en;q=0.7",
    "Referer": "https://search.naver.com/",
}

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
    req = urllib.request.Request(url, headers=HEADERS)
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


def load_thumbnail_map():
    m = {}
    if not THUMBNAIL_MAP_PATH.exists():
        return m

    line_re = re.compile(r'^\s*"(?P<k>.*)"\s*:\s*"(?P<v>.*)"\s*$')
    for line in THUMBNAIL_MAP_PATH.read_text(encoding="utf-8").splitlines():
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        mm = line_re.match(s)
        if not mm:
            continue
        key = mm.group("k").replace('\\"', '"').replace('\\\\', '\\').strip()
        val = mm.group("v").replace('\\"', '"').replace('\\\\', '\\').strip()
        if key and val:
            m[key] = val
    return m


def save_thumbnail_map(m):
    THUMBNAIL_MAP_PATH.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# 드라마명: 썸네일 이미지 URL (자동 수집 + 수동 보정)"]
    for k in sorted(m.keys()):
        k2 = k.replace('\\', '\\\\').replace('"', '\\"')
        v2 = m[k].replace('\\', '\\\\').replace('"', '\\"')
        lines.append(f'"{k2}": "{v2}"')
    THUMBNAIL_MAP_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")


def fetch_thumbnail_by_title(title: str) -> str:
    # 요청 방식: "{드라마명} 정보" 검색 결과에서 a.thumb > img 추출
    q = urllib.parse.quote(f"{title} 정보")
    url = (
        "https://search.naver.com/search.naver"
        f"?where=nexearch&sm=tab_etc&mra=bjkw&pkid=57&qvt=0&query={q}"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8", errors="ignore")
    except Exception:
        return ""

    m = re.search(r'<a[^>]*class="thumb"[^>]*>.*?<img[^>]*>', raw, flags=re.S)
    if not m:
        return ""

    tag = m.group(0)
    for attr in ["src", "data-lazysrc", "data-src"]:
        mm = re.search(attr + r'="([^"]+)"', tag)
        if mm:
            return html.unescape(mm.group(1)).strip()

    return ""


def render_table(rows, prev_map, thumbnail_map):
    # 3개 소스를 합쳐 시청률 기준으로 통합 순위 산정
    sorted_rows = sorted(rows, key=lambda x: x["rating"], reverse=True)

    lines = []
    lines.append("| 통합순위 | 썸네일 | 채널 | 드라마 | 시청률(%) | 전주 대비 |")
    lines.append("|---:|---|---|---|---:|---:|")

    for i, r in enumerate(sorted_rows, start=1):
        prev = prev_map.get((r["segment"], r["title"]))
        if prev is None:
            diff = "NEW"
        else:
            d = r["rating"] - prev
            sign = "+" if d > 0 else ""
            diff = f"{sign}{d:.3f}%p"

        thumb_url = thumbnail_map.get(r["title"], "")
        thumb = f'<img src="{thumb_url}" alt="{r["title"]}" width="72" />' if thumb_url else "-"

        lines.append(f"| {i} | {thumb} | {r['channel']} | {r['title']} | {r['rating']:.3f} | {diff} |")

    return "\n".join(lines)


def make_post(week_label: str, prev_label: str, rows, prev_map):
    today = dt.date.today().isoformat()
    post_path = POSTS_DIR / f"{today}-weekly-drama-ratings-{week_label}.md"

    thumbnail_map = load_thumbnail_map()

    # 매핑 없는 작품은 드라마명 기준으로 썸네일 자동 탐색 후 캐시
    changed = False
    for r in rows:
        t = r["title"]
        existing = thumbnail_map.get(t, "")
        # 기존 값이 없거나 기본 og 이미지면 재탐색
        if existing and "og_v3.png" not in existing:
            continue
        img = fetch_thumbnail_by_title(t)
        if img:
            thumbnail_map[t] = img
            changed = True

    if changed:
        save_thumbnail_map(thumbnail_map)

    table_md = render_table(rows, prev_map, thumbnail_map)

    content = f"""---
layout: post
title: \"주간 드라마 시청률 ({week_label})\"
date: {today} 09:00:00 +0900
categories: [drama-ratings]
tags: [weekly, naver, nielsen]
---

이번 주 드라마 시청률 요약입니다.

{table_md}
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
