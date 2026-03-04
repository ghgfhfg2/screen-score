document.addEventListener("DOMContentLoaded", () => {
  const rows = document.querySelectorAll("table tbody tr");
  const cards = document.querySelectorAll("details");

  if (window.gsap) {
    gsap.from(".post-title, .page-heading", {
      y: 18,
      opacity: 0,
      duration: 0.6,
      ease: "power2.out"
    });

    gsap.from(rows, {
      y: 14,
      opacity: 0,
      duration: 0.4,
      stagger: 0.04,
      delay: 0.15,
      ease: "power2.out"
    });

    gsap.from(cards, {
      y: 10,
      opacity: 0,
      duration: 0.35,
      stagger: 0.03,
      delay: 0.2,
      ease: "power1.out"
    });
  }
});
