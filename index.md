---
layout: home
title: 홈
---

<section class="hero-panel">
  <p class="hero-kicker">DRAMA · MOVIE · DATA</p>
  <h1>드라마/영화 데이터를<br />한눈에 보는 통계 대시보드</h1>
  <p class="hero-desc">시청률, 박스오피스, 추이 차트를 트렌디한 카드형 UI로 빠르게 탐색하세요.</p>
  <div class="hero-stats">
    <div class="stat-card">
      <span class="stat-label">전체 포스트</span>
      <strong class="stat-value">{{ site.posts.size }}</strong>
    </div>
    <div class="stat-card">
      <span class="stat-label">드라마 카테고리</span>
      <strong class="stat-value">{{ site.categories['drama-ratings'].size | default: 0 }}</strong>
    </div>
    <div class="stat-card">
      <span class="stat-label">영화 카테고리</span>
      <strong class="stat-value">{{ site.categories['boxoffice'].size | default: 0 }}</strong>
    </div>
  </div>
</section>

<section class="category-block category-drama">
  <div class="category-head">
    <h2>📺 드라마 카테고리</h2>
    <span class="category-chip">Drama</span>
  </div>
  <div class="post-grid">
    {% assign drama_posts = site.posts | where_exp: "p", "p.categories contains 'drama-ratings'" %}
    {% if drama_posts.size > 0 %}
      {% for post in drama_posts limit: 6 %}
      <a class="post-card" href="{{ post.url | relative_url }}">
        <p class="post-card-meta">{{ post.date | date: "%Y-%m-%d" }}</p>
        <h3>{{ post.title }}</h3>
        <p class="post-card-desc">{{ post.excerpt | strip_html | truncate: 92 }}</p>
      </a>
      {% endfor %}
    {% else %}
      <p class="empty-note">아직 드라마 데이터 포스트가 없습니다.</p>
    {% endif %}
  </div>
</section>

<section class="category-block category-movie">
  <div class="category-head">
    <h2>🎬 영화 카테고리</h2>
    <span class="category-chip">Movie</span>
  </div>
  <div class="post-grid">
    {% assign movie_posts = site.posts | where_exp: "p", "p.categories contains 'boxoffice'" %}
    {% if movie_posts.size > 0 %}
      {% for post in movie_posts limit: 6 %}
      <a class="post-card" href="{{ post.url | relative_url }}">
        <p class="post-card-meta">{{ post.date | date: "%Y-%m-%d" }}</p>
        <h3>{{ post.title }}</h3>
        <p class="post-card-desc">{{ post.excerpt | strip_html | truncate: 92 }}</p>
      </a>
      {% endfor %}
    {% else %}
      <p class="empty-note">아직 영화 데이터 포스트가 없습니다.</p>
    {% endif %}
  </div>
</section>
