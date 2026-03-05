#!/usr/bin/env python3
import csv
import datetime as dt
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "boxoffice"
TREND_DIR = ROOT / "data" / "boxoffice_trends"
POSTS_DIR = ROOT / "_posts"

KOBIS_API_KEY = os.getenv("KOBIS_API_KEY", "fe8372a6229f81c0ada051da749bb9d5")
KOBIS_DAILY_URL = "https://kobis.or.kr/kobisopenapi/webservice/rest/boxoffice/searchDailyBoxOfficeList.json"


def ymd(d: dt.date) -> str:
    return d.strftime("%Y%m%d")


def post_date_str(d: dt.date) -> str:
    return d.strftime("%Y-%m-%d")


def fetch_daily(target_date: dt.date):
    query = urllib.parse.urlencode(
        {
            "key": KOBIS_API_KEY,
            "targetDt": ymd(target_date),
            "itemPerPage": 10,
            "multiMovieYn": "",
            "repNationCd": "",
            "wideAreaCd": "",
        }
    )
    url = f"{KOBIS_DAILY_URL}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as res:
        data = json.loads(res.read().decode("utf-8", errors="ignore"))

    lst = data.get("boxOfficeResult", {}).get("dailyBoxOfficeList", [])
    rows = []
    for r in lst:
        rows.append(
            {
                "rank": int(r.get("rank", 0) or 0),
                "movieNm": r.get("movieNm", "").strip(),
                "audiCnt": int(r.get("audiCnt", 0) or 0),
                "audiAcc": int(r.get("audiAcc", 0) or 0),
                "salesAmt": int(r.get("salesAmt", 0) or 0),
                "openDt": r.get("openDt", ""),
            }
        )
    return rows


def to_map(rows, key="movieNm", val="audiCnt"):
    return {r[key]: r[val] for r in rows if r.get(key)}


def write_csv(target_date: dt.date, rows):
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    p = DATA_DIR / f"{post_date_str(target_date)}.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(
            f,
            fieldnames=["date", "rank", "movieNm", "audiCnt", "audiAcc", "salesAmt", "openDt"],
        )
        wr.writeheader()
        for r in rows:
            wr.writerow({"date": post_date_str(target_date), **r})
    return p


def fetch_7day_trend(movie_name: str, end_date: dt.date):
    out = []
    for i in range(6, -1, -1):
        d = end_date - dt.timedelta(days=i)
        try:
            rows = fetch_daily(d)
        except Exception:
            continue
        val = 0
        for r in rows:
            if r["movieNm"] == movie_name:
                val = r["audiCnt"]
                break
        out.append({"date": post_date_str(d), "audiCnt": val})
    return out


def write_trend_csv(target_date: dt.date, trend_map):
    TREND_DIR.mkdir(parents=True, exist_ok=True)
    p = TREND_DIR / f"{post_date_str(target_date)}.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["date", "movieNm", "trendDate", "audiCnt"])
        wr.writeheader()
        for name, arr in trend_map.items():
            for it in arr:
                wr.writerow(
                    {
                        "date": post_date_str(target_date),
                        "movieNm": name,
                        "trendDate": it["date"],
                        "audiCnt": it["audiCnt"],
                    }
                )
    return p


def fmt_int(n: int) -> str:
    return f"{n:,}"


def make_post(target_date: dt.date, rows, prev_map, prev_week_map, trend_map):
    today = post_date_str(dt.date.today())
    post_path = POSTS_DIR / f"{today}-daily-boxoffice-{post_date_str(target_date)}.md"

    lines = []
    lines.append("| 순위 | 제목 | 일일관객수 | 채널 | 전일 대비 | 전주 동일요일 대비 | 박스오피스 추이 |")
    lines.append("|---:|---|---:|---|---:|---:|---|")

    for i, r in enumerate(rows, start=1):
        name = r["movieNm"]
        cur = r["audiCnt"]
        p = prev_map.get(name)
        w = prev_week_map.get(name)

        if p is None:
            d1 = "NEW"
        else:
            x = cur - p
            sign = "+" if x > 0 else ""
            d1 = f"{sign}{fmt_int(x)}"

        if w is None:
            d7 = "NEW"
        else:
            x = cur - w
            sign = "+" if x > 0 else ""
            d7 = f"{sign}{fmt_int(x)}"

        btn = f"<button class=\"trend-btn\" type=\"button\" data-trend-id=\"trend-{i}\">박스오피스 추이 보기</button>"
        lines.append(f"| {r['rank']} | {name} | {fmt_int(cur)} | 영화 | {d1} | {d7} | {btn} |")

    trend_sections = []
    for i, r in enumerate(rows, start=1):
        name = r["movieNm"]
        arr = trend_map.get(name, [])
        if arr:
            latest = arr[-1]["audiCnt"]
            best = max(x["audiCnt"] for x in arr)
            avg = int(sum(x["audiCnt"] for x in arr) / len(arr))
            body = (
                f"<div class=\"trend-meta\">"
                f"<span>최신 <strong>{fmt_int(latest)}명</strong></span>"
                f"<span>최고 <strong>{fmt_int(best)}명</strong></span>"
                f"<span>평균 <strong>{fmt_int(avg)}명</strong></span>"
                f"</div>"
                f"<div class=\"trend-table-wrap\">"
                f"<table class=\"trend-table\">"
                f"<thead><tr><th>날짜</th><th>일일관객수</th><th>보조값</th></tr></thead>"
                f"<tbody>"
                + "".join(
                    [
                        f"<tr><td>{it['date']}</td><td>{it['audiCnt']}</td><td>{it['audiCnt']}</td></tr>"
                        for it in arr
                    ]
                )
                + "</tbody></table></div>"
            )
        else:
            body = "<p class=\"trend-empty\">이 영화는 박스오피스 추이를 제공하지 않습니다.</p>"

        trend_sections.append(
            f"<details class=\"trend-details\" id=\"trend-{i}\">"
            f"<summary><span class=\"trend-title\">{name}</span></summary>"
            f"{body}"
            f"</details>"
        )

    content = f"""---
layout: post
title: "일일 박스오피스 ({post_date_str(target_date)})"
date: {today} 12:00:00 +0900
categories: [boxoffice]
tags: [daily, kobis, movie]
comments: true
---

영화진흥위원회(KOBIS) 일일 박스오피스 기준 집계입니다.

{chr(10).join(lines)}

<section class="trend-section">
## 영화별 박스오피스 추이

{chr(10).join(trend_sections)}
</section>

---

### 데이터 출처 및 기준

- 출처: **영화진흥위원회(KOBIS) 오픈 API**
- 집계 기준: 일일 박스오피스(전국)
- 안내: 본 콘텐츠는 정보 제공 목적이며, 최종 수치는 원출처 공지값을 기준으로 확인해 주세요.
"""
    post_path.write_text(content, encoding="utf-8")
    return post_path


def main():
    target_date = dt.date.today() - dt.timedelta(days=1)
    prev_date = target_date - dt.timedelta(days=1)
    prev_week_date = target_date - dt.timedelta(days=7)

    rows = fetch_daily(target_date)
    prev_rows = fetch_daily(prev_date)
    prev_week_rows = fetch_daily(prev_week_date)

    prev_map = to_map(prev_rows)
    prev_week_map = to_map(prev_week_rows)

    trend_map = {}
    for r in rows:
        trend_map[r["movieNm"]] = fetch_7day_trend(r["movieNm"], target_date)

    csv_path = write_csv(target_date, rows)
    trend_csv_path = write_trend_csv(target_date, trend_map)
    post_path = make_post(target_date, rows, prev_map, prev_week_map, trend_map)

    print(f"saved: {csv_path}")
    print(f"saved: {trend_csv_path}")
    print(f"saved: {post_path}")


if __name__ == "__main__":
    main()
