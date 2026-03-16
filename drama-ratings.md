---
layout: page
title: 드라마 시청률 목록
permalink: /drama-ratings/
---

{% assign drama_posts = site.posts | where_exp: "p", "p.categories contains 'drama-ratings'" %}

<ul class="post-list">
  {% for post in drama_posts %}
    <li>
      <span class="post-meta">{{ post.date | date: "%Y-%m-%d" }}</span>
      <h3><a class="post-link" href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    </li>
  {% endfor %}
</ul>
