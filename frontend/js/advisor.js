// Deterministic, grounded answers from the current estimate. Used when the
// server has no chat key, and as the offline fallback. It quotes only figures
// present in the estimate response.

import { fmtCompact, fmtPct } from "./charts.js";

export const SUGGESTIONS = [
  "How much cash do I need upfront?",
  "What is my monthly EMI?",
  "What are the stamp duty and GST?",
  "What is the RBI loan limit?",
  "Is this price high for the city?",
  "What is the likely price range?",
];

export function answerLocally(question, est) {
  if (!est) {
    return "Run an estimate first. I can only answer from its figures.";
  }
  const q = question.toLowerCase();
  const f = est.finance;
  const where = `${est.bhk} BHK in ${est.locality}, ${est.city}`;

  if (/upfront|out.?of.?pocket|cash|down ?payment|equity|how much.*(need|pay)/.test(q)) {
    return [
      `Upfront cash for ${where}:`,
      `• Down payment: ${fmtCompact(f.down_payment)}`,
      `• Stamp duty and registration: ${fmtCompact(f.stamp_duty)} (${fmtPct(f.stamp_duty_rate * 100)}, approximate)`,
      `• GST: ${f.gst === 0 ? "nil for ready-to-move" : fmtCompact(f.gst)}`,
      `Total to have in liquid funds: ${fmtCompact(f.upfront_cash)}.`,
      `The loan covers the remaining ${fmtCompact(f.loan_amount)}.`,
    ].join("\n");
  }

  if (/emi|monthly|tenure|interest|repay/.test(q)) {
    return [
      `Monthly EMI: ${fmtCompact(f.monthly_emi)} on a ${fmtCompact(f.loan_amount)} loan.`,
      `Total interest over the loan: ${fmtCompact(f.total_interest)}.`,
      `Total repayment: ${fmtCompact(f.total_repayment)}.`,
      "A longer tenure lowers the EMI but raises total interest. Use the grid above to compare.",
    ].join("\n");
  }

  if (/stamp|duty|registration|gst|tax/.test(q)) {
    return [
      `Statutory charges for ${est.state}:`,
      `• Stamp duty and registration: ${fmtCompact(f.stamp_duty)} at ${fmtPct(f.stamp_duty_rate * 100)} (approximate state rate).`,
      `• GST: ${f.gst === 0 ? "nil for ready-to-move homes with a completion certificate" : fmtCompact(f.gst) + " (upper estimate for under-construction)"}.`,
      "Women-buyer rebates, metro surcharges and cess are not included. Confirm with the state registration department before paying.",
    ].join("\n");
  }

  if (/ltv|rbi|loan limit|eligib|how much loan|max loan|cap/.test(q)) {
    const pct = fmtPct(f.ltv_ratio * 100, 0);
    return [
      `Your loan is ${fmtCompact(f.loan_amount)}, which is ${pct} of the property value.`,
      f.ltv_cap_applied
        ? "The RBI loan-to-value cap for this loan size was applied, so your down payment is higher than you requested."
        : "Your requested down payment already meets the RBI loan-to-value cap for this loan size.",
      "RBI caps are 90% for loans up to ₹30 L, 80% for ₹30 L to ₹75 L, and 75% above ₹75 L.",
    ].join("\n");
  }

  if (/range|between|interval|likely|low.*high/.test(q)) {
    const r = est.price_range;
    return [
      `Model range (P${Math.round(r.low_q * 100)} to P${Math.round(r.high_q * 100)}): ${fmtCompact(r.low)} to ${fmtCompact(r.high)}.`,
      `Point estimate: ${fmtCompact(est.predicted_price)}.`,
      "The range is a statistical band from the model, not a guarantee of sale price.",
    ].join("\n");
  }

  if (/high|low|expensive|cheap|fair|city|median|worth|value|overpriced|underpriced/.test(q)) {
    const d = est.vs_city_median_pct;
    const dir = d >= 0 ? "above" : "below";
    return [
      `At ${Math.round(est.rate_per_sqft).toLocaleString("en-IN")} per sq.ft., this unit is ${fmtPct(Math.abs(d), 0)} ${dir} the model's median for ${est.city}.`,
      `That median is ${Math.round(est.city_median_rate_per_sqft).toLocaleString("en-IN")} per sq.ft., measured on the same reference unit. Locality and condition drive most of the gap.`,
      "This is a model comparison, not a negotiation price.",
    ].join("\n");
  }

  return [
    "I can answer about: upfront cash, EMI and total interest, stamp duty and GST, the RBI loan limit, the price range, and how this price compares with the city median.",
    "Try one of the suggestions above.",
  ].join("\n");
}
