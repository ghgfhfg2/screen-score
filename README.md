# Drama & Movie Stats (Jekyll)

드라마/영화 통계형 블로그 기본 세팅입니다.

## 포함된 구성

- Jekyll + Minima 테마
- 기본 페이지 (`/`, `/about`)
- 샘플 포스트 1개
- SEO/Sitemap/Feed 플러그인

## 로컬 실행 (Ruby 설치 후)

```bash
bundle install
bundle exec jekyll serve --livereload
```

브라우저: <http://127.0.0.1:4000>

## 이 환경에서 확인된 점

현재 작업 환경에는 `ruby`, `bundler`, `jekyll`이 설치되어 있지 않아 실제 빌드 실행은 못 했습니다.
설치 후 위 명령으로 바로 실행하면 됩니다.

## 포스터(TMDB) 설정

포스터는 TMDB API를 사용합니다.

```bash
export TMDB_API_KEY="YOUR_TMDB_API_KEY"
python3 scripts/drama_weekly.py
```

GitHub Actions에서는 저장소 `Settings > Secrets and variables > Actions`에
`TMDB_API_KEY` 시크릿을 추가하세요.

## 크론잡 재등록 가이드 (운영용)

크론이 비활성화/유실됐을 때 아래 명령으로 동일하게 재등록하면 됩니다.

### 1) 일일 박스오피스 (매일 12:30, KST)

```bash
openclaw cron add \
  --name "daily-boxoffice-publish" \
  --cron "30 12 * * *" \
  --tz "Asia/Seoul" \
  --session isolated \
  --announce --channel last \
  --message "screen-score 저장소에서 일일 박스오피스 포스트 발행 작업을 수행해줘.
순서:
1) cd /home/sooya/.openclaw/workspace/screen-score
2) python3 scripts/boxoffice_daily.py 실행
3) 변경 파일 git add/commit (메시지: chore: publish daily boxoffice)
4) git push origin main
5) 실행 결과(생성 파일, 커밋해시, 푸시 여부) 요약 보고."
```

### 2) 주간 드라마 시청률 (매주 월요일 11:30, KST)

```bash
openclaw cron add \
  --name "weekly-drama-ratings-publish" \
  --cron "30 11 * * 1" \
  --tz "Asia/Seoul" \
  --session isolated \
  --announce --channel last \
  --message "screen-score 저장소에서 드라마 주간 포스트 발행 작업을 수행해줘.
순서:
1) cd /home/sooya/.openclaw/workspace/screen-score
2) python3 scripts/drama_weekly.py 실행
3) 변경 파일 git add/commit (메시지: chore: publish weekly drama ratings)
4) git push origin main
5) 실행 결과(생성 파일, 커밋해시, 푸시 여부) 요약 보고."
```

### 운영 팁

- 중복 등록 방지: `openclaw cron list --all`로 기존 동일 이름 확인 후 등록
- 비활성 잡 활성화: `openclaw cron enable <job-id>`
- 즉시 테스트 실행: `openclaw cron run <job-id>`

## 일일 박스오피스 게시글 작성 가이드 (운영 메모)

`daily-boxoffice` 포스트 작성/백필 시 추이 데이터는 아래 원칙을 따른다.

1. **일 관객 수 추이(`trend-full`)**
   - 개봉 첫날 데이터만 신규 생성하고,
   - 그 외 날짜는 **직전 게시물의 동일 영화 추이 테이블을 그대로 이어받아** 당일 `audiCnt`만 append 한다.

2. **누적 관객 수 추이(`trend-acc-full`)**
   - 기본적으로 **직전 게시물의 동일 영화 누적 추이 테이블을 기준**으로,
   - 당일 `audiAcc`만 append 한다.

3. **신규 진입 영화 처리**
   - 직전 게시물에 동일 영화가 없으면 해당 날짜부터 새 추이 블록을 시작한다.

4. **백필(누락일 복구) 시 우선순위**
   - 정확한 연속성(전일 히스토리 + 당일 append)을 최우선으로 한다.
   - 임시 7일 추이 등 축약 포맷은 긴급 복구용으로만 사용하고, 최종본은 연속 히스토리 기준으로 교체한다.

## 다음 단계(기획 반영)

기획 주시면 아래를 순서대로 붙일게요.

1. 카테고리/태그 체계 설계
2. 통계용 포스트 템플릿(표/차트)
3. 데이터 파일 구조(`_data/*.yml` 혹은 CSV 기반)
4. 홈/카테고리 페이지 커스터마이징
5. GitHub Pages 배포 세팅 확정
