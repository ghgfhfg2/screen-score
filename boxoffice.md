---
layout: page
title: 박스오피스 목록
permalink: /boxoffice/
---

{% assign movie_posts = site.posts | where_exp: "p", "p.categories contains 'boxoffice'" %}

<ul class="post-list">
  {% for post in movie_posts %}
    <li>
      <span class="post-meta">{{ post.date | date: "%Y-%m-%d" }}</span>
      <h3><a class="post-link" href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    </li>
  {% endfor %}
</ul>
