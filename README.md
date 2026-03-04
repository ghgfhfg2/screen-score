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

## 다음 단계(기획 반영)

기획 주시면 아래를 순서대로 붙일게요.

1. 카테고리/태그 체계 설계
2. 통계용 포스트 템플릿(표/차트)
3. 데이터 파일 구조(`_data/*.yml` 혹은 CSV 기반)
4. 홈/카테고리 페이지 커스터마이징
5. GitHub Pages 배포 세팅 확정
