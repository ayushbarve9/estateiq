// Print handler for EstateIQ Official Valuation Certificate
document.addEventListener("DOMContentLoaded", () => {
  const btn = document.getElementById("printCertBtn");
  if (btn) {
    btn.addEventListener("click", () => {
      window.print();
    });
  }
});
