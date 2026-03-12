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
KOBIS_MOVIE_INFO_URL = "https://kobis.or.kr/kobisopenapi/webservice/rest/movie/searchMovieInfo.json"


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


def load_cached_daily(target_date: dt.date):
    p = DATA_DIR / f"{post_date_str(target_date)}.csv"
    if not p.exists():
        return []
    out = []
    with p.open("r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            out.append(
                {
                    "rank": int(r.get("rank", 0) or 0),
                    "movieCd": (r.get("movieCd") or "").strip(),
                    "movieNm": (r.get("movieNm") or "").strip(),
                    "audiCnt": int(r.get("audiCnt", 0) or 0),
                    "audiAcc": int(r.get("audiAcc", 0) or 0),
                    "salesAmt": int(r.get("salesAmt", 0) or 0),
                    "openDt": (r.get("openDt") or "").strip(),
                }
            )
    return out


def fetch_daily_cached(target_date: dt.date, cache: dict):
    key = post_date_str(target_date)
    if key not in cache:
        cache[key] = fetch_daily(target_date)
    return cache[key]


def fetch_movie_info(movie_cd: str, cache: dict):
    if not movie_cd:
        return {"director": "-", "casts": []}

    if movie_cd in cache:
        return cache[movie_cd]

    query = urllib.parse.urlencode({"key": KOBIS_API_KEY, "movieCd": movie_cd})
    url = f"{KOBIS_MOVIE_INFO_URL}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})

    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            data = json.loads(res.read().decode("utf-8", errors="ignore"))
        info = data.get("movieInfoResult", {}).get("movieInfo", {})
        directors = info.get("directors", []) or []
        actors = info.get("actors", []) or []
        genres = info.get("genres", []) or []
        nations = info.get("nations", []) or []
        audits = info.get("audits", []) or []

        director = ", ".join([d.get("peopleNm", "").strip() for d in directors if d.get("peopleNm")]).strip()
        if not director:
            director = "-"

        casts = []
        seen = set()
        for a in actors[:20]:
            actor = (a.get("peopleNm") or "").strip()
            role = (a.get("cast") or "").strip()
            if actor:
                key = (role, actor)
                if key in seen:
                    continue
                seen.add(key)
                casts.append({"actor": actor, "role": role})

        out = {
            "director": director,
            "casts": casts,
            "genres": ", ".join([g.get("genreNm", "").strip() for g in genres if g.get("genreNm")]) or "-",
            "nations": ", ".join([n.get("nationNm", "").strip() for n in nations if n.get("nationNm")]) or "-",
            "showTm": info.get("showTm", "") or "-",
            "watchGrade": ", ".join([a.get("watchGradeNm", "").strip() for a in audits if a.get("watchGradeNm")]) or "-",
        }
    except Exception:
        out = {"director": "-", "casts": []}

    cache[movie_cd] = out
    return out


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
        start = end_date - dt.timedelta(days=30)

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


def load_prev_full_trend(target_date: dt.date):
    prev_date = target_date - dt.timedelta(days=1)
    p = TREND_DIR / f"{post_date_str(prev_date)}.csv"
    out = {}
    if not p.exists():
        return out

    with p.open("r", encoding="utf-8") as f:
        rd = csv.DictReader(f)
        for r in rd:
            if r.get("kind") != "full":
                continue
            name = (r.get("movieNm") or "").strip()
            day = (r.get("trendDate") or "").strip()
            if not name or not day:
                continue
            try:
                cnt = int(r.get("audiCnt", 0) or 0)
            except Exception:
                cnt = 0
            out.setdefault(name, []).append({"date": day, "audiCnt": cnt})

    for name in out:
        out[name].sort(key=lambda x: x["date"])
    return out


def append_today_to_full_trend(prev_full, target_date: dt.date, today_cnt: int):
    day = post_date_str(target_date)
    arr = list(prev_full or [])
    if arr and arr[-1].get("date") == day:
        arr[-1]["audiCnt"] = today_cnt
    else:
        arr.append({"date": day, "audiCnt": today_cnt})
    return arr


def trim_leading_zeros(arr):
    if not arr:
        return arr
    idx = 0
    while idx < len(arr) and int(arr[idx].get("audiCnt", 0) or 0) == 0:
        idx += 1
    if idx >= len(arr):
        return arr[-1:]
    return arr[idx:]


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


def make_post(target_date: dt.date, rows, prev_map, prev_week_map, trend_map, movie_info_map):
    now = dt.datetime.now()
    today = now.date().isoformat()
    post_path = POSTS_DIR / f"{today}-daily-boxoffice-{post_date_str(target_date)}.md"

    lines = []
    lines.append("| 순위 | 제목 | 개봉일 | 일일관객수 | 누적관객수 | 전일 대비 | 박스오피스 추이 |")
    lines.append("|---:|---|---:|---:|---:|---:|---|")

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

        btn_full = f"<button class=\"trend-btn\" type=\"button\" data-trend-id=\"trend-full-{i}\">일 관객 수 추이보기</button>"
        btn_acc = f"<button class=\"trend-btn\" type=\"button\" data-trend-id=\"trend-acc-full-{i}\">누적 관객 수 추이보기</button>"
        open_dt_raw = r.get("openDt") or ""
        open_dt_display = "-"
        if open_dt_raw:
            try:
                od = dt.datetime.strptime(open_dt_raw, "%Y-%m-%d").date()
                days = (target_date - od).days
                if days >= 0:
                    open_dt_display = f"{open_dt_raw} (+{days}일)"
                else:
                    open_dt_display = open_dt_raw
            except Exception:
                open_dt_display = open_dt_raw
        title_btn = f"<button class=\"movie-info-toggle\" type=\"button\" data-info-id=\"movie-info-{i}\">{name}</button>"
        lines.append(f"| {r['rank']} | {title_btn} | {open_dt_display} | {fmt_int(cur)} | {fmt_int(r['audiAcc'])} | {d1} | {btn_full} {btn_acc} |")

    trend_sections = []
    movie_info_sections = []
    for i, r in enumerate(rows, start=1):
        name = r["movieNm"]

        info = movie_info_map.get(name, {"director": "-", "casts": [], "genres": "-", "nations": "-", "showTm": "-", "watchGrade": "-"})
        cast_rows = "".join(
            [
                f"<tr><td>{(c.get('role') or '-')}</td><td>{c.get('actor')}</td></tr>"
                for c in info.get("casts", [])
                if c.get("actor")
            ]
        )
        if not cast_rows:
            cast_rows = "<tr><td>-</td><td>정보 없음</td></tr>"

        show_tm = info.get("showTm", "-")
        show_tm_text = f"{show_tm}분" if str(show_tm).isdigit() else show_tm

        open_meta = r.get("openDt") or "-"
        days_text = "-"
        try:
            od = dt.datetime.strptime(r.get("openDt", ""), "%Y-%m-%d").date()
            days = (target_date - od).days
            if days >= 0:
                days_text = f"+{days}일"
        except Exception:
            pass

        movie_info_sections.append(
            f"<details class=\"movie-info-details\" id=\"movie-info-{i}\">"
            f"<summary><span class=\"trend-title\">{name} · 상세 정보</span></summary>"
            f"<div class=\"movie-info-wrap\">"
            f"<div class=\"movie-info-meta-grid\">"
            f"<div class=\"meta-item\"><span class=\"meta-label\">감독</span><strong>{info.get('director', '-')}</strong></div>"
            f"<div class=\"meta-item\"><span class=\"meta-label\">장르</span><strong>{info.get('genres', '-')}</strong></div>"
            f"<div class=\"meta-item\"><span class=\"meta-label\">국가</span><strong>{info.get('nations', '-')}</strong></div>"
            f"<div class=\"meta-item\"><span class=\"meta-label\">상영시간</span><strong>{show_tm_text}</strong></div>"
            f"<div class=\"meta-item\"><span class=\"meta-label\">관람등급</span><strong>{info.get('watchGrade', '-')}</strong></div>"
            f"<div class=\"meta-item\"><span class=\"meta-label\">개봉일</span><strong>{open_meta} ({days_text})</strong></div>"
            f"</div>"
            f"<table class=\"trend-table movie-cast-table\">"
            f"<thead><tr><th>배역</th><th>배우명</th></tr></thead>"
            f"<tbody>{cast_rows}</tbody>"
            f"</table>"
            f"</div>"
            f"</details>"
        )

        for kind, detail_id, label in [
            ("full", f"trend-full-{i}", "일 관객 수 추이"),
            ("acc_full", f"trend-acc-full-{i}", "누적 관객 수 추이"),
        ]:
            source_arr = trend_map.get(name, {}).get("full" if kind == "acc_full" else kind, [])

            if kind == "acc_full":
                arr = []
                latest_acc = r.get("audiAcc", 0)
                running = latest_acc - sum(it["audiCnt"] for it in source_arr)
                for it in source_arr:
                    running += it["audiCnt"]
                    arr.append({"date": it["date"], "audiAcc": running})
            else:
                arr = source_arr

            if arr:
                if kind == "acc_full":
                    latest = arr[-1]["audiAcc"]
                    start_val = arr[0]["audiAcc"]
                    growth = latest - start_val
                    body = (
                        f"<div class=\"trend-meta\">"
                        f"<span>최신 <strong>{fmt_int(latest)}명</strong></span>"
                        f"<span>개봉 첫날 <strong>{fmt_int(start_val)}명</strong></span>"
                        f"<span>누적 증가 <strong>{fmt_int(growth)}명</strong></span>"
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

<section class="movie-info-section" style="display:none;">
## 영화별 상세 정보

{chr(10).join(movie_info_sections)}
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
    if not rows:
        rows = load_cached_daily(target_date)

    prev_rows = fetch_daily(prev_date)
    if not prev_rows:
        prev_rows = load_cached_daily(prev_date)

    prev_week_rows = fetch_daily(prev_week_date)
    if not prev_week_rows:
        prev_week_rows = load_cached_daily(prev_week_date)

    prev_map = to_map(prev_rows)
    prev_week_map = to_map(prev_week_rows)

    trend_map = {}
    movie_info_map = {}
    daily_cache = {}
    movie_info_cache = {}
    prev_full_map = load_prev_full_trend(target_date)

    for r in rows:
        name = r["movieNm"]
        movie_cd = r.get("movieCd", "")
        open_dt = r.get("openDt", "")
        today_cnt = r.get("audiCnt", 0)

        prev_full = prev_full_map.get(name)
        if prev_full:
            full_trend = append_today_to_full_trend(prev_full, target_date, today_cnt)
        else:
            full_trend = fetch_full_trend(movie_cd, name, open_dt, target_date, daily_cache)

        trend_map[name] = {
            "week": fetch_7day_trend(movie_cd, name, target_date, daily_cache),
            "full": trim_leading_zeros(full_trend),
        }
        movie_info_map[name] = fetch_movie_info(movie_cd, movie_info_cache)

    csv_path = write_csv(target_date, rows)
    trend_csv_path = write_trend_csv(target_date, trend_map)
    post_path = make_post(target_date, rows, prev_map, prev_week_map, trend_map, movie_info_map)

    print(f"saved: {csv_path}")
    print(f"saved: {trend_csv_path}")
    print(f"saved: {post_path}")


if __name__ == "__main__":
    main()
