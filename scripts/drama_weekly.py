#!/usr/bin/env python3
import csv
import datetime as dt
import html
import json
import os
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
TREND_DIR = ROOT / "data" / "drama_trends"
POSTS_DIR = ROOT / "_posts"
THUMBNAIL_MAP_PATH = ROOT / "_data" / "drama_thumbnails.yml"
TMDB_API_KEY = os.getenv("TMDB_API_KEY", "")
TMDB_IMAGE_BASE = "https://image.tmdb.org/t/p/w342"

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
    # TMDB 기반 포스터 조회 (저작권/출처 정책 관리 용이)
    if not TMDB_API_KEY:
        return ""

    q = urllib.parse.quote(title)
    url = (
        "https://api.themoviedb.org/3/search/tv"
        f"?api_key={TMDB_API_KEY}&language=ko-KR&query={q}&page=1&include_adult=false"
    )
    req = urllib.request.Request(url, headers={"User-Agent": HEADERS["User-Agent"]})
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8", errors="ignore")
        data = json.loads(raw)
    except Exception:
        return ""

    results = data.get("results", []) or []
    for item in results:
        poster_path = item.get("poster_path")
        if poster_path:
            return f"{TMDB_IMAGE_BASE}{poster_path}"

    return ""


def fetch_rating_trend_by_title(title: str):
    q = urllib.parse.quote(f"{title} 시청률")
    url = (
        "https://search.naver.com/search.naver"
        f"?where=nexearch&sm=tab_etc&mra=bjkw&x_csa=%7B%22pkid%22%3A%2257%22%2C%20%22isOpen%22%3Afalse%2C%20%22tab%22%3A%22rating%22%7D&pkid=57&qvt=0&query={q}"
    )
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            raw = res.read().decode("utf-8", errors="ignore")
    except Exception:
        return []

    block_m = re.search(
        r'"containerSelector":\s*"\._chart_container1".*?"dateList":\s*\[(.*?)\]\s*\}',
        raw,
        flags=re.S,
    )
    if not block_m:
        return []

    block = block_m.group(1)
    out = []
    item_re = re.compile(
        r'"turn":\s*"(\d+)"\+"회".*?"rating":\s*"([0-9]+(?:\.[0-9]+)?)".*?"date":\s*"([^"]+)"',
        flags=re.S,
    )
    for m in item_re.finditer(block):
        out.append({"turn": int(m.group(1)), "rating": float(m.group(2)), "date": m.group(3)})

    return out


def write_trend_csv(week_label: str, trend_map):
    TREND_DIR.mkdir(parents=True, exist_ok=True)
    p = TREND_DIR / f"{week_label}.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["week", "title", "turn", "date", "rating"])
        wr.writeheader()
        for title, arr in trend_map.items():
            for it in arr:
                wr.writerow({
                    "week": week_label,
                    "title": title,
                    "turn": it["turn"],
                    "date": it["date"],
                    "rating": it["rating"],
                })
    return p


def render_table(rows, prev_map, thumbnail_map):
    # 3개 소스를 합쳐 시청률 기준으로 통합 순위 산정
    sorted_rows = sorted(rows, key=lambda x: x["rating"], reverse=True)

    lines = []
    lines.append("| 통합순위 | 채널 | 제목 | 시청률(%) | 전주 대비 | 시청률 추이 |")
    lines.append("|---:|---|---|---:|---:|---|")

    for i, r in enumerate(sorted_rows, start=1):
        prev = prev_map.get((r["segment"], r["title"]))
        if prev is None:
            diff = "NEW"
        else:
            d = r["rating"] - prev
            sign = "+" if d > 0 else ""
            diff = f"{sign}{d:.3f}%p"

        trend_link = f"<button class=\"trend-btn\" type=\"button\" data-trend-id=\"trend-{i}\">시청률 추이 보기</button>"

        lines.append(f"| {i} | {r['channel']} | {r['title']} | {r['rating']:.3f} | {diff} | {trend_link} |")

    return "\n".join(lines), sorted_rows


def make_post(week_label: str, prev_label: str, rows, prev_map, trend_map):
    now = dt.datetime.now()
    today = now.date().isoformat()
    collected_at = now.strftime("%Y-%m-%d %H:%M KST")
    post_path = POSTS_DIR / f"{today}-weekly-drama-ratings-{week_label}.md"

    # 이미지 컬럼 제거: 포스터 조회 로직 비활성화
    thumbnail_map = {}

    table_md, sorted_rows = render_table(rows, prev_map, thumbnail_map)

    trend_sections = []
    for i, r in enumerate(sorted_rows, start=1):
        title = r["title"]
        arr = sorted(trend_map.get(title, []), key=lambda x: x["turn"])

        if arr:
            latest = arr[-1]["rating"]
            best = max(x["rating"] for x in arr)
            avg = sum(x["rating"] for x in arr) / len(arr)

            rows_html = []
            for it in arr:
                rows_html.append(
                    f"<tr><td>{it['turn']}회</td><td>{it['date']}</td><td>{it['rating']:.3f}</td></tr>"
                )

            body = (
                f"<div class=\"trend-meta\">"
                f"<span>최신 <strong>{latest:.3f}%</strong></span>"
                f"<span>최고 <strong>{best:.3f}%</strong></span>"
                f"<span>평균 <strong>{avg:.3f}%</strong></span>"
                f"</div>"
                f"<div class=\"trend-table-wrap\">"
                f"<table class=\"trend-table\">"
                f"<thead><tr><th>회차</th><th>방영일</th><th>시청률(%)</th></tr></thead>"
                f"<tbody>{''.join(rows_html)}</tbody>"
                f"</table></div>"
            )
        else:
            body = "<p class=\"trend-empty\">시청률 추이 데이터를 찾지 못했습니다.</p>"

        trend_sections.append(
            f"<details class=\"trend-details\" id=\"trend-{i}\">"
            f"<summary><span class=\"trend-title\">{title}</span></summary>"
            f"{body}"
            f"</details>"
        )

    content = f"""---
layout: post
title: \"주간 드라마 시청률 ({week_label})\"
date: {today} 09:00:00 +0900
categories: [drama-ratings]
tags: [weekly, naver, nielsen]
---

이번 주 드라마 시청률 요약입니다.

{table_md}

<section class="trend-section">
## 드라마별 시청률 추이

{chr(10).join(trend_sections)}
</section>

---

### 데이터 출처 및 기준

- 출처: **닐슨코리아(Nielsen Korea)**
- 집계 기준: 주간 단위 시청률
- 수집 일시: {collected_at}
- 안내: 본 콘텐츠는 정보 제공 목적이며, 최종 수치는 원출처 공지값을 기준으로 확인해 주세요.
"""
    post_path.write_text(content, encoding="utf-8")
    return post_path


def main():
    week = current_week_label()
    all_rows = []

    if not TMDB_API_KEY:
        print("warn: TMDB_API_KEY not set, poster lookup will be skipped")

    for segment, url in URLS.items():
        text = fetch_text(url)
        rows = collect_rows(segment, text)
        if not rows:
            raise SystemExit(f"수집 실패: {segment} 패턴 매칭 결과가 없습니다.")
        all_rows.extend(rows)

    prev_label, prev_map = read_prev(week)

    # 제목 기준 시청률 추이 수집(차트 dateList)
    trend_map = {}
    for r in all_rows:
        t = r["title"]
        if t in trend_map:
            continue
        trend_map[t] = fetch_rating_trend_by_title(t)

    csv_path = write_csv(week, all_rows)
    trend_csv_path = write_trend_csv(week, trend_map)
    post_path = make_post(week, prev_label, all_rows, prev_map, trend_map)
    print(f"saved: {csv_path}")
    print(f"saved: {trend_csv_path}")
    print(f"saved: {post_path}")


if __name__ == "__main__":
    main()
