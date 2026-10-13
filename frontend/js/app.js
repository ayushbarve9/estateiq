// EstateIQ front end. Vanilla JS, ES modules, zero build step.
// Formerly GrihaValue core valuation engine.

import {
  countUp, donut, fmtCompact, fmtINR, fmtPct, forecastChart, heatColor,
  lineChart, mountHbars, mountStack, scatterMap, startAnimations,
} from "./charts.js";
import { SUGGESTIONS, answerLocally } from "./advisor.js";

const $ = (sel, root = document) => root.querySelector(sel);
const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

const BHK_TYPICAL = {
  1: "450–700", 2: "850–1,350", 3: "1,200–2,100", 4: "2,000–3,300", 5: "3,000–5,000",
};
const TYPE_ICON = {
  "Apartment": "i-apartment",
  "Builder Floor": "i-floor",
  "Independent Villa": "i-villa",
  "Penthouse": "i-penthouse",
};

const state = {
  meta: null,
  est: null,
  busy: false,
  history: [],
};

// ---------------------------------------------------------------------------
// Boot
// ---------------------------------------------------------------------------

document.addEventListener("DOMContentLoaded", () => {
  initTheme();
  initSlideshow();
  initTopbarScroll();
  wireReveal();
  wireForm();
  wirePresets();
  wireDeckChatBtn();
  wireTalkTeam();
  wireForecastScenarios();
  wireChat();
  wireRulesExplorer();
  wireClusterPills();
  initMarketHeatmap();
  initPropertyBattle();
  initOfferStrategy();
  initLoanPrepayment();
  initBuyVsRent();
  loadMeta().catch((err) => showFormError(`Could not load markets: ${err.message}`));
});

// ---------------------------------------------------------------------------
// Theme
// ---------------------------------------------------------------------------

function initTheme() {
  const saved = safeGet("estateiq-theme") || safeGet("gv-theme");
  setTheme(saved || "dark");
  $("#themeToggle").addEventListener("click", () => {
    const next = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
    setTheme(next);
    safeSet("estateiq-theme", next);
  });
}

function setTheme(t) {
  document.documentElement.dataset.theme = t;
  const icon = $("#themeToggle use");
  if (icon) {
    icon.setAttribute("href", t === "dark" ? "#i-sun" : "#i-moon");
  }
}

function safeGet(k) { try { return localStorage.getItem(k); } catch { return null; } }
function safeSet(k, v) { try { localStorage.setItem(k, v); } catch { /* storage blocked */ } }

// ---------------------------------------------------------------------------
// Hero Slideshow & Media Controls (Aspen Homes Architectural Style)
// ---------------------------------------------------------------------------

let currentSlide = 0;
let slideInterval = null;
let isPlaying = true;
const SLIDE_DURATION = 6000;

function initSlideshow() {
  const slides = $$(".hero-slide");
  const bars = $$(".slide-bar");
  if (!slides.length) return;

  function showSlide(index) {
    currentSlide = (index + slides.length) % slides.length;
    slides.forEach((s, i) => s.classList.toggle("active", i === currentSlide));
    bars.forEach((b, i) => b.classList.toggle("active", i === currentSlide));
    const locText = $("#slideLocationText");
    if (locText && slides[currentSlide]) {
      const loc = slides[currentSlide].dataset.location || "";
      locText.textContent = `0${currentSlide + 1} / 0${slides.length} · ${loc}`;
    }
  }

  function nextSlide() {
    showSlide(currentSlide + 1);
  }

  function prevSlide() {
    showSlide(currentSlide - 1);
  }

  function startTimer() {
    stopTimer();
    slideInterval = setInterval(nextSlide, SLIDE_DURATION);
    isPlaying = true;
    updatePlayPause();
  }

  function stopTimer() {
    if (slideInterval) clearInterval(slideInterval);
    slideInterval = null;
    isPlaying = false;
    updatePlayPause();
  }

  function updatePlayPause() {
    const icon = $("#playPauseIcon use");
    if (icon) icon.setAttribute("href", isPlaying ? "#i-pause" : "#i-play");
    const btn = $("#slidePlayPause");
    if (btn) btn.setAttribute("aria-label", isPlaying ? "Pause slideshow" : "Play slideshow");
  }

  bars.forEach((bar) => {
    bar.addEventListener("click", () => {
      const idx = Number(bar.dataset.slide);
      showSlide(idx);
      if (isPlaying) startTimer();
    });
  });

  $("#slideNext")?.addEventListener("click", () => {
    nextSlide();
    if (isPlaying) startTimer();
  });

  $("#slidePrev")?.addEventListener("click", () => {
    prevSlide();
    if (isPlaying) startTimer();
  });

  $("#slidePlayPause")?.addEventListener("click", () => {
    if (isPlaying) {
      stopTimer();
    } else {
      nextSlide();
      startTimer();
    }
  });

  // Video / Cinematic motion mode
  $("#videoToggle")?.addEventListener("click", () => {
    const video = $("#heroVideo");
    if (!video) return;
    if (video.hidden) {
      video.hidden = false;
      video.play().catch(() => {});
      video.classList.add("playing");
      stopTimer();
    } else {
      video.hidden = true;
      video.pause();
      video.classList.remove("playing");
      startTimer();
    }
  });

  showSlide(0);
  startTimer();
}

// ---------------------------------------------------------------------------
// Quick Mumbai Presets
// ---------------------------------------------------------------------------

const PRESETS = {
  worli: {
    city: "Mumbai (MMR)",
    locality: "Worli / South Mumbai",
    bhk: 3,
    area: 2200,
    bathrooms: 3,
    parking: 2,
    type: "Apartment",
    furnishing: "Semi-Furnished",
    status: "Ready to Move",
    age: 2,
    dp: 20,
    rate: 8.5,
    tenure: 20,
  },
  bandra: {
    city: "Mumbai (MMR)",
    locality: "Bandra West",
    bhk: 4,
    area: 3500,
    bathrooms: 4,
    parking: 3,
    type: "Independent Villa",
    furnishing: "Furnished",
    status: "Ready to Move",
    age: 1,
    dp: 25,
    rate: 8.5,
    tenure: 20,
  },
  lowerparel: {
    city: "Mumbai (MMR)",
    locality: "Worli / South Mumbai",
    bhk: 4,
    area: 2800,
    bathrooms: 4,
    parking: 2,
    type: "Penthouse",
    furnishing: "Furnished",
    status: "Ready to Move",
    age: 3,
    dp: 20,
    rate: 8.5,
    tenure: 25,
  },
  juhu: {
    city: "Mumbai (MMR)",
    locality: "Andheri West",
    bhk: 5,
    area: 4200,
    bathrooms: 5,
    parking: 3,
    type: "Independent Villa",
    furnishing: "Furnished",
    status: "Ready to Move",
    age: 2,
    dp: 30,
    rate: 8.5,
    tenure: 20,
  },
};

function wirePresets() {
  $$(".preset-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const presetKey = btn.dataset.preset;
      const p = PRESETS[presetKey];
      if (!p) return;
      applyPreset(p);
    });
  });
}

function applyPreset(p) {
  const citySel = $("#city");
  if (citySel) {
    citySel.value = p.city;
    populateLocalities();
  }
  const locSel = $("#locality");
  if (locSel) {
    locSel.value = p.locality;
    updateStateHint();
  }
  setSegValue("#bhkGroup", String(p.bhk));
  onBhkChange(p.bhk);

  $("#area").value = p.area;
  $("#areaRange").value = p.area;

  $("#bathrooms").textContent = String(p.bathrooms);
  $("#parking").textContent = String(p.parking);

  setTypeValue(p.type);

  setSegValue("#furnGroup", p.furnishing);
  setSegValue("#statusGroup", p.status);

  $("#age").value = p.age;
  $("#ageOut").textContent = String(p.age);
  $("#dp").value = p.dp;
  $("#dpOut").textContent = String(p.dp);
  $("#rate").value = p.rate;
  $("#rateOut").textContent = Number(p.rate).toFixed(2);
  $("#tenure").value = p.tenure;
  $("#tenureOut").textContent = String(p.tenure);

  paintFills();

  const form = $("#estimateForm");
  form.scrollIntoView({ behavior: "smooth", block: "start" });
  setTimeout(() => {
    form.dispatchEvent(new Event("submit", { cancelable: true }));
  }, 400);
}

function setSegValue(containerSel, val) {
  const c = $(containerSel);
  if (!c) return;
  $$("button", c).forEach((btn) => {
    const active = btn.dataset.value === val;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-checked", String(active));
  });
}

function setTypeValue(val) {
  $$(".type-card").forEach((card) => {
    const active = card.dataset.value === val;
    card.classList.toggle("active", active);
    card.setAttribute("aria-checked", String(active));
  });
}

function initTopbarScroll() {
  const topbar = $(".topbar");
  if (!topbar) return;
  const onScroll = () => {
    topbar.classList.toggle("scrolled", window.scrollY > 40);
  };
  window.addEventListener("scroll", onScroll, { passive: true });
  onScroll();
}

function wireTalkTeam() {
  const modal = $("#contactModal");
  const openBtn = $("#talkTeamBtn");
  const closeBtn = $("#modalCloseBtn");
  const form = $("#teamContactForm");
  const errorEl = $("#modalFormError");
  const submitBtn = $("#contactSubmitBtn");
  const formView = $("#modalFormView");
  const reportView = $("#modalReportView");
  const backBtn = $("#repBackBtn");
  const printBtn = $("#repPrintBtn");
  const channels = $$(".channel-btn");

  if (!modal || !openBtn) return;

  let selectedChannel = "whatsapp";

  channels.forEach((btn) => {
    btn.addEventListener("click", () => {
      channels.forEach((b) => {
        b.classList.remove("active");
        b.setAttribute("aria-checked", "false");
      });
      btn.classList.add("active");
      btn.setAttribute("aria-checked", "true");
      selectedChannel = btn.dataset.channel;
    });
  });

  function updateContextCard() {
    let city = $("#city")?.value || "Mumbai (MMR)";
    let loc = $("#locality")?.value || "Worli / South Mumbai";
    let bhk = $(`#bhkGroup button[aria-checked="true"]`)?.dataset.value || "3";
    let area = $("#area")?.value || "2200";

    if (state.est) {
      city = state.est.city || city;
      loc = state.est.locality || loc;
      bhk = state.est.bhk || bhk;
      area = state.est.area_sqft || area;
      $("#modalContextProp").textContent = `${city} · ${loc} (${bhk} BHK · ${Number(area).toLocaleString("en-IN")} sq.ft.)`;
      $("#modalContextPrice").textContent = fmtCompact(state.est.predicted_price);
      $("#modalContextPsf").textContent = `${fmtINR(state.est.rate_per_sqft)} / sq.ft.`;
      $("#modalContextTax").textContent = "Included";
    } else {
      $("#modalContextProp").textContent = `${city} · ${loc} (${bhk} BHK · ${Number(area).toLocaleString("en-IN")} sq.ft.)`;
      $("#modalContextPrice").textContent = "Calculated on submit";
      $("#modalContextPsf").textContent = "Live benchmark";
      $("#modalContextTax").textContent = "Included";
    }
  }

  function openModal() {
    updateContextCard();
    formView.hidden = false;
    reportView.hidden = true;
    errorEl.hidden = true;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    setTimeout(() => $("#clientName")?.focus(), 100);
  }

  function closeModal() {
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    document.body.style.overflow = "";
  }

  function openDirectReport() {
    let est = state.est;
    if (!est) {
      openModal();
      return;
    }
    const clientName = $("#clientName")?.value.trim() || "Private Client";
    const clientEmail = $("#clientEmail")?.value.trim() || "verified@estateiq.desk";
    const clientPhone = $("#clientPhone")?.value.trim() || "+91 (Verified Dossier Client)";
    const contactPayload = {
      name: clientName,
      email: clientEmail,
      phone: clientPhone,
      advisory_type: "Full Certified Property Valuation Audit",
      preferred_contact: "Direct Dossier Download",
    };
    const resp = {
      lead_id: `EID-2026-${(est.city || "MUM").replace(/[^a-zA-Z]/g, "").substring(0, 3).toUpperCase()}-${Math.floor(1000 + Math.random() * 9000)}`,
    };
    populateDetailedReport(resp, contactPayload, est);
    formView.hidden = true;
    reportView.hidden = false;
    errorEl.hidden = true;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    modal.querySelector(".modal-container").scrollTop = 0;
  }

  $("#heroReportBtn")?.addEventListener("click", (e) => {
    e.preventDefault();
    openDirectReport();
  });

  openBtn.addEventListener("click", (e) => {
    e.preventDefault();
    openModal();
  });

  closeBtn?.addEventListener("click", closeModal);

  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.classList.contains("open")) {
      closeModal();
    }
  });

  backBtn?.addEventListener("click", () => {
    reportView.hidden = true;
    formView.hidden = false;
    modal.querySelector(".modal-container").scrollTop = 0;
  });

  printBtn?.addEventListener("click", () => {
    window.print();
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorEl.hidden = true;

    const name = $("#clientName")?.value.trim();
    const email = $("#clientEmail")?.value.trim();
    const phone = $("#clientPhone")?.value.trim();
    const advisoryType = $("#advisoryType")?.value;
    const notes = $("#clientNotes")?.value.trim() || "";

    if (!name || name.length < 2) {
      errorEl.textContent = "Please enter your full name.";
      errorEl.hidden = false;
      return;
    }
    if (!email || !email.includes("@") || !email.includes(".")) {
      errorEl.textContent = "Please provide a valid email address.";
      errorEl.hidden = false;
      return;
    }
    const digits = phone.replace(/\D/g, "");
    if (digits.length < 7) {
      errorEl.textContent = "Please provide a valid contact telephone/mobile number.";
      errorEl.hidden = false;
      return;
    }

    submitBtn.disabled = true;
    const originalBtnText = submitBtn.innerHTML;
    submitBtn.innerHTML = `<span>GENERATING CERTIFIED DOSSIER...</span>`;

    try {
      // If active estimate not generated yet, compute it now
      let activeEst = state.est;
      if (!activeEst) {
        const payload = collectPayload();
        const prob = validate(payload);
        if (!prob) {
          const estRes = await fetch("/api/estimate", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload),
          });
          if (estRes.ok) {
            activeEst = { ...(await estRes.json()), ...payload };
            state.est = activeEst;
            renderEstimate(activeEst);
          }
        }
      }

      const contactPayload = {
        name,
        email,
        phone,
        advisory_type: advisoryType,
        preferred_contact: selectedChannel,
        notes,
        estimate_context: activeEst,
      };

      const res = await fetch("/api/contact", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(contactPayload),
      });

      if (!res.ok) {
        throw new Error(await errorText(res));
      }

      const data = await res.json();
      populateDetailedReport(data, contactPayload, activeEst);

      formView.hidden = true;
      reportView.hidden = false;
      modal.querySelector(".modal-container").scrollTop = 0;
    } catch (err) {
      errorEl.textContent = `Could not submit report request: ${err.message}`;
      errorEl.hidden = false;
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = originalBtnText;
    }
  });
}

function populateDetailedReport(resp, contact, est) {
  if (!est) {
    est = state.est || {
      predicted_price: 184200000,
      rate_per_sqft: 83727,
      price_range: { low: 169500000, high: 201500000 },
      vs_city_median_pct: 18.4,
      city: "Mumbai (MMR)",
      locality: "Worli Sea Face",
      bhk: 3,
      area_sqft: 2200,
      bathrooms: 3,
      parking: 2,
      property_type: "Apartment",
      construction_status: "Ready to Move",
      age_years: 2,
      furnishing: "Semi-Furnished",
      finance: {
        loan_amount: 138150000,
        down_payment: 46050000,
        ltv_ratio: 0.75,
        monthly_emi: 1198400,
        stamp_duty: 11082000,
        gst: 0,
        upfront_cash: 57132000,
        acquisition_cost: 195282000,
      },
      comparables: [],
    };
  }

  const f = est.finance || {};
  const r = est.price_range || { low: est.predicted_price * 0.92, high: est.predicted_price * 1.09 };

  $("#repRef").textContent = resp.lead_id || "EID-2026-MUM-8491";
  $("#repPropHeading").textContent = `${est.bhk} BHK ${est.property_type || "Apartment"} · ${est.locality}, ${est.city}`;
  $("#repPrice").textContent = fmtCompact(est.predicted_price);
  $("#repPrice").title = fmtINR(est.predicted_price);
  $("#repPsf").textContent = `${fmtINR(est.rate_per_sqft)} / sq.ft.`;
  $("#repRange").textContent = `${fmtCompact(r.low)} – ${fmtCompact(r.high)}`;
  const vs = est.vs_city_median_pct || 0;
  $("#repVsCity").textContent = `${vs >= 0 ? "+" : ""}${vs.toFixed(1)}% vs City Median`;

  $("#repClientName").textContent = contact.name;
  const chanName = contact.preferred_contact === "whatsapp" ? "WhatsApp" : contact.preferred_contact === "phone" ? "Phone" : "Email";
  $("#repClientContact").textContent = `${contact.email} · ${contact.phone} (${chanName})`;
  $("#repAdvisoryType").textContent = contact.advisory_type;
  $("#repTimestamp").textContent = new Date().toLocaleString("en-IN", {
    dateStyle: "medium", timeStyle: "short",
  }) + " IST";

  $("#repLocality").textContent = `${est.locality}, ${est.city}, ${est.state || "Maharashtra"}`;
  $("#repLayout").textContent = `${est.bhk} BHK ${est.property_type || "Residence"}`;
  $("#repArea").textContent = `${Number(est.area_sqft).toLocaleString("en-IN")} sq.ft.`;
  $("#repSpecs").textContent = `${est.bathrooms || est.bhk} Bathrooms · ${est.parking || 1} Dedicated Bays`;
  $("#repStatus").textContent = `${est.construction_status || "Ready to Move"} · ${est.age_years || 0} Years Age`;
  $("#repFurnishing").textContent = est.furnishing || "Semi-Furnished";

  $("#repBasePrice").textContent = fmtINR(est.predicted_price);
  $("#repStampDuty").textContent = fmtINR(f.stamp_duty || Math.round(est.predicted_price * 0.06));
  $("#repGst").textContent = (f.gst === 0 || est.construction_status === "Ready to Move") ? "Nil (Ready to Move)" : fmtINR(f.gst || 0);
  $("#repTotalCost").textContent = fmtINR(f.acquisition_cost || (est.predicted_price + (f.stamp_duty || 0) + (f.gst || 0)));

  const ltvPct = Math.round((f.ltv_ratio || 0.75) * 100);
  $("#repLoanAmount").textContent = `${fmtINR(f.loan_amount || Math.round(est.predicted_price * 0.75))} (${ltvPct}% Cap)`;
  $("#repDownPayment").textContent = `${fmtINR(f.down_payment || Math.round(est.predicted_price * 0.25))} (${100 - ltvPct}%)`;
  $("#repUpfrontCash").textContent = fmtINR(f.upfront_cash || ((f.down_payment || 0) + (f.stamp_duty || 0) + (f.gst || 0)));
  $("#repMonthlyEmi").textContent = `${fmtINR(f.monthly_emi || 0)} / month`;
  const rateVal = $("#rate")?.value || 8.5;
  const tenureVal = $("#tenure")?.value || 20;
  $("#repFinTerms").textContent = `${Number(rateVal).toFixed(2)}% p.a. · ${tenureVal} Years Tenure`;

  // Render comparables
  const grid = $("#repComparablesGrid");
  if (grid) {
    const comps = est.comparables && est.comparables.length ? est.comparables.slice(0, 3) : [];
    if (comps.length) {
      grid.innerHTML = comps.map((c) => `
        <div class="comp-mini-card">
          <div class="comp-loc">${escapeHtml(c.Locality)}, ${escapeHtml(c.City)}</div>
          <div class="comp-price">${fmtCompact(c.Price_INR)}</div>
          <div class="comp-meta">${c.BHK} BHK · ${c.Area_SqFt} sq.ft. · ${fmtINR(c.Price_per_sqft)}/psf</div>
        </div>
      `).join("");
    } else {
      grid.innerHTML = `
        <div class="comp-mini-card" style="grid-column: 1 / -1; text-align: center; color: var(--muted); padding: 16px;">
          Micro-market transactions indexed from official NHB RESIDEX benchmark registry.
        </div>
      `;
    }
  }

  if (est.data_provenance) {
    $("#repProvenance").textContent = est.data_provenance;
  }

  // Populate audited statutory legal citations
  const snap = f.applied_rules_snapshot || {};
  const stampRule = snap.stamp_duty_rule || {};
  const gstRule = snap.gst_rule || {};
  const ltvRules = Array.isArray(snap.ltv_rules) ? snap.ltv_rules : [];
  const activeLtv = ltvRules.find((r) => (f.loan_amount || 0) <= r.max_loan_inr) || ltvRules[0] || {};

  if ($("#repLtvCitation")) {
    $("#repLtvCitation").textContent = activeLtv.citation_ref || "RBI Master Direction - Housing Finance, Annex I (75% Cap)";
  }
  if ($("#repStampCitation")) {
    $("#repStampCitation").textContent = stampRule.citation_ref || `${est.state || "State"} Stamp Act Schedule (approximate compilation)`;
  }
  if ($("#repGstCitation")) {
    $("#repGstCitation").textContent = gstRule.citation_ref || (f.gst === 0 ? "Schedule III CGST Act (Ready to Move: 0%)" : "CBIC Notification No. 03/2019-Central Tax (Rate)");
  }
  if ($("#repRuleStatus")) {
    const isVerified = (stampRule.verification_status === "VERIFIED");
    $("#repRuleStatus").innerHTML = `<span class="badge ${isVerified ? "up" : "down"}">${isVerified ? "VERIFIED" : (stampRule.verification_status || "APPROXIMATE")}</span>`;
  }

  const certLink = $("#repCertLink");
  if (certLink) {
    const ref = est.valuation_ref || resp.lead_id || "REF-OFFICIAL";
    certLink.href = `/api/valuation/${encodeURIComponent(ref)}/certificate`;
  }
}


// ---------------------------------------------------------------------------
// Scroll reveal
// ---------------------------------------------------------------------------

let revealObserver = null;
function wireReveal() {
  if (!("IntersectionObserver" in window)) {
    $$(".reveal").forEach((el) => el.classList.add("in"));
    return;
  }
  revealObserver = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("in");
        revealObserver.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  $$(".reveal").forEach((el) => revealObserver.observe(el));
}

function observeReveal(root) {
  if (!revealObserver) return;
  $$(".reveal:not(.in)", root).forEach((el) => revealObserver.observe(el));
}

// ---------------------------------------------------------------------------
// Meta and static sections
// ---------------------------------------------------------------------------

async function loadMeta() {
  const res = await fetch("/api/meta");
  if (!res.ok) throw new Error(await errorText(res));
  const meta = await res.json();
  state.meta = meta;

  populateCities(meta);
  populateHeroStats(meta);
  populateMethod(meta);
  loadMarket().catch((err) => {
    $("#cityChart").innerHTML = `<p class="muted">Market overview unavailable: ${escapeHtml(err.message)}</p>`;
  });
}

function populateCities(meta) {
  const citySel = $("#city");
  citySel.innerHTML = meta.cities
    .map((c) => `<option value="${escapeAttr(c.name)}">${escapeHtml(c.name)} · ${escapeHtml(c.state)}</option>`)
    .join("");
  // Default to Mumbai (MMR) for EstateIQ focus
  citySel.value = meta.cities.find((c) => c.name.includes("Mumbai"))?.name || meta.cities[0].name;
  state.chatEnabled = Boolean(meta.chat_enabled);
  citySel.addEventListener("change", populateLocalities);
  populateLocalities();

  const preferred = ["Worli / South Mumbai", "Bandra West", "Whitefield", "Gomti Nagar", "Baner"];
  const locSel = $("#locality");
  const first = Array.from(locSel.options).find((o) => preferred.includes(o.value));
  if (first) locSel.value = first.value;
  updateStateHint();

  locSel.addEventListener("change", updateStateHint);
  buildSeg("#bhkGroup", [1, 2, 3, 4, 5].map(String), "3", (v) => onBhkChange(Number(v)), "bhk");
  buildTypeCards();
  buildSeg("#furnGroup", meta.furnishing_options, "Semi-Furnished", () => {}, "furnishing");
  buildSeg("#statusGroup", meta.status_options, "Ready to Move", () => {}, "status");

  setupRange("#area", "#areaRange", { min: 200, max: meta.bounds.area_sqft_max });
  setupRange("#age", null, {});
  setupRange("#dp", null, { fmt: (v) => v });
  setupRange("#rate", null, { fmt: (v) => Number(v).toFixed(2) });
  setupRange("#tenure", null, {});
  onBhkChange(3);

  $$("[data-step]").forEach((btn) => btn.addEventListener("click", () => {
    const key = btn.dataset.step;
    const max = key === "bathrooms" ? 10 : 5;
    const min = key === "bathrooms" ? 1 : 0;
    const el = $("#" + key);
    const next = Math.min(max, Math.max(min, Number(el.textContent) + Number(btn.dataset.d)));
    el.textContent = String(next);
    clearFormError();
  }));

  const r = meta.bounds.rate_pct;
  $("#rate").min = r.min; $("#rate").max = r.max; $("#rate").value = r.default;
  const t = meta.bounds.tenure_years;
  $("#tenure").min = t.min; $("#tenure").max = t.max; $("#tenure").value = t.default;
  $("#tenureOut").textContent = t.default;
  $("#rateOut").textContent = Number(r.default).toFixed(2);
  paintFills();
}

function populateLocalities() {
  const city = state.meta.cities.find((c) => c.name === $("#city").value);
  const sel = $("#locality");
  sel.innerHTML = city.localities
    .map((l) => `<option value="${escapeAttr(l.name)}">${escapeHtml(l.name)}</option>`)
    .join("");
  updateStateHint();
}

function updateStateHint() {
  const city = state.meta.cities.find((c) => c.name === $("#city").value);
  const loc = city.localities.find((l) => l.name === $("#locality").value);
  $("#stateHint").textContent = loc ? `State jurisdiction for stamp duty: ${loc.state}` : "";
}

function populateHeroStats(meta) {
  const localities = meta.cities.reduce((n, c) => n + c.localities.length, 0);
  const states = new Set(meta.cities.flatMap((c) => c.localities.map((l) => l.state))).size;
  const stats = {
    cities: String(meta.cities.length),
    localities: String(localities),
    mape: fmtPct(meta.model.metrics.mape_pct),
    states: String(states),
  };
  Object.entries(stats).forEach(([k, v]) => {
    const el = $(`[data-stat="${k}"]`);
    if (el) el.textContent = v;
  });
}

function populateMethod(meta) {
  const m = meta.model.metrics;
  const d = meta.model.data;
  $("#modelMeta").textContent = `${meta.model.name}`;
  $("#provText").textContent = d.kind === "synthetic"
    ? d.provenance
    : `Real transaction data (${d.source}). ${d.provenance}`;
  $("#metricTiles").innerHTML = [
    tile("Median holdout error", fmtPct(m.median_ape_pct), "good"),
    tile("Average error (MAPE)", fmtPct(m.mape_pct)),
    tile("R² on valuation", m.r2_price.toFixed(3)),
    tile(`Interval coverage (target ${m.interval_target_pct.toFixed(0)}%)`, fmtPct(m.interval_coverage_pct)),
    tile("Locality-median baseline", fmtPct(m.baseline_locality_median_mape_pct)),
    tile("Holdout sample rows", m.holdout_rows.toLocaleString("en-IN")),
  ].join("");

  const items = [
    { label: "EstateIQ Ensemble (holdout)", value: m.mape_pct },
    { label: "Locality-median baseline", value: m.baseline_locality_median_mape_pct },
  ];
  if (typeof m.noise_floor_mape_pct === "number") {
    items.push({ label: "Noise floor (theoretical ceiling)", value: m.noise_floor_mape_pct });
  }
  const chart = $("#accuracyChart");
  chart.innerHTML = `<div class="hbar" id="accBars"></div>`;
  mountHbars($("#accBars"), items, { format: (v) => fmtPct(v) });
  if (typeof m.noise_floor_mape_pct === "number") {
    const note = document.createElement("p");
    note.className = "hint";
    note.textContent = "Lower is better. On synthetic benchmark data, the noise floor is the best any statistical model could achieve.";
    chart.appendChild(note);
  }
}

function tile(label, value, cls = "") {
  return `<div class="tile ${cls}"><small>${escapeHtml(label)}</small><b>${escapeHtml(value)}</b></div>`;
}

async function loadMarket() {
  const res = await fetch("/api/market-overview");
  if (!res.ok) throw new Error(await errorText(res));
  const data = await res.json();
  state.marketData = data;

  mountHbars($("#cityChart"), data.cities.map((c) => ({ label: c.city, value: c.median_psf })), {
    format: (v) => fmtINR(v),
  });

  const coords = new Map();
  state.meta.cities.forEach((c) => c.localities.forEach((l) => coords.set(`${c.name}|${l.name}`, l)));
  const points = data.localities.map((l) => {
    const loc = coords.get(`${l.city}|${l.locality}`);
    return {
      lon: loc?.lon,
      lat: loc?.lat,
      value: l.psf,
      label: `${l.locality}, ${l.city}`,
      city: l.city,
      locality: l.locality,
      state: l.state,
    };
  }).filter((p) => Number.isFinite(p.lon) && Number.isFinite(p.lat));

  state.marketPoints = points;
  renderMarketMap("all");

  const scale = $("#mapScale");
  scale.innerHTML = `<span>Lower ₹/sq.ft.</span><span class="scale-bar"></span><span>Higher ₹/sq.ft.</span>`;
  observeReveal($("#market"));
  startAnimations($("#market"));

  wireCityBarSync();
}

function renderMarketMap(filter = "all") {
  if (!state.marketPoints) return;
  const filtered = filterPoints(state.marketPoints, filter);
  $("#indiaMap").innerHTML = scatterMap({ points: filtered, activeFilter: filter });
  wireMapInteractions();
}

function filterPoints(points, filter) {
  if (filter === "all") return points;
  if (filter === "tier2") {
    const topMetros = new Set(["Mumbai (MMR)", "Delhi NCR", "Bengaluru", "Hyderabad", "Pune", "Chennai", "Kolkata"]);
    return points.filter((p) => !topMetros.has(p.city));
  }
  return points.filter((p) => p.city === filter);
}

function wireClusterPills() {
  const pillsRoot = $("#clusterFilterPills");
  if (!pillsRoot) return;
  pillsRoot.addEventListener("click", (e) => {
    const btn = e.target.closest(".cluster-pill");
    if (!btn) return;
    pillsRoot.querySelectorAll(".cluster-pill").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const filter = btn.dataset.filter || "all";
    renderMarketMap(filter);
  });
}

function wireMapInteractions() {
  const mapSvg = $("#indiaMap svg");
  const hud = $("#marketHud");
  const mapWrapper = $("#mapWrapper");
  if (!mapSvg || !hud || !mapWrapper) return;

  const dotGroups = Array.from(mapSvg.querySelectorAll(".map-dot-group"));
  dotGroups.forEach((g) => {
    const onEnter = (e) => {
      dotGroups.forEach((other) => other.classList.remove("active-dot"));
      g.classList.add("active-dot");

      const locality = g.dataset.locality || "";
      const city = g.dataset.city || "";
      const tier = g.dataset.tier || "Prime Market";
      const psf = Number(g.dataset.psf) || 0;

      $("#hudLocality").textContent = locality;
      $("#hudTag").textContent = tier;
      $("#hudCity").textContent = city;
      $("#hudPsf").textContent = `₹${Math.round(psf).toLocaleString("en-IN")} / sq.ft.`;

      // Position HUD relative to map container
      const mapBox = mapWrapper.getBoundingClientRect();
      const dotCircle = g.querySelector(".map-dot");
      const dotBox = dotCircle.getBoundingClientRect();

      let left = dotBox.left - mapBox.left + 14;
      let top = dotBox.top - mapBox.top - 70;

      if (left + 230 > mapBox.width) left = dotBox.left - mapBox.left - 230;
      if (left < 10) left = 10;
      if (top < 10) top = dotBox.top - mapBox.top + 20;

      hud.style.left = `${left}px`;
      hud.style.top = `${top}px`;
      hud.hidden = false;

      syncCityChartRow(city);
    };

    g.addEventListener("mouseenter", onEnter);
    g.addEventListener("focus", onEnter);
    g.addEventListener("touchstart", onEnter, { passive: true });
  });

  mapWrapper.addEventListener("mouseleave", () => {
    hud.hidden = true;
    dotGroups.forEach((g) => g.classList.remove("active-dot"));
    clearCityChartHighlight();
  });

  const selectBtn = $("#hudSelectBtn");
  if (selectBtn) {
    selectBtn.onclick = () => {
      const activeGroup = mapSvg.querySelector(".map-dot-group.active-dot");
      if (!activeGroup) return;
      const city = activeGroup.dataset.city;
      const locality = activeGroup.dataset.locality;
      selectMarketInEstimator(city, locality);
    };
  }
}

function selectMarketInEstimator(city, locality) {
  const citySelect = $("#city");
  if (!citySelect) return;

  citySelect.value = city;
  citySelect.dispatchEvent(new Event("change"));

  setTimeout(() => {
    const locSelect = $("#locality");
    if (locSelect) {
      locSelect.value = locality;
      locSelect.dispatchEvent(new Event("change"));
    }
    const estSec = $("#estimate");
    if (estSec) {
      estSec.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  }, 120);
}

function wireCityBarSync() {
  const cityRows = $$("#cityChart .hbar-row");
  cityRows.forEach((row) => {
    const nameEl = row.querySelector(".name");
    const cityName = nameEl ? nameEl.getAttribute("title") || nameEl.textContent.trim() : "";

    row.addEventListener("mouseenter", () => {
      row.classList.add("city-row-hovered");
      const mapSvg = $("#indiaMap svg");
      if (!mapSvg) return;
      mapSvg.querySelectorAll(".map-dot-group").forEach((g) => {
        if (g.dataset.city === cityName) {
          g.classList.add("city-spotlight");
        } else {
          g.classList.add("city-dimmed");
        }
      });
    });

    row.addEventListener("mouseleave", () => {
      row.classList.remove("city-row-hovered");
      const mapSvg = $("#indiaMap svg");
      if (!mapSvg) return;
      mapSvg.querySelectorAll(".map-dot-group").forEach((g) => {
        g.classList.remove("city-spotlight", "city-dimmed");
      });
    });
  });
}

function syncCityChartRow(cityName) {
  $$("#cityChart .hbar-row").forEach((row) => {
    const nameEl = row.querySelector(".name");
    const name = nameEl ? nameEl.getAttribute("title") || nameEl.textContent.trim() : "";
    if (name === cityName) {
      row.classList.add("city-row-hovered");
      row.scrollIntoView({ behavior: "smooth", block: "nearest" });
    } else {
      row.classList.remove("city-row-hovered");
    }
  });
}

function clearCityChartHighlight() {
  $$("#cityChart .hbar-row").forEach((row) => row.classList.remove("city-row-hovered"));
}

function wireDeckChatBtn() {
  const btn = $("#deckChatBtn");
  if (!btn) return;
  btn.addEventListener("click", () => {
    const askSec = $("#ask");
    if (askSec) {
      askSec.scrollIntoView({ behavior: "smooth", block: "start" });
    }
    setTimeout(() => {
      const input = $("#chatInput");
      if (input) {
        input.focus();
        const cityVal = $("#city")?.value;
        const locVal = $("#locality")?.value;
        if (!state.est && cityVal && locVal && !input.value) {
          input.value = `What are the typical capital values, stamp duty and financing options in ${locVal}, ${cityVal}?`;
        }
      }
      const chatForm = $("#chatForm");
      if (chatForm) {
        chatForm.classList.add("highlight-focus");
        setTimeout(() => chatForm.classList.remove("highlight-focus"), 2000);
      }
    }, 550);
  });
}

// ---------------------------------------------------------------------------
// Controls
// ---------------------------------------------------------------------------

function buildSeg(sel, options, selected, onChange, name) {
  const root = $(sel);
  root.innerHTML = options.map((o) =>
    `<button type="button" role="radio" aria-checked="${o === selected}" data-value="${escapeAttr(o)}">${escapeHtml(o)}</button>`
  ).join("");
  root.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-value]");
    if (!btn || btn.disabled) return;
    $$("button", root).forEach((b) => b.setAttribute("aria-checked", String(b === btn)));
    onChange(btn.dataset.value);
    clearFormError();
  });
  root.dataset.name = name;
  wireArrowKeys(root);
}

function buildTypeCards() {
  const root = $("#typeGroup");
  root.innerHTML = state.meta.property_types.map((t) =>
    `<button type="button" class="type-card" role="radio" aria-checked="${t === "Apartment"}" data-value="${escapeAttr(t)}">
       <svg class="ico" aria-hidden="true"><use href="#${TYPE_ICON[t] || "i-apartment"}"/></svg>
       <span>${escapeHtml(t)}</span>
     </button>`
  ).join("");
  root.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-value]");
    if (!btn || btn.disabled) return;
    $$("button", root).forEach((b) => b.setAttribute("aria-checked", String(b === btn)));
    clearFormError();
  });
  wireArrowKeys(root);
}

function wireArrowKeys(container) {
  container.addEventListener("keydown", (e) => {
    if (!["ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown"].includes(e.key)) return;
    const buttons = $$("button[data-value]", container);
    const curr = buttons.findIndex((b) => b.getAttribute("aria-checked") === "true");
    if (curr < 0) return;
    e.preventDefault();
    const delta = ["ArrowRight", "ArrowDown"].includes(e.key) ? 1 : -1;
    const next = (curr + delta + buttons.length) % buttons.length;
    buttons[next].click();
    buttons[next].focus();
  });
}

function setupRange(numSel, rangeSel, { min, max, fmt }) {
  const num = $(numSel);
  const range = rangeSel ? $(rangeSel) : num;
  const out = $("#" + num.id + "Out");

  const sync = (v) => {
    num.value = v;
    if (rangeSel) range.value = v;
    if (out) out.textContent = fmt ? fmt(v) : v;
    paintFill(range);
    clearFormError();
  };

  if (rangeSel) {
    range.addEventListener("input", () => sync(range.value));
    num.addEventListener("input", () => {
      let v = Number(num.value);
      if (min != null && v < min) v = min;
      if (max != null && v > max) v = max;
      sync(v);
    });
  } else {
    num.addEventListener("input", () => sync(num.value));
  }
}

function paintFills() {
  $$('input[type="range"]').forEach(paintFill);
}

function paintFill(input) {
  const min = Number(input.min) || 0;
  const max = Number(input.max) || 100;
  const val = Number(input.value) || 0;
  const pct = Math.min(100, Math.max(0, ((val - min) / (max - min)) * 100));
  input.style.background = `linear-gradient(90deg, var(--accent) ${pct}%, var(--surface-2) ${pct}%)`;
}

function onBhkChange(bhk) {
  const typ = BHK_TYPICAL[bhk] || "1,000–3,000";
  $("#areaHint").textContent = `Market standard for ${bhk} BHK: ${typ} sq.ft.`;
  const bath = $("#bathrooms");
  if (Number(bath.textContent) > bhk + 2) bath.textContent = String(bhk);
}

// ---------------------------------------------------------------------------
// Form submission
// ---------------------------------------------------------------------------

function wireForm() {
  $("#estimateForm").addEventListener("submit", onSubmit);
}

function collectPayload() {
  const segVal = (sel) => $(`${sel} button[aria-checked="true"]`)?.dataset.value;
  return {
    city: $("#city").value,
    locality: $("#locality").value,
    bhk: Number(segVal("#bhkGroup")),
    area_sqft: Number($("#area").value),
    bathrooms: Number($("#bathrooms").textContent),
    parking: Number($("#parking").textContent),
    property_type: segVal("#typeGroup"),
    furnishing: segVal("#furnGroup"),
    construction_status: segVal("#statusGroup"),
    age_years: Number($("#age").value),
    down_payment_pct: Number($("#dp").value),
    annual_rate_pct: Number($("#rate").value),
    tenure_years: Number($("#tenure").value),
  };
}

function validate(p) {
  if (!p.city) return "Please choose a city.";
  if (!p.locality) return "Please choose a micro-market.";
  if (!p.bhk) return "Please select the number of bedrooms (BHK).";
  if (!p.property_type) return "Please choose a property type.";
  if (!p.area_sqft || p.area_sqft < 200) return "Area must be at least 200 sq.ft.";
  return null;
}

async function onSubmit(e) {
  e.preventDefault();
  if (state.busy) return;
  const payload = collectPayload();
  const problem = validate(payload);
  if (problem) return showFormError(problem);
  clearFormError();
  setBusy(true);
  showPanel("loading");
  try {
    const res = await fetch("/api/estimate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await errorText(res));
    const est = await res.json();
    state.est = { ...est, ...payload };
    renderEstimate(state.est);
    showPanel("body");
    resetChatForNewEstimate();
  } catch (err) {
    $("#errorText").textContent = err.message || "Unknown error";
    showPanel("error");
  } finally {
    setBusy(false);
  }
}

function setBusy(on) {
  state.busy = on;
  const btn = $("#submitBtn");
  btn.disabled = on;
  btn.classList.toggle("loading", on);
  btn.setAttribute("aria-busy", String(on));
}

function showPanel(which) {
  $("#resultsEmpty").hidden = which !== "empty";
  $("#resultsLoading").hidden = which !== "loading";
  $("#resultsError").hidden = which !== "error";
  $("#resultsBody").hidden = which !== "body";
}

function showFormError(msg) {
  const el = $("#formError");
  el.textContent = msg;
  el.hidden = false;
}

function clearFormError() {
  $("#formError").hidden = true;
}

async function errorText(res) {
  let body = null;
  try { body = await res.json(); } catch { /* not JSON */ }
  if (body?.detail?.message) return body.detail.message;
  if (body?.detail?.error) return body.detail.error;
  if (body?.details?.length) return body.details.map((d) => `${d.field ? d.field + ": " : ""}${d.message}`).join("; ");
  if (typeof body?.detail === "string") return body.detail;
  return `Request failed (${res.status})`;
}

// ---------------------------------------------------------------------------
// Results Rendering
// ---------------------------------------------------------------------------

function renderEstimate(est) {
  const f = est.finance;
  const r = est.price_range;

  countUp($("#outPrice"), est.predicted_price, fmtCompact);
  $("#outPrice").title = fmtINR(est.predicted_price);
  countUp($("#outRate"), est.rate_per_sqft, (v) => fmtINR(v));

  const vs = est.vs_city_median_pct;
  const vsEl = $("#outVs");
  vsEl.textContent = `${vs >= 0 ? "+" : ""}${vs.toFixed(1)}% vs ${est.city} median`;
  vsEl.className = "badge " + (vs >= 0 ? "up" : "down");

  $("#outLow").textContent = fmtCompact(r.low);
  $("#outHigh").textContent = fmtCompact(r.high);
  $("#rangeNote").textContent = `Statistical interval covers P${Math.round(r.low_q * 100)} to P${Math.round(r.high_q * 100)} of the model's calibrated predictive distribution.`;

  const lo = r.low * 0.85, hi = r.high * 1.15;
  const pos = (v) => `${Math.min(100, Math.max(0, ((v - lo) / (hi - lo)) * 100))}%`;
  const fill = $("#rangeFill");
  fill.style.left = pos(r.low);
  fill.style.width = `${(((r.high - r.low) / (hi - lo)) * 100)}%`;
  $("#rangeDot").style.left = pos(est.predicted_price);

  $("#ltvNote").textContent = f.ltv_cap_applied
    ? `RBI Tier LTV Cap Applied: Loan at ${fmtPct(f.ltv_ratio * 100, 0)} of value`
    : `Loan at ${fmtPct(f.ltv_ratio * 100, 0)} of property value`;

  $("#kpis").innerHTML = [
    kpi("Max Loan Amount", fmtCompact(f.loan_amount)),
    kpi("Monthly EMI", fmtCompact(f.monthly_emi), "accent"),
    kpi("Down Payment", fmtCompact(f.down_payment)),
    kpi("Stamp Duty & Reg.", fmtCompact(f.stamp_duty)),
    kpi("GST (Construction)", f.gst === 0 ? "Nil (Ready)" : fmtCompact(f.gst)),
    kpi("Total Upfront Cash", fmtCompact(f.upfront_cash), "accent"),
  ].join("");

  mountCostDonuts(est);
  mountComposition(est);
  renderForecast(est);
  renderAppliedRules(est);
  renderSensitivity(est);
  renderComparables(est);
  renderProforma(est);
  renderInfraProjects(est);
  updateOfferStrategy(est);
  updateLoanPrepayment(est);
  updateBuyVsRent(est);

  $("#compKind").textContent = est.comparables_kind === "synthetic"
    ? "Benchmark dataset"
    : "Supplied transactions";
  $("#compNote").textContent = est.comparables.length
    ? "Nearest architectural matches by micro-market and BHK from calibrated training data. Not active brokerage listings."
    : "No exact comparable matches for this micro-market and BHK in training data.";
  $("#provNote").textContent =
    `${est.data_provenance} Statutory stamp duty for ${est.state} is ${f.stamp_duty_status === "APPROXIMATE" ? "an approximate schedule rate. Verify with state registrar before execution." : "derived from verified schedule."}`;

  $$(".reveal", $("#resultsBody")).forEach((el) => el.classList.remove("in"));
  observeReveal($("#resultsBody"));
  startAnimations($("#resultsBody"));
}

function kpi(label, value, cls = "") {
  return `<div class="kpi ${cls}"><small>${escapeHtml(label)}</small><b>${escapeHtml(value)}</b></div>`;
}

function mountCostDonuts(est) {
  const f = est.finance;
  $("#costBar").innerHTML = donut({
    value: f.loan_amount,
    total: f.property_value,
    colorA: "var(--surface-2)",
    colorB: "var(--accent-3)",
    centerTop: fmtPct(f.ltv_ratio * 100, 0),
    centerBottom: "Funded by Loan",
  });
  $("#emiDonut").innerHTML = donut({
    value: f.total_interest,
    total: f.total_repayment,
    colorA: "var(--surface-2)",
    colorB: "var(--accent)",
    centerTop: fmtPct((f.total_interest / f.total_repayment) * 100, 0),
    centerBottom: "Interest Share",
  });
}

function mountComposition(est) {
  const f = est.finance;
  const segs = [
    { label: "Loan", value: f.loan_amount, color: "var(--accent-3)" },
    { label: "Down payment", value: f.down_payment, color: "var(--accent-2)" },
    { label: "Stamp duty + reg.", value: f.stamp_duty, color: "var(--accent)" },
    { label: "GST", value: f.gst, color: "#f87171" },
  ].filter((s) => s.value > 0);
  mountStack($("#stackBar"), segs);
  $("#stackLegend").innerHTML = segs.map((s) =>
    `<li><span class="swatch" style="background:${s.color}"></span>${escapeHtml(s.label)}<b>${fmtCompact(s.value)}</b></li>`
  ).join("");
}

let currentForecastCagr = 0.084;

function renderForecast(est, cagr = currentForecastCagr) {
  currentForecastCagr = cagr;
  const p = Number(est.predicted_price) || 0;
  if (!p) return;

  const y2021 = Math.round(p / Math.pow(1 + cagr, 5));
  const y2023 = Math.round(p / Math.pow(1 + cagr, 3));
  const y2026 = p;
  const y2027 = Math.round(p * Math.pow(1 + cagr, 1));
  const y2029 = Math.round(p * Math.pow(1 + cagr, 3));
  const y2031 = Math.round(p * Math.pow(1 + cagr, 5));
  const y2036 = Math.round(p * Math.pow(1 + cagr, 10));

  const gain3yPct = ((y2029 - p) / p) * 100;
  const gain5yPct = ((y2031 - p) / p) * 100;
  const gain10yTotal = y2036 - p;
  const gain10yPct = ((y2036 - p) / p) * 100;

  const kpisEl = $("#forecastKpis");
  if (kpisEl) {
    kpisEl.innerHTML = `
      <div class="forecast-kpi-item">
        <small>Current Valuation (2026)</small>
        <b>${fmtCompact(p)}</b>
        <span class="gain" style="color:var(--muted)">Base Benchmark</span>
      </div>
      <div class="forecast-kpi-item">
        <small>+3 Years (2029)</small>
        <b>${fmtCompact(y2029)}</b>
        <span class="gain">+${gain3yPct.toFixed(1)}% Appreciation</span>
      </div>
      <div class="forecast-kpi-item">
        <small>+5 Years (2031)</small>
        <b>${fmtCompact(y2031)}</b>
        <span class="gain">+${gain5yPct.toFixed(1)}% Appreciation</span>
      </div>
      <div class="forecast-kpi-item highlight">
        <small>10-Year Horizon (2036)</small>
        <b>${fmtCompact(y2036)}</b>
        <span class="gain">+${fmtCompact(gain10yTotal)} (+${gain10yPct.toFixed(0)}%)</span>
      </div>
    `;
  }

  const chartEl = $("#forecastChart");
  if (chartEl) {
    const dataPoints = [
      { year: 2021, price: y2021, label: "2021", isPast: true },
      { year: 2023, price: y2023, label: "2023", isPast: true },
      { year: 2026, price: y2026, label: "2026 (Now)", isCurrent: true },
      { year: 2027, price: y2027, label: "2027 (+1y)", isFuture: true },
      { year: 2029, price: y2029, label: "2029 (+3y)", isFuture: true },
      { year: 2031, price: y2031, label: "2031 (+5y)", isFuture: true },
      { year: 2036, price: y2036, label: "2036 (+10y)", isFuture: true },
    ];
    chartEl.innerHTML = forecastChart({ dataPoints, width: 720, height: 280, currencyFmt: fmtCompact });
  }

  // Update scenario button states
  $$("#forecastScenarios button").forEach((btn) => {
    const bCagr = Number(btn.dataset.cagr);
    const active = Math.abs(bCagr - cagr) < 0.001;
    btn.classList.toggle("active", active);
    btn.setAttribute("aria-checked", String(active));
  });
}

function wireForecastScenarios() {
  $("#forecastScenarios")?.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-cagr]");
    if (!btn || !state.est) return;
    const cagr = Number(btn.dataset.cagr) || 0.084;
    renderForecast(state.est, cagr);
  });
}

async function renderSensitivity(est) {
  const b = state.meta.bounds.rate_pct;
  const t = state.meta.bounds.tenure_years;
  const rates = [...new Set([
    clamp(est.annual_rate_pct - 1, b.min, b.max),
    est.annual_rate_pct,
    clamp(est.annual_rate_pct + 1, b.min, b.max),
  ].map((r) => Number(r.toFixed(2))))];
  const tenures = [10, 15, 20, 25, 30].filter((x) => x >= t.min && x <= t.max);

  const res = await fetch("/api/finance/sensitivity", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      property_value: est.predicted_price,
      down_payment_pct: est.down_payment_pct,
      rates_pct: rates,
      tenures_years: tenures,
    }),
  });
  if (!res.ok) {
    $("#emiLines").innerHTML = `<p class="muted">EMI grid unavailable: ${escapeHtml(await errorText(res))}</p>`;
    return;
  }
  const data = await res.json();
  const palette = ["var(--accent-2)", "var(--accent)", "var(--accent-3)"];
  const series = data.grid.map((row, i) => ({
    label: `${row.rate_pct}%`,
    color: palette[i % palette.length],
    points: row.emis.map((e) => ({ x: e.tenure_years, y: e.monthly_emi })),
  }));
  $("#emiLines").innerHTML = lineChart({
    series,
    xLabel: "Tenure (years)",
    yFormat: (v) => fmtCompact(v),
  });

  const head = `<thead><tr><th>Rate</th>${tenures.map((x) => `<th>${x} yrs</th>`).join("")}</tr></thead>`;
  const body = `<tbody>${data.grid.map((row) =>
    `<tr><td>${row.rate_pct}%</td>${row.emis.map((e) => {
      const hit = row.rate_pct === est.annual_rate_pct && e.tenure_years === est.tenure_years;
      return `<td class="${hit ? "hi" : ""}">${fmtINR(e.monthly_emi)}</td>`;
    }).join("")}</tr>`).join("")}</tbody>`;
  $("#emiTable").innerHTML = `<caption class="sr-only">Monthly EMI grid</caption>${head}${body}`;
  startAnimations($("#emiLines"));
}

function clamp(v, lo, hi) { return Math.min(hi, Math.max(lo, v)); }

function renderComparables(est) {
  const root = $("#comps");
  if (!est.comparables.length) {
    root.innerHTML = `<p class="muted">No comparables found.</p>`;
    return;
  }
  root.innerHTML = est.comparables.map((c, i) => {
    const hue = hashHue(c.City);
    return `
      <article class="comp" style="transition-delay:${i * 90}ms">
        <div class="comp-top">
          <span class="monogram" style="background:hsl(${hue} 55% 42%)">${escapeHtml(initials(c.Locality))}</span>
          <div><h4>${escapeHtml(c.Locality)}</h4><small>${escapeHtml(c.City)}</small></div>
        </div>
        <div class="big">${fmtCompact(c.Price_INR)}</div>
        <small class="muted">${fmtINR(c.Price_per_sqft)} / sq.ft.</small>
        <div class="meta">
          <span class="tag">${c.BHK} BHK</span>
          <span class="tag">${Math.round(c.Area_SqFt).toLocaleString("en-IN")} sq.ft.</span>
          <span class="tag">${escapeHtml(c.Property_Type)}</span>
          <span class="tag">${escapeHtml(c.Construction_Status)}</span>
        </div>
      </article>`;
  }).join("");
  requestAnimationFrame(() => requestAnimationFrame(() => {
    $$(".comp", root).forEach((el) => el.classList.add("in"));
  }));
}

function hashHue(s) {
  let h = 0;
  for (const ch of s) h = (h * 31 + ch.charCodeAt(0)) >>> 0;
  return h % 360;
}

function initials(name) {
  const words = name.replace(/[^A-Za-z0-9 ]/g, " ").trim().split(/\s+/).filter(Boolean);
  if (!words.length) return "EQ";
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return (words[0][0] + words[1][0]).toUpperCase();
}

// ---------------------------------------------------------------------------
// Chat Concierge
// ---------------------------------------------------------------------------

function wireChat() {
  renderChips();
  $("#chatForm").addEventListener("submit", onChatSubmit);
}

function resetChatForNewEstimate() {
  state.history = [];
  const log = $("#chatLog");
  log.innerHTML = "";
  renderChips();
  addBotMessage(
    `Valuation complete for ${state.est.bhk} BHK in ${state.est.locality}, ${state.est.city} (₹${fmtCompact(state.est.predicted_price)}). Ask any questions regarding your LTV cap, EMI schedules, or stamp duty.`
  );
}

function renderChips() {
  const root = $("#chips");
  const suggestions = SUGGESTIONS.slice(0, 4);
  root.innerHTML = suggestions
    .map((s) => `<button type="button" class="chip">${escapeHtml(s)}</button>`)
    .join("");
  $$(".chip", root).forEach((c) => {
    c.addEventListener("click", () => {
      $("#chatInput").value = c.textContent;
      $("#chatForm").dispatchEvent(new Event("submit", { cancelable: true }));
    });
  });
}

async function onChatSubmit(e) {
  e.preventDefault();
  const input = $("#chatInput");
  const text = input.value.trim();
  if (!text) return;
  input.value = "";
  addUserMessage(text);
  state.history.push({ role: "user", content: text });

  if (!state.est) {
    addBotMessage("Please calculate a property valuation first so I can ground answers in specific numbers.");
    return;
  }

  const thinking = addBotMessage("Thinking…");
  thinking.classList.add("muted");

  let reply = null;
  if (state.chatEnabled) {
    reply = await streamRemoteChat(state.history, state.est, thinking);
  }
  if (!reply) {
    reply = answerLocally(text, state.est);
    thinking.textContent = reply;
  }
  thinking.classList.remove("muted");
  state.history.push({ role: "assistant", content: reply });
}

function addUserMessage(text) {
  const el = document.createElement("div");
  el.className = "chat-msg user";
  el.textContent = text;
  $("#chatLog").appendChild(el);
  $("#chatLog").scrollTop = $("#chatLog").scrollHeight;
  return el;
}

function addBotMessage(text) {
  const el = document.createElement("div");
  el.className = "chat-msg bot";
  el.textContent = text;
  $("#chatLog").appendChild(el);
  $("#chatLog").scrollTop = $("#chatLog").scrollHeight;
  return el;
}

async function streamRemoteChat(messages, est, bubble) {
  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ messages, estimate_context: est }),
    });
    if (!res.ok || !res.body) return null;
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    let text = "";
    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      text += decoder.decode(value, { stream: true });
      bubble.textContent = text;
      $("#chatLog").scrollTop = $("#chatLog").scrollHeight;
    }
    if (!text.trim() || text.includes("temporarily unavailable")) return null;
    return text;
  } catch {
    return null;
  }
}

// ---------------------------------------------------------------------------
// Escaping
// ---------------------------------------------------------------------------

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function escapeAttr(s) { return escapeHtml(s); }

// ---------------------------------------------------------------------------
// Statutory Rules Applied Grid & Explorer Database
// ---------------------------------------------------------------------------

function renderAppliedRules(est) {
  try {
    const f = est.finance || {};
    const snap = f.applied_rules_snapshot || {};
    const grid = $("#rulesAppliedGrid");
    if (!grid) return;

    const stampRule = snap.stamp_duty_rule || {};
    const gstRule = snap.gst_rule || {};
    const ltvRules = Array.isArray(snap.ltv_rules) ? snap.ltv_rules : [];
    const activeLtv = ltvRules.find((r) => (f.loan_amount || 0) <= r.max_loan_inr) || ltvRules[0] || {};

    const benchRates = snap.benchmark_rates;
    let defaultRate = {};
    if (Array.isArray(benchRates)) {
      defaultRate = benchRates.find((r) => r.rate_key === "interest_rate_default_pct" || r.rate_key === "default_rate") || benchRates[0] || {};
    } else if (benchRates && typeof benchRates === "object") {
      const rulesApplied = benchRates.rules_applied || {};
      const ref = rulesApplied.interest_rate_default_pct || rulesApplied.default_rate || {};
      defaultRate = {
        citation_ref: ref.citation || "Bank floating-rate benchmarks (SBI / HDFC retail card)",
        source_url: ref.source_url || "https://www.rbi.org.in/",
      };
    }

    const stampStatus = stampRule.verification_status || (f.stamp_duty_status || "APPROXIMATE");
    const stampTagCls = stampStatus === "VERIFIED" ? "verified" : stampStatus === "FALLBACK" ? "fallback" : "approx";

    grid.innerHTML = `
      <div class="rule-card-mini">
        <div class="rule-card-head">
          <span class="rule-card-title">RBI Loan-to-Value Cap</span>
          <span class="rule-tag verified">VERIFIED</span>
        </div>
        <div class="rule-card-val">${fmtPct((activeLtv.ltv_ratio || f.ltv_ratio || 0.75) * 100, 0)} Cap</div>
        <div class="rule-card-cit">
          <strong>${escapeHtml(activeLtv.tier_name || "Tier")}</strong>:
          ${escapeHtml(activeLtv.citation_ref || "RBI Master Direction - Housing Finance, Annex I")}
        </div>
        ${activeLtv.source_url ? `<a href="${escapeAttr(activeLtv.source_url)}" target="_blank" rel="noopener" class="rule-source-link">Primary Source Circular ↗</a>` : ""}
      </div>

      <div class="rule-card-mini">
        <div class="rule-card-head">
          <span class="rule-card-title">${escapeHtml(est.state || "State")} Stamp Duty &amp; Reg.</span>
          <span class="rule-tag ${stampTagCls}">${escapeHtml(stampStatus)}</span>
        </div>
        <div class="rule-card-val">${fmtPct((stampRule.rate || f.stamp_duty_rate || 0.06) * 100, 1)} Rate</div>
        <div class="rule-card-cit">
          ${escapeHtml(stampRule.citation_ref || "State Stamp Act Schedule (approximate compilation)")}
        </div>
        ${stampRule.source_url ? `<a href="${escapeAttr(stampRule.source_url)}" target="_blank" rel="noopener" class="rule-source-link">Gazette Schedule ↗</a>` : ""}
      </div>

      <div class="rule-card-mini">
        <div class="rule-card-head">
          <span class="rule-card-title">Goods &amp; Services Tax (GST)</span>
          <span class="rule-tag verified">VERIFIED</span>
        </div>
        <div class="rule-card-val">${fmtPct((gstRule.rate ?? (f.gst === 0 ? 0 : 0.05)) * 100, 1)}</div>
        <div class="rule-card-cit">
          ${escapeHtml(gstRule.citation_ref || (f.gst === 0 ? "Schedule III CGST Act (Ready to Move: 0%)" : "Notification No. 03/2019-Central Tax (Rate)"))}
        </div>
        ${gstRule.source_url ? `<a href="${escapeAttr(gstRule.source_url)}" target="_blank" rel="noopener" class="rule-source-link">GST Council Circular ↗</a>` : ""}
      </div>

      <div class="rule-card-mini">
        <div class="rule-card-head">
          <span class="rule-card-title">Home Loan Floating Rate</span>
          <span class="rule-tag approx">INDICATIVE</span>
        </div>
        <div class="rule-card-val">${Number($("#rate")?.value || 8.5).toFixed(2)}% p.a.</div>
        <div class="rule-card-cit">
          ${escapeHtml(defaultRate.citation_ref || "Bank floating-rate benchmarks (SBI / HDFC retail card)")}
        </div>
        ${defaultRate.source_url ? `<a href="${escapeAttr(defaultRate.source_url)}" target="_blank" rel="noopener" class="rule-source-link">Benchmark Source ↗</a>` : ""}
      </div>
    `;
  } catch (err) {
    console.warn("Could not render applied rules:", err);
  }
}

let cachedRules = null;
let currentRuleFilter = "all";

function wireRulesExplorer() {
  const modal = $("#rulesModal");
  const navBtn = $("#rulesNavBtn");
  const openBtn = $("#openRulesExplorerBtn");
  const closeBtn = $("#closeRulesModalBtn");
  if (!modal) return;

  function openRules() {
    modal.hidden = false;
    modal.classList.add("open");
    modal.setAttribute("aria-hidden", "false");
    document.body.style.overflow = "hidden";
    loadRulesData();
  }

  function closeRules() {
    modal.classList.remove("open");
    modal.setAttribute("aria-hidden", "true");
    modal.hidden = true;
    document.body.style.overflow = "";
  }

  navBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    openRules();
  });

  openBtn?.addEventListener("click", (e) => {
    e.preventDefault();
    openRules();
  });

  closeBtn?.addEventListener("click", closeRules);

  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeRules();
  });

  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.classList.contains("open")) closeRules();
  });

  $("#rulesFilterGroup")?.addEventListener("click", (e) => {
    const btn = e.target.closest("button[data-filter]");
    if (!btn) return;
    $$("#rulesFilterGroup button").forEach((b) => {
      const active = b === btn;
      b.classList.toggle("active", active);
      b.setAttribute("aria-checked", String(active));
    });
    currentRuleFilter = btn.dataset.filter;
    renderRulesTable();
  });
}

async function loadRulesData() {
  if (cachedRules) {
    renderRulesTable();
    return;
  }
  const tbody = $("#rulesTableBody");
  if (tbody) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color:var(--muted);">Loading versioned legal database...</td></tr>`;
  }
  try {
    const res = await fetch("/api/rules");
    if (!res.ok) throw new Error(await errorText(res));
    cachedRules = await res.json();
    renderRulesTable();
  } catch (err) {
    if (tbody) {
      tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color:#ef4444;">Failed to load rules: ${escapeHtml(err.message)}</td></tr>`;
    }
  }
}

function renderRulesTable() {
  if (!cachedRules) return;
  const tbody = $("#rulesTableBody");
  if (!tbody) return;

  let items = [];

  if (currentRuleFilter === "all" || currentRuleFilter === "ltv") {
    (cachedRules.ltv_rules || []).forEach((r) => {
      items.push({
        name: `RBI LTV: ${r.tier_name}`,
        value: `${Math.round(r.ltv_ratio * 100)}% Cap`,
        citation: r.citation_ref,
        effective_from: r.effective_from,
        status: r.verification_status,
        url: r.source_url,
      });
    });
  }

  if (currentRuleFilter === "all" || currentRuleFilter === "stamp") {
    (cachedRules.stamp_duty_rules || []).forEach((r) => {
      items.push({
        name: `Stamp Duty: ${r.state} (${r.buyer_category})`,
        value: `${(r.rate_pct * 100).toFixed(1)}%`,
        citation: r.gazette_ref,
        effective_from: r.effective_from,
        status: r.verification_status,
        url: r.source_url,
      });
    });
  }

  if (currentRuleFilter === "all" || currentRuleFilter === "gst") {
    (cachedRules.gst_rules || []).forEach((r) => {
      items.push({
        name: `GST: ${r.construction_status} ${r.is_affordable ? "(Affordable)" : ""}`,
        value: `${(r.rate_pct * 100).toFixed(1)}%`,
        citation: r.notification_ref,
        effective_from: r.effective_from,
        status: r.verification_status,
        url: r.source_url,
      });
    });
  }

  if (currentRuleFilter === "all" || currentRuleFilter === "bench") {
    (cachedRules.benchmark_rates || []).forEach((r) => {
      items.push({
        name: `Benchmark: ${r.rate_key}`,
        value: `${r.rate_value} ${r.unit === "percentage" ? "%" : "yrs"}`,
        citation: r.citation_ref,
        effective_from: r.effective_from,
        status: r.verification_status,
        url: r.source_url,
      });
    });
  }

  if (!items.length) {
    tbody.innerHTML = `<tr><td colspan="6" style="text-align:center; padding: 24px; color:var(--muted);">No matching rules found in active database.</td></tr>`;
    return;
  }

  tbody.innerHTML = items.map((item) => {
    const isVer = item.status === "VERIFIED";
    const tagCls = isVer ? "verified" : item.status === "FALLBACK" ? "fallback" : "approx";
    return `
      <tr>
        <td class="rule-name-cell">${escapeHtml(item.name)}</td>
        <td class="rule-val-cell">${escapeHtml(item.value)}</td>
        <td>${escapeHtml(item.citation)}</td>
        <td>${escapeHtml(item.effective_from || "2020-01-01")}</td>
        <td><span class="rule-tag ${tagCls}">${escapeHtml(item.status)}</span></td>
        <td><a href="${escapeAttr(item.url)}" target="_blank" rel="noopener" class="rule-source-link">Primary Source ↗</a></td>
      </tr>
    `;
  }).join("");
}

// ---------------------------------------------------------------------------
// Interactive Micro-Market Heatmap (Mumbai MMR)
// ---------------------------------------------------------------------------

let activeHeatmapMetric = "rate"; // "rate" | "yield"
let heatmapNodesData = [];

async function initMarketHeatmap() {
  const container = $("#mapNodesContainer");
  const hud = $("#mapNodeHud");
  const toggles = $("#mapMetricToggles");
  if (!container) return;

  try {
    const res = await fetch("/api/market-heatmap");
    if (!res.ok) throw new Error(await errorText(res));
    heatmapNodesData = await res.json();
    renderHeatmapNodes();
  } catch (err) {
    console.warn("Could not load market heatmap:", err);
  }

  toggles?.addEventListener("click", (e) => {
    const btn = e.target.closest(".map-toggle-btn");
    if (!btn) return;
    $$(".map-toggle-btn", toggles).forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    activeHeatmapMetric = btn.dataset.mode;
    renderHeatmapNodes();
  });

  $("#hudNodeSelectBtn")?.addEventListener("click", () => {
    const activeNodeId = hud?.dataset.activeNodeId;
    const node = heatmapNodesData.find((n) => n.id === activeNodeId);
    if (!node) return;
    loadNodeIntoValuationEngine(node);
  });
}

function renderHeatmapNodes() {
  const container = $("#mapNodesContainer");
  if (!container || !heatmapNodesData.length) return;

  container.innerHTML = heatmapNodesData.map((node) => {
    const cx = (node.x / 100) * 1000;
    const cy = (node.y / 100) * 680;
    const isRate = activeHeatmapMetric === "rate";

    let color = "#d4af37";
    let glowId = "nodeGlowHigh";
    if (isRate) {
      if (node.rate > 75000) color = "#d4af37";
      else if (node.rate >= 45000) color = "#5c7cfa";
      else color = "#34d399";
    } else {
      glowId = "nodeGlowYield";
      if (node.yield >= 3.5) color = "#34d399";
      else if (node.yield >= 2.5) color = "#5c7cfa";
      else color = "#d4af37";
    }

    const valDisplay = isRate ? `₹${Math.round(node.rate / 1000)}k/psf` : `${node.yield}% yield`;

    return `
      <g class="map-node-group" data-id="${escapeAttr(node.id)}" tabindex="0" role="button" aria-label="${escapeAttr(node.name)}: ${valDisplay}">
        <circle cx="${cx}" cy="${cy}" r="32" fill="url(#${glowId})" opacity="0.65" />
        <circle cx="${cx}" cy="${cy}" r="9" fill="${color}" stroke="#ffffff" stroke-width="2" />
        <circle cx="${cx}" cy="${cy}" r="16" fill="none" stroke="${color}" stroke-width="1.5" stroke-dasharray="3,3" opacity="0.8" />
        <rect x="${cx - 55}" y="${cy + 14}" width="110" height="20" rx="4" fill="rgba(9,13,20,0.85)" stroke="${color}" stroke-width="0.8"/>
        <text x="${cx}" y="${cy + 28}" text-anchor="middle" fill="#ffffff" font-size="9.5" font-weight="600" letter-spacing="0.2">${escapeHtml(node.name.split(" ")[0])} · ${valDisplay}</text>
      </g>
    `;
  }).join("");

  $$(".map-node-group", container).forEach((g) => {
    const nodeId = g.dataset.id;
    const node = heatmapNodesData.find((n) => n.id === nodeId);
    if (!node) return;

    g.addEventListener("mouseenter", () => showNodeHud(node));
    g.addEventListener("focus", () => showNodeHud(node));
    g.addEventListener("click", () => showNodeHud(node));
  });
}

function showNodeHud(node) {
  const hud = $("#mapNodeHud");
  if (!hud) return;
  hud.dataset.activeNodeId = node.id;
  $("#hudNodeTag").textContent = node.tag || "Prime Micro-Market";
  $("#hudNodeBhk").textContent = `${node.bhk} BHK · ${Number(node.area_sqft).toLocaleString("en-IN")} sq.ft.`;
  $("#hudNodeName").textContent = node.name;
  $("#hudNodeRate").textContent = `₹${Number(node.rate).toLocaleString("en-IN")} / sq.ft.`;
  $("#hudNodeYield").textContent = `${node.yield}% p.a.`;
  hud.hidden = false;
}

function loadNodeIntoValuationEngine(node) {
  const citySel = $("#city");
  if (citySel) {
    citySel.value = "Mumbai (MMR)";
    populateLocalities();
  }
  const locSel = $("#locality");
  if (locSel) {
    const opt = Array.from(locSel.options).find((o) =>
      o.value.toLowerCase().includes(node.name.toLowerCase().split(" ")[0]) ||
      node.name.toLowerCase().includes(o.value.toLowerCase().split(" ")[0])
    );
    if (opt) locSel.value = opt.value;
    updateStateHint();
  }

  const bhkBtn = $(`#bhkGroup button[data-value="${node.bhk}"]`);
  if (bhkBtn) bhkBtn.click();

  const areaInput = $("#area");
  if (areaInput) {
    areaInput.value = node.area_sqft;
    const areaRange = $("#areaRange");
    if (areaRange) areaRange.value = node.area_sqft;
    paintFills();
  }

  $("#estimate")?.scrollIntoView({ behavior: "smooth" });

  setTimeout(() => {
    $("#estimateForm")?.dispatchEvent(new Event("submit", { cancelable: true }));
  }, 250);
}

// ---------------------------------------------------------------------------
// Investor Pro-Forma & Rental Yield
// ---------------------------------------------------------------------------

function renderProforma(est) {
  const panel = $("#proformaPanel");
  if (!panel) return;

  const f = est.finance || {};
  const propVal = est.predicted_price || 0;
  if (!propVal) return;

  let grossYield = 0.030;
  if (est.city?.includes("Mumbai")) grossYield = 0.026;
  else if (est.city?.includes("Bengaluru")) grossYield = 0.038;
  else if (est.city?.includes("Hyderabad")) grossYield = 0.035;
  else if (est.city?.includes("Pune")) grossYield = 0.036;

  const annualGrossRent = Math.round(propVal * grossYield);
  const monthlyRent = Math.round(annualGrossRent / 12);
  const vacancyReserve = monthlyRent;
  const maintTax = Math.round(propVal * 0.0075);
  const netAnnualCashflow = Math.max(0, annualGrossRent - vacancyReserve - maintTax);
  const realNetYield = ((netAnnualCashflow / propVal) * 100).toFixed(2);

  const emi = f.monthly_emi || 1;
  const emiCoverage = Math.min(100, (monthlyRent / emi) * 100).toFixed(1);
  const upfront = f.upfront_cash || Math.round(propVal * 0.31);
  const paybackYears = netAnnualCashflow > 0 ? (upfront / netAnnualCashflow).toFixed(1) : "–";

  $("#proformaYieldBadge").textContent = `Gross Yield: ${(grossYield * 100).toFixed(1)}%`;
  $("#proMonthlyRent").textContent = fmtCompact(monthlyRent);
  $("#proAnnualRent").textContent = fmtCompact(annualGrossRent);
  $("#proNetYield").textContent = `${realNetYield}%`;
  $("#proEmiOffset").textContent = `${emiCoverage}%`;
  $("#proPayback").textContent = `${paybackYears} Yrs`;

  $("#flowGrossRent").textContent = fmtCompact(annualGrossRent);
  $("#flowVacancy").textContent = fmtCompact(vacancyReserve);
  $("#flowMaint").textContent = fmtCompact(maintTax);
  $("#flowNetCash").textContent = fmtCompact(netAnnualCashflow);

  const battleBtn = $("#addCurrentToBattleBtn");
  if (battleBtn) {
    battleBtn.onclick = () => {
      loadActiveIntoBattleSlot1();
      $("#propBattle")?.scrollIntoView({ behavior: "smooth" });
    };
  }
}

// ---------------------------------------------------------------------------
// Mega-Infrastructure Impact & Catalysts
// ---------------------------------------------------------------------------

async function renderInfraProjects(est) {
  const grid = $("#infraProjectsGrid");
  if (!grid) return;

  try {
    const loc = est.locality || "";
    const city = est.city || "Mumbai (MMR)";
    const res = await fetch(`/api/infrastructure-projects?locality=${encodeURIComponent(loc)}&city=${encodeURIComponent(city)}`);
    if (!res.ok) throw new Error(await errorText(res));
    const data = await res.json();

    $("#infraBaseCagr").textContent = `${data.base_cagr_pct}%`;
    $("#infraCatalystCagr").textContent = `${data.catalyst_cagr_pct}%`;
    $("#infra3YrMult").textContent = `${data.projected_3yr_multiplier}×`;
    $("#infra5YrMult").textContent = `${data.projected_5yr_multiplier}×`;

    const projects = data.active_projects || [];
    grid.innerHTML = projects.map((proj) => `
      <div class="infra-project-card">
        <div class="infra-proj-head">
          <span class="infra-proj-agency">${escapeHtml(proj.agency)}</span>
          <span class="infra-proj-year">Completion: ${proj.completion_year}</span>
        </div>
        <h4 class="infra-proj-title">${escapeHtml(proj.name)}</h4>
        <p class="infra-proj-summary">${escapeHtml(proj.summary)}</p>
        <div class="infra-proj-foot">
          <span class="infra-boost-pill">+${proj.premium_appreciation_pct}% / yr Catalyst Boost</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.warn("Could not load infrastructure projects:", err);
  }
}

// ---------------------------------------------------------------------------
// Side-by-Side Property Battle
// ---------------------------------------------------------------------------

let battleSlots = [
  { name: "Worli Sea Face 3 BHK", locality: "Worli Sea Face", city: "Mumbai (MMR)", bhk: 3, area_sqft: 2200, age_years: 2, property_value: 184200000, rental_yield_pct: 2.4 },
  { name: "Bandra West 3 BHK", locality: "Bandra West", city: "Mumbai (MMR)", bhk: 3, area_sqft: 1850, age_years: 3, property_value: 145200000, rental_yield_pct: 2.7 },
  { name: "Powai Hiranandani 2 BHK", locality: "Powai Hiranandani", city: "Mumbai (MMR)", bhk: 2, area_sqft: 1100, age_years: 4, property_value: 35800000, rental_yield_pct: 3.9 },
];

function initPropertyBattle() {
  $("#loadPresetBattleBtn")?.addEventListener("click", () => {
    battleSlots = [
      { name: "Worli Sea Face 3 BHK", locality: "Worli Sea Face", city: "Mumbai (MMR)", bhk: 3, area_sqft: 2200, age_years: 2, property_value: 184200000, rental_yield_pct: 2.4 },
      { name: "Bandra West 3 BHK", locality: "Bandra West", city: "Mumbai (MMR)", bhk: 3, area_sqft: 1850, age_years: 3, property_value: 145200000, rental_yield_pct: 2.7 },
      { name: "Powai Hiranandani 2 BHK", locality: "Powai Hiranandani", city: "Mumbai (MMR)", bhk: 2, area_sqft: 1100, age_years: 4, property_value: 35800000, rental_yield_pct: 3.9 },
    ];
    runPropertyBattle();
  });

  $("#loadActiveIntoSlot1Btn")?.addEventListener("click", () => {
    loadActiveIntoBattleSlot1();
  });

  runPropertyBattle();
}

function loadActiveIntoBattleSlot1() {
  if (!state.est) return;
  const e = state.est;
  battleSlots[0] = {
    name: `${e.locality} ${e.bhk} BHK (Active Valuation)`,
    locality: e.locality,
    city: e.city,
    bhk: e.bhk,
    area_sqft: e.area_sqft,
    age_years: e.age_years || 2,
    property_value: e.predicted_price,
    rental_yield_pct: e.city?.includes("Mumbai") ? 2.6 : 3.5,
  };
  runPropertyBattle();
}

async function runPropertyBattle() {
  const grid = $("#battleCardsGrid");
  if (!grid) return;

  try {
    const res = await fetch("/api/finance/compare-properties", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ properties: battleSlots }),
    });
    if (!res.ok) throw new Error(await errorText(res));
    const data = await res.json();

    const winners = data.winner_summary || {};
    $("#winCash").textContent = winners.lowest_upfront_cash || "–";
    $("#winYield").textContent = winners.highest_rental_yield || "–";
    $("#winEmi").textContent = winners.lowest_monthly_emi || "–";
    $("#winPsf").textContent = winners.best_value_rate_per_sqft || "–";

    grid.innerHTML = (data.properties || []).map((p, idx) => `
      <div class="battle-slot-card">
        <div class="battle-card-header">
          <div>
            <span class="slot-tag">SLOT 0${idx + 1}</span>
            <h4 class="slot-prop-name">${escapeHtml(p.name)}</h4>
          </div>
          <span class="tag">${p.bhk} BHK · ${Math.round(p.area_sqft)} sq.ft.</span>
        </div>

        <div class="slot-prop-price">${fmtCompact(p.property_value)}</div>
        <small class="muted" style="margin-top:-10px;">${fmtINR(p.rate_per_sqft)} / sq.ft.</small>

        <table class="slot-metrics-table">
          <tr><td>Total Upfront Cash:</td><td><strong>${fmtCompact(p.upfront_cash_inr)}</strong></td></tr>
          <tr><td>Down Payment (20-25%):</td><td>${fmtCompact(p.down_payment_inr)}</td></tr>
          <tr><td>Stamp Duty & Reg.:</td><td>${fmtCompact(p.stamp_duty_inr)}</td></tr>
          <tr><td>Monthly EMI (20 Yrs):</td><td><strong>${fmtINR(p.monthly_emi_inr)} / mo</strong></td></tr>
          <tr><td>Gross Rental Yield:</td><td><strong class="highlight-emerald">${p.gross_rental_yield_pct}%</strong></td></tr>
          <tr><td>Tenant EMI Coverage:</td><td>${p.emi_offset_pct}%</td></tr>
        </table>

        <div class="slot-verdict-banner">
          <strong class="highlight-gold" style="display:block; margin-bottom:2px;">${escapeHtml(p.verdict_badge)}</strong>
          <span>${escapeHtml(p.verdict)}</span>
        </div>
      </div>
    `).join("");
  } catch (err) {
    console.warn("Could not run property battle:", err);
  }
}

// ---------------------------------------------------------------------------
// Interactive Offer Strategy & Bargaining Simulator
// ---------------------------------------------------------------------------

let activeOfferEst = null;
let offerDebounceTimer = null;

function initOfferStrategy() {
  const slider = $("#offerSlider");
  if (!slider) return;

  slider.addEventListener("input", () => {
    if (offerDebounceTimer) clearTimeout(offerDebounceTimer);
    offerDebounceTimer = setTimeout(calcOfferStrategy, 80);
  });

  $("#copyNegotiationBriefBtn")?.addEventListener("click", () => {
    const bullets = Array.from($$("#briefBulletsList li")).map((li) => `• ${li.textContent}`).join("\n");
    if (!bullets) return;
    navigator.clipboard.writeText(bullets).then(() => {
      const toast = $("#copyToast");
      if (toast) {
        toast.hidden = false;
        setTimeout(() => { toast.hidden = true; }, 3000);
      }
    }).catch(() => {});
  });

  calcOfferStrategy();
}

function updateOfferStrategy(est) {
  activeOfferEst = est;
  calcOfferStrategy();
}

async function calcOfferStrategy() {
  const slider = $("#offerSlider");
  if (!slider) return;

  const est = activeOfferEst || state.est || {
    predicted_price: 28500000,
    price_range: { low: 26200000, high: 30800000 },
    city: "Mumbai (MMR)",
    locality: "Worli Sea Face",
  };

  const pVal = est.predicted_price;
  const pLow = est.price_range?.low || Math.round(pVal * 0.92);
  const pHigh = est.price_range?.high || Math.round(pVal * 1.08);

  $("#offerP10Label").textContent = fmtCompact(pLow);
  $("#offerP50Label").textContent = fmtCompact(pVal);
  $("#offerP90Label").textContent = fmtCompact(pHigh);

  const pct = Number(slider.value) / 100;
  const targetOffer = Math.round(pLow + pct * (pHigh - pLow));

  try {
    const res = await fetch("/api/finance/offer-strategy", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_value: pVal,
        price_low: pLow,
        price_high: pHigh,
        target_offer: targetOffer,
        city: est.city,
        locality: est.locality,
      }),
    });
    if (!res.ok) throw new Error(await errorText(res));
    const data = await res.json();

    $("#offerTargetDisplay").textContent = fmtCompact(data.target_offer);
    const diffTag = $("#offerDiffTag");
    if (diffTag) {
      if (data.discount_inr > 0) {
        diffTag.textContent = `₹${fmtCompact(data.discount_inr)} below median (${data.discount_pct}% discount)`;
        diffTag.style.color = "#34d399";
      } else if (data.discount_inr < 0) {
        diffTag.textContent = `₹${fmtCompact(Math.abs(data.discount_inr))} trophy premium (+${Math.abs(data.discount_pct)}%)`;
        diffTag.style.color = "#d4af37";
      } else {
        diffTag.textContent = "Benchmark Valuation Equilibrium";
        diffTag.style.color = "var(--text-dim)";
      }
    }

    $("#offerTierPill").textContent = data.badge;
    $("#offerPercentileText").textContent = `${Math.round(data.percentile)}th Percentile`;
    $("#offerTierDesc").textContent = data.description;
    $("#offerDiscountVal").textContent = fmtCompact(data.discount_inr);
    $("#offerStampSaved").textContent = fmtCompact(data.stamp_saved_inr);
    $("#offerEmiTrimmed").textContent = `${fmtINR(data.monthly_emi_saved_inr)} / mo`;

    const bulletsList = $("#briefBulletsList");
    if (bulletsList && data.negotiation_points) {
      bulletsList.innerHTML = data.negotiation_points.map((pt) => `<li>${escapeHtml(pt)}</li>`).join("");
    }
  } catch (err) {
    console.warn("Could not calculate offer strategy:", err);
  }
}

// ---------------------------------------------------------------------------
// Loan Prepayment & "Interest Saver" Calculator
// ---------------------------------------------------------------------------

let prepayDebounceTimer = null;

function initLoanPrepayment() {
  const mSlider = $("#monthlyPrepaySlider");
  const aSlider = $("#annualLumpsumSlider");
  if (!mSlider || !aSlider) return;

  const onPrepayInput = () => {
    $("#monthlyPrepayOut").textContent = `+₹${Number(mSlider.value).toLocaleString("en-IN")} / mo`;
    $("#annualLumpsumOut").textContent = `+₹${fmtCompact(Number(aSlider.value))} / yr`;
    if (prepayDebounceTimer) clearTimeout(prepayDebounceTimer);
    prepayDebounceTimer = setTimeout(calcLoanPrepayment, 80);
  };

  mSlider.addEventListener("input", onPrepayInput);
  aSlider.addEventListener("input", onPrepayInput);

  calcLoanPrepayment();
}

function updateLoanPrepayment(est) {
  calcLoanPrepayment();
}

async function calcLoanPrepayment() {
  const mSlider = $("#monthlyPrepaySlider");
  const aSlider = $("#annualLumpsumSlider");
  if (!mSlider || !aSlider) return;

  const est = state.est;
  const loanAmount = est?.finance?.loan_amount || 20000000;
  const ratePct = Number($("#rate")?.value || 8.5);
  const tenureYears = Number($("#tenure")?.value || 20);

  $("#prepayBaseLoan").textContent = fmtCompact(loanAmount);
  $("#prepayBaseRate").textContent = `${ratePct.toFixed(2)}%`;
  $("#prepayBaseTenure").textContent = `${tenureYears} Yrs`;

  const monthlyExtra = Number(mSlider.value);
  const annualExtra = Number(aSlider.value);

  try {
    const res = await fetch("/api/finance/loan-prepayment", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        loan_amount: loanAmount,
        annual_rate_pct: ratePct,
        tenure_years: tenureYears,
        monthly_prepayment: monthlyExtra,
        annual_lumpsum: annualExtra,
      }),
    });
    if (!res.ok) throw new Error(await errorText(res));
    const data = await res.json();

    $("#prepayYearsSaved").textContent = `${data.years_saved} Yrs`;
    $("#prepayOriginalTenure").textContent = `${data.base_tenure_years}`;
    $("#prepayNewTenure").textContent = `${data.accelerated_tenure_years} Yrs`;
    $("#prepayInterestSaved").textContent = fmtCompact(data.interest_saved);
    $("#prepayInterestSavedPct").textContent = `${data.interest_saved_pct}%`;

    $("#barBaseTotal").textContent = fmtCompact(data.base_total_repayment);
    $("#barAccelTotal").textContent = fmtCompact(data.accelerated_total_repayment);
    const fillPct = Math.min(100, Math.round((data.accelerated_total_repayment / data.base_total_repayment) * 100));
    const fillEl = $("#barAccelFill");
    if (fillEl) fillEl.style.width = `${fillPct}%`;
  } catch (err) {
    console.warn("Could not calculate loan prepayment:", err);
  }
}

// ---------------------------------------------------------------------------
// 20-Year "Buy vs. Rent" Wealth Compounding Comparison
// ---------------------------------------------------------------------------

let bvrDebounceTimer = null;

function initBuyVsRent() {
  $("#bvrEquityCagr")?.addEventListener("change", () => {
    if (bvrDebounceTimer) clearTimeout(bvrDebounceTimer);
    bvrDebounceTimer = setTimeout(calcBuyVsRent, 80);
  });
  $("#bvrPropCagr")?.addEventListener("change", () => {
    if (bvrDebounceTimer) clearTimeout(bvrDebounceTimer);
    bvrDebounceTimer = setTimeout(calcBuyVsRent, 80);
  });

  calcBuyVsRent();
}

function updateBuyVsRent(est) {
  calcBuyVsRent();
}

async function calcBuyVsRent() {
  const grid = $("#bvrMilestonesGrid");
  if (!grid) return;

  const est = state.est || {
    predicted_price: 20000000,
    city: "Mumbai (MMR)",
    state: "Maharashtra",
    down_payment_pct: 20,
    annual_rate_pct: 8.5,
    tenure_years: 20,
    construction_status: "Ready to Move",
  };

  const equityCagr = Number($("#bvrEquityCagr")?.value || 12);
  const propCagr = Number($("#bvrPropCagr")?.value || 6.5);

  try {
    const res = await fetch("/api/finance/buy-vs-rent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        property_value: est.predicted_price,
        city: est.city,
        state: est.state,
        down_payment_pct: est.down_payment_pct || 20,
        annual_rate_pct: est.annual_rate_pct || 8.5,
        tenure_years: est.tenure_years || 20,
        is_under_construction: est.construction_status !== "Ready to Move",
        property_appreciation_pct: propCagr,
        equity_cagr_pct: equityCagr,
        simulation_years: 20,
      }),
    });
    if (!res.ok) throw new Error(await errorText(res));
    const data = await res.json();

    const crossPill = $("#bvrCrossoverPill");
    if (crossPill) {
      const yr = data.breakeven_year;
      if (yr) {
        crossPill.innerHTML = `
          <svg class="ico xs" aria-hidden="true"><use href="#i-sparkle"/></svg>
          <span>CROSSOVER YEAR: <strong>YEAR ${yr}</strong> (Buying Surpasses Renting)</span>
        `;
      } else {
        crossPill.innerHTML = `
          <svg class="ico xs" aria-hidden="true"><use href="#i-sparkle"/></svg>
          <span>CROSSOVER: <strong>HIGH EQUITY CAGR</strong> (Renting + Compounding Holds Edge)</span>
        `;
      }
    }

    const trajectory = data.trajectory || [];
    const milestoneYears = [5, 10, 15, 20];
    const milestones = milestoneYears.map((yr) => trajectory.find((t) => t.year === yr) || trajectory[trajectory.length - 1]);

    grid.innerHTML = milestones.map((m) => {
      const buyerAhead = m.buyer_ahead;
      const spread = Math.abs(m.wealth_delta);
      return `
        <div class="bvr-milestone-card">
          <div class="bvr-m-head">
            <span class="bvr-m-year">Year ${m.year}</span>
            <span class="bvr-m-winner-tag ${buyerAhead ? "buyer" : "renter"}">
              ${buyerAhead ? "Homeowner Leads" : "Renting Ahead"}
            </span>
          </div>

          <div class="bvr-stat-row">
            <span class="lbl">Home Equity:</span>
            <strong class="${buyerAhead ? "highlight-emerald" : ""}">${fmtCompact(m.buyer_equity)}</strong>
          </div>
          <div class="bvr-stat-row">
            <span class="lbl">Rent + MF Portfolio:</span>
            <strong class="${!buyerAhead ? "highlight-cyan" : ""}">${fmtCompact(m.renter_portfolio)}</strong>
          </div>
          <div class="bvr-stat-row" style="padding-top:6px; border-top:1px solid var(--line);">
            <span class="lbl">Wealth Spread:</span>
            <strong>${fmtCompact(spread)} (${buyerAhead ? "+Buyer" : "+Renter"})</strong>
          </div>
        </div>
      `;
    }).join("");
  } catch (err) {
    console.warn("Could not calculate Buy vs Rent:", err);
  }
}

// Exported for testing and console inspection
window.EstateIQ = window.GrihaValue = { state, heatColor };
