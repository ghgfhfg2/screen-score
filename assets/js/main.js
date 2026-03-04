document.addEventListener("DOMContentLoaded", () => {
  const allRows = document.querySelectorAll("table tbody tr");
  const details = document.querySelectorAll(".trend-details");

  // 메인 통합 테이블 찾기
  const tables = Array.from(document.querySelectorAll("table"));
  const mainTable = tables.find((t) =>
    (t.querySelector("thead th")?.textContent || "").includes("통합순위")
  );

  if (mainTable) {
    setupMainTableControls(mainTable);
  }

  // 드라마별 추이 차트 생성
  if (window.Chart) {
    details.forEach((detail) => buildTrendChart(detail));
  }

  if (window.gsap) {
    gsap.from(".post-title, .page-heading", {
      y: 10,
      opacity: 0,
      duration: 0.35,
      ease: "power1.out"
    });

    gsap.from(allRows, {
      opacity: 0,
      duration: 0.22,
      stagger: 0.02,
      delay: 0.05,
      ease: "none"
    });
  }

  details.forEach((el) => {
    el.addEventListener("toggle", () => {
      if (!el.open || !window.gsap) return;
      const body = el.querySelector(".trend-meta, .trend-chart-wrap, .trend-table-wrap, .trend-empty");
      if (!body) return;
      gsap.from(body, { opacity: 0, y: 6, duration: 0.22, ease: "power1.out" });
    });
  });
});

function setupMainTableControls(mainTable) {
  const rows = Array.from(mainTable.querySelectorAll("tbody tr"));
  if (!rows.length) return;

  const channels = [...new Set(rows.map((r) => r.children[2]?.textContent?.trim()).filter(Boolean))];

  const controls = document.createElement("div");
  controls.className = "trend-controls";
  controls.innerHTML = `
    <input type="text" class="trend-search" placeholder="제목 검색" />
    <select class="trend-channel-filter">
      <option value="">전체 채널</option>
      ${channels.map((c) => `<option value="${c}">${c}</option>`).join("")}
    </select>
  `;

  mainTable.parentNode.insertBefore(controls, mainTable);

  const searchInput = controls.querySelector(".trend-search");
  const channelSelect = controls.querySelector(".trend-channel-filter");

  const applyFilter = () => {
    const q = searchInput.value.trim().toLowerCase();
    const ch = channelSelect.value;

    rows.forEach((row) => {
      const title = row.children[3]?.textContent?.trim().toLowerCase() || "";
      const channel = row.children[2]?.textContent?.trim() || "";
      const okQ = !q || title.includes(q);
      const okCh = !ch || channel === ch;
      row.style.display = okQ && okCh ? "" : "none";
    });
  };

  searchInput.addEventListener("input", applyFilter);
  channelSelect.addEventListener("change", applyFilter);
}

function buildTrendChart(detail) {
  const table = detail.querySelector(".trend-table");
  if (!table) return;

  const rows = Array.from(table.querySelectorAll("tbody tr"));
  if (!rows.length) return;

  const labels = rows.map((r) => r.children[0]?.textContent?.trim() || "");
  const data = rows.map((r) => Number(r.children[2]?.textContent?.trim() || 0));

  const wrap = document.createElement("div");
  wrap.className = "trend-chart-wrap";
  wrap.innerHTML = `<canvas height="120"></canvas>`;
  table.parentNode.insertBefore(wrap, table);

  const ctx = wrap.querySelector("canvas");
  new Chart(ctx, {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          data,
          borderColor: "#3451b2",
          backgroundColor: "rgba(52,81,178,0.12)",
          pointRadius: 2,
          pointHoverRadius: 3,
          borderWidth: 2,
          tension: 0.3,
          fill: true
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
        y: { grid: { color: "#eef2fb" }, ticks: { callback: (v) => `${v}%` } }
      }
    }
  });
}
