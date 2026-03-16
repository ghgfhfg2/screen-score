---
layout: page
title: 드라마 시청률 목록
permalink: /drama-ratings/
---

{% assign drama_posts = site.posts | where_exp: "p", "p.categories contains 'drama-ratings'" %}

<ul id="category-post-list" class="post-list paged-post-list">
  {% for post in drama_posts %}
    <li class="paged-item">
      <span class="post-meta">{{ post.date | date: "%Y-%m-%d" }}</span>
      <h3><a class="post-link" href="{{ post.url | relative_url }}">{{ post.title }}</a></h3>
    </li>
  {% endfor %}
</ul>

<div id="category-pagination" class="category-pagination"></div>

<script>
  (function () {
    const list = document.getElementById('category-post-list');
    const pager = document.getElementById('category-pagination');
    if (!list || !pager) return;

    const items = Array.from(list.querySelectorAll('.paged-item'));
    const perPage = 10;
    const totalPages = Math.max(1, Math.ceil(items.length / perPage));
    let currentPage = 1;

    function render() {
      items.forEach((item, idx) => {
        const page = Math.floor(idx / perPage) + 1;
        item.style.display = page === currentPage ? '' : 'none';
      });

      pager.innerHTML = '';
      if (totalPages <= 1) return;

      const prev = document.createElement('button');
      prev.className = 'pager-btn';
      prev.textContent = '← 이전';
      prev.disabled = currentPage === 1;
      prev.onclick = () => { currentPage--; render(); window.scrollTo({ top: 0, behavior: 'smooth' }); };
      pager.appendChild(prev);

      for (let p = 1; p <= totalPages; p++) {
        const btn = document.createElement('button');
        btn.className = 'pager-btn' + (p === currentPage ? ' is-active' : '');
        btn.textContent = p;
        btn.onclick = () => { currentPage = p; render(); window.scrollTo({ top: 0, behavior: 'smooth' }); };
        pager.appendChild(btn);
      }

      const next = document.createElement('button');
      next.className = 'pager-btn';
      next.textContent = '다음 →';
      next.disabled = currentPage === totalPages;
      next.onclick = () => { currentPage++; render(); window.scrollTo({ top: 0, behavior: 'smooth' }); };
      pager.appendChild(next);
    }

    render();
  })();
</script>
