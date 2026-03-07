document.addEventListener("DOMContentLoaded", () => {
  const allRows = document.querySelectorAll("table tbody tr");
  const details = document.querySelectorAll(".trend-details");

  const tables = Array.from(document.querySelectorAll("table"));
  const mainTable = tables.find((t) => {
    const headText = Array.from(t.querySelectorAll("thead th")).map((th) => th.textContent || "").join(" ");
    return headText.includes("시청률 추이") || headText.includes("박스오피스 추이");
  });

  if (mainTable) {
    setupMainTableControls(mainTable);
    setupInlineTrendAccordion(mainTable);
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

  const ths = Array.from(mainTable.querySelectorAll("thead th")).map((th) => (th.textContent || "").trim());
  const titleIdx = ths.findIndex((t) => t === "제목");
  const channelIdx = ths.findIndex((t) => t === "채널");
  if (titleIdx < 0 || channelIdx < 0) return;

  const channels = [...new Set(rows.map((r) => r.children[channelIdx]?.textContent?.trim()).filter(Boolean))];

  const hasMeaningfulChannelFilter = channels.length > 1;

  const controls = document.createElement("div");
  controls.className = "trend-controls";
  controls.innerHTML = `
    <input type="text" class="trend-search" placeholder="제목 검색" />
    ${hasMeaningfulChannelFilter ? `<select class="trend-channel-filter">
      <option value="">전체 채널</option>
      ${channels.map((c) => `<option value="${c}">${c}</option>`).join("")}
    </select>` : ""}
  `;

  mainTable.parentNode.insertBefore(controls, mainTable);

  const searchInput = controls.querySelector(".trend-search");
  const channelSelect = controls.querySelector(".trend-channel-filter");

  const applyFilter = () => {
    const q = searchInput.value.trim().toLowerCase();
    const ch = channelSelect ? channelSelect.value : "";

    rows.forEach((row) => {
      const title = row.children[titleIdx]?.textContent?.trim().toLowerCase() || "";
      const channel = row.children[channelIdx]?.textContent?.trim() || "";
      const okQ = !q || title.includes(q);
      const okCh = !ch || channel === ch;
      row.style.display = okQ && okCh ? "" : "none";

      const next = row.nextElementSibling;
      if (next && next.classList.contains("inline-trend-row") && row.style.display === "none") {
        next.remove();
        row.classList.remove("is-expanded");
      }
    });
  };

  searchInput.addEventListener("input", applyFilter);
  if (channelSelect) {
    channelSelect.addEventListener("change", applyFilter);
  }
}

function setupInlineTrendAccordion(mainTable) {
  const bodyRows = Array.from(mainTable.querySelectorAll("tbody tr"));

  bodyRows.forEach((row) => {
    const btns = Array.from(row.querySelectorAll(".trend-btn"));
    if (!btns.length) return;

    btns.forEach((btn) => {
      btn.addEventListener("click", () => {
        const trendId = btn.getAttribute("data-trend-id");
        const source = document.getElementById(trendId);
        if (!source) return;

        const alreadyOpen = row.classList.contains("is-expanded") && row.dataset.openTrendId === trendId;
        closeAllInlineTrendRows(mainTable);
        if (alreadyOpen) return;

        const colCount = row.children.length;
        const inlineRow = document.createElement("tr");
        inlineRow.className = "inline-trend-row";
        inlineRow.innerHTML = `<td colspan="${colCount}"></td>`;

        const cell = inlineRow.firstElementChild;
        const title = source.querySelector(".trend-title")?.textContent?.trim() || "추이";
        const metaHtml = source.querySelector(".trend-meta")?.outerHTML || "";
        const tableEl = source.querySelector(".trend-table");
        const emptyHtml = "<p class='trend-empty'>추이 데이터를 제공하지 않습니다.</p>";

        cell.innerHTML = `
          <div class="inline-trend-card">
            <div class="inline-trend-head">${title}</div>
            ${tableEl ? metaHtml : ""}
            ${tableEl ? '<div class="trend-chart-wrap"><canvas height="120"></canvas></div>' : emptyHtml}
          </div>
        `;

        row.insertAdjacentElement("afterend", inlineRow);
        row.classList.add("is-expanded");
        row.dataset.openTrendId = trendId;

        const canvas = inlineRow.querySelector("canvas");
        if (canvas && tableEl && window.Chart) {
          buildTrendChartFromTable(canvas, tableEl);
        }

        if (window.gsap) {
          gsap.from(inlineRow.querySelector(".inline-trend-card"), {
            y: 8,
            opacity: 0,
            duration: 0.2,
            ease: "power1.out"
          });
        }
      });
    });
  });
}

function closeAllInlineTrendRows(mainTable) {
  mainTable.querySelectorAll("tbody tr.inline-trend-row").forEach((r) => r.remove());
  mainTable.querySelectorAll("tbody tr.is-expanded").forEach((r) => {
    r.classList.remove("is-expanded");
    delete r.dataset.openTrendId;
  });
}

function buildTrendChartFromTable(canvas, table) {
  const rows = Array.from(table.querySelectorAll("tbody tr"));
  if (!rows.length) return;

  const thText = Array.from(table.querySelectorAll("thead th")).map((th) => (th.textContent || "").trim());
  const valueIdx = Math.max(1, thText.length - 1); // 보통 마지막 열이 값
  const isPercent = thText.join(" ").includes("시청률");

  const labels = rows.map((r) => r.children[0]?.textContent?.trim() || "");
  const data = rows.map((r) => {
    const raw = r.children[valueIdx]?.textContent?.trim() || "0";
    return Number(raw.replace(/,/g, "")) || 0;
  });

  new Chart(canvas, {
    type: "line",
    data: {
      labels,
      datasets: [{
        data,
        borderColor: "#3451b2",
        backgroundColor: "rgba(52,81,178,0.12)",
        pointRadius: 0,
        pointHoverRadius: 4,
        pointHitRadius: 24,
        borderWidth: 2,
        tension: 0.3,
        cubicInterpolationMode: "monotone",
        fill: true
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        mode: "index",
        intersect: false
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          mode: "index",
          intersect: false,
          callbacks: {
            label: (ctx) => {
              const v = Number(ctx.parsed.y || 0);
              return isPercent ? ` ${v}%` : ` ${v.toLocaleString()}명`;
            }
          }
        }
      },
      scales: {
        x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true, maxTicksLimit: 8 } },
        y: {
          min: 0,
          grid: { color: "#eef2fb" },
          ticks: {
            callback: (v) => isPercent ? `${v}%` : `${Number(v).toLocaleString()}명`
          }
        }
      }
    }
  });
}
