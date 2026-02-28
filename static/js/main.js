document.addEventListener("DOMContentLoaded", () => {
  // Animate ring percentages on load
  document.querySelectorAll(".ss-ring-svg").forEach((svg) => {
    const value = parseFloat(svg.getAttribute("data-value") || "0");
    const progress = svg.querySelector(".ss-ring-progress");
    if (!progress) return;
    requestAnimationFrame(() => {
      progress.style.strokeDasharray = `${Math.min(value, 100)}, 100`;
    });
  });

  // Smooth scroll for hash links
  document.querySelectorAll('a[href^="#"]').forEach((link) => {
    link.addEventListener("click", (e) => {
      const targetId = link.getAttribute("href") || "";
      const el = document.querySelector(targetId);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
});

