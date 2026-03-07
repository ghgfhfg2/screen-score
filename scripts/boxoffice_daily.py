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
                "movieCd": r.get("movieCd", "").strip(),
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
            fieldnames=["date", "rank", "movieCd", "movieNm", "audiCnt", "audiAcc", "salesAmt", "openDt"],
        )
        wr.writeheader()
        for r in rows:
            wr.writerow({"date": post_date_str(target_date), **r})
    return p


def fetch_daily_cached(target_date: dt.date, cache: dict):
    key = post_date_str(target_date)
    if key not in cache:
        cache[key] = fetch_daily(target_date)
    return cache[key]


def find_audi_cnt(rows, movie_cd: str, movie_name: str) -> int:
    for r in rows:
        if movie_cd and r.get("movieCd") == movie_cd:
            return r.get("audiCnt", 0)
    for r in rows:
        if r.get("movieNm") == movie_name:
            return r.get("audiCnt", 0)
    return 0


def fetch_7day_trend(movie_cd: str, movie_name: str, end_date: dt.date, cache: dict):
    out = []
    for i in range(6, -1, -1):
        d = end_date - dt.timedelta(days=i)
        try:
            rows = fetch_daily_cached(d, cache)
        except Exception:
            continue
        val = find_audi_cnt(rows, movie_cd, movie_name)
        out.append({"date": post_date_str(d), "audiCnt": val})
    return out


def fetch_full_trend(movie_cd: str, movie_name: str, open_dt: str, end_date: dt.date, cache: dict):
    try:
        start = dt.datetime.strptime(open_dt, "%Y-%m-%d").date() if open_dt else (end_date - dt.timedelta(days=30))
    except Exception:
        start = end_date - dt.timedelta(days=30)

    if start > end_date:
        start = end_date

    # 비정상적으로 긴 기간 요청 방지(재개봉/오래된 개봉일 등)
    if (end_date - start).days > 730:
        start = end_date - dt.timedelta(days=730)

    out = []
    d = start
    while d <= end_date:
        try:
            rows = fetch_daily_cached(d, cache)
        except Exception:
            d += dt.timedelta(days=1)
            continue
        val = find_audi_cnt(rows, movie_cd, movie_name)
        out.append({"date": post_date_str(d), "audiCnt": val})
        d += dt.timedelta(days=1)
    return out


def write_trend_csv(target_date: dt.date, trend_map):
    TREND_DIR.mkdir(parents=True, exist_ok=True)
    p = TREND_DIR / f"{post_date_str(target_date)}.csv"
    with p.open("w", encoding="utf-8", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=["date", "kind", "movieNm", "trendDate", "audiCnt"])
        wr.writeheader()
        for name, kinds in trend_map.items():
            for kind, arr in kinds.items():
                for it in arr:
                    wr.writerow(
                        {
                            "date": post_date_str(target_date),
                            "kind": kind,
                            "movieNm": name,
                            "trendDate": it["date"],
                            "audiCnt": it["audiCnt"],
                        }
                    )
    return p


def fmt_int(n: int) -> str:
    return f"{n:,}"


def make_post(target_date: dt.date, rows, prev_map, prev_week_map, trend_map):
    now = dt.datetime.now()
    today = now.date().isoformat()
    post_path = POSTS_DIR / f"{today}-daily-boxoffice-{post_date_str(target_date)}.md"

    lines = []
    lines.append("| 순위 | 제목 | 일일관객수 | 누적관객수 | 채널 | 전일 대비 | 박스오피스 추이 |")
    lines.append("|---:|---|---:|---:|---|---:|---|")

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

        btn_week = f"<button class=\"trend-btn\" type=\"button\" data-trend-id=\"trend-week-{i}\">주간 관객 추이보기</button>"
        btn_full = f"<button class=\"trend-btn\" type=\"button\" data-trend-id=\"trend-full-{i}\">전체 관객 추이보기</button>"
        btn_acc_week = f"<button class=\"trend-btn\" type=\"button\" data-trend-id=\"trend-acc-week-{i}\">주간 누적관객 추이보기</button>"
        btn_acc_full = f"<button class=\"trend-btn\" type=\"button\" data-trend-id=\"trend-acc-full-{i}\">전체 누적관객 추이보기</button>"
        lines.append(f"| {r['rank']} | {name} | {fmt_int(cur)} | {fmt_int(r['audiAcc'])} | 영화 | {d1} | {btn_week} {btn_full} {btn_acc_week} {btn_acc_full} |")

    trend_sections = []
    for i, r in enumerate(rows, start=1):
        name = r["movieNm"]

        for kind, detail_id, label in [
            ("week", f"trend-week-{i}", "주간 관객 추이"),
            ("full", f"trend-full-{i}", "전체 관객 추이"),
            ("acc_week", f"trend-acc-week-{i}", "주간 누적관객 추이"),
            ("acc_full", f"trend-acc-full-{i}", "전체 누적관객 추이"),
        ]:
            source_arr = trend_map.get(name, {}).get("full" if kind in ("acc_week", "acc_full") else kind, [])

            if kind in ("acc_week", "acc_full"):
                acc_full = []
                latest_acc = r.get("audiAcc", 0)
                running = latest_acc - sum(it["audiCnt"] for it in source_arr)
                for it in source_arr:
                    running += it["audiCnt"]
                    acc_full.append({"date": it["date"], "audiAcc": running})
                arr = acc_full[-7:] if kind == "acc_week" else acc_full
            else:
                arr = source_arr

            if arr:
                if kind in ("acc_week", "acc_full"):
                    latest = arr[-1]["audiAcc"]
                    start_val = arr[0]["audiAcc"]
                    growth = latest - start_val
                    start_label = "7일 전" if kind == "acc_week" else "개봉 첫날"
                    growth_label = "7일 증가" if kind == "acc_week" else "누적 증가"
                    body = (
                        f"<div class=\"trend-meta\">"
                        f"<span>최신 <strong>{fmt_int(latest)}명</strong></span>"
                        f"<span>{start_label} <strong>{fmt_int(start_val)}명</strong></span>"
                        f"<span>{growth_label} <strong>{fmt_int(growth)}명</strong></span>"
                        f"</div>"
                        f"<div class=\"trend-table-wrap\">"
                        f"<table class=\"trend-table\">"
                        f"<thead><tr><th>날짜</th><th>누적관객수</th></tr></thead>"
                        f"<tbody>"
                        + "".join(
                            [
                                f"<tr><td>{it['date']}</td><td>{it['audiAcc']}</td></tr>"
                                for it in arr
                            ]
                        )
                        + "</tbody></table></div>"
                    )
                else:
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
                        f"<thead><tr><th>날짜</th><th>일일관객수</th></tr></thead>"
                        f"<tbody>"
                        + "".join(
                            [
                                f"<tr><td>{it['date']}</td><td>{it['audiCnt']}</td></tr>"
                                for it in arr
                            ]
                        )
                        + "</tbody></table></div>"
                    )
            else:
                body = "<p class=\"trend-empty\">이 영화는 박스오피스 추이를 제공하지 않습니다.</p>"

            trend_sections.append(
                f"<details class=\"trend-details\" id=\"{detail_id}\">"
                f"<summary><span class=\"trend-title\">{name} · {label}</span></summary>"
                f"{body}"
                f"</details>"
            )

    content = f"""---
layout: post
title: "일일 박스오피스 ({post_date_str(target_date)})"
date: {now.strftime('%Y-%m-%d %H:%M:%S')} +0900
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
    daily_cache = {}
    for r in rows:
        name = r["movieNm"]
        movie_cd = r.get("movieCd", "")
        open_dt = r.get("openDt", "")
        trend_map[name] = {
            "week": fetch_7day_trend(movie_cd, name, target_date, daily_cache),
            "full": fetch_full_trend(movie_cd, name, open_dt, target_date, daily_cache),
        }

    csv_path = write_csv(target_date, rows)
    trend_csv_path = write_trend_csv(target_date, trend_map)
    post_path = make_post(target_date, rows, prev_map, prev_week_map, trend_map)

    print(f"saved: {csv_path}")
    print(f"saved: {trend_csv_path}")
    print(f"saved: {post_path}")


if __name__ == "__main__":
    main()
