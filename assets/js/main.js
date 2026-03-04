document.addEventListener("DOMContentLoaded", () => {
  const rows = document.querySelectorAll("table tbody tr");
  const details = document.querySelectorAll(".trend-details");

  if (window.gsap) {
    gsap.from(".post-title, .page-heading", {
      y: 10,
      opacity: 0,
      duration: 0.35,
      ease: "power1.out"
    });

    gsap.from(rows, {
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
      const body = el.querySelector(".trend-meta, .trend-table-wrap, .trend-empty");
      if (!body) return;
      gsap.from(body, { opacity: 0, y: 6, duration: 0.22, ease: "power1.out" });
    });
  });
});
