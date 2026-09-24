/**
 * Dispatch Desk frontend logic.
 *
 * No build step, no framework — plain fetch + DOM. That's a deliberate
 * choice for a small internal tool like this one: zero install friction,
 * and every line here is something you can point to and explain directly
 * in an interview.
 *
 * Point this at a different backend (e.g. a deployed one) by setting
 * `window.CHURN_API_BASE = "https://your-api.example.com"` in a <script>
 * tag *before* this file loads.
 */

const API_BASE = window.CHURN_API_BASE || "http://localhost:8000";

// Mirrors backend/app/model.py exactly. Used only if /options can't be
// reached, so the form still works while you get the backend running.
const FALLBACK_OPTIONS = {
  occupations: ["Student", "Employee", "Self Employed", "House wife"],
  monthly_incomes: [
    "No Income",
    "Below Rs.10000",
    "10001-25000",
    "25001 to 50000",
    "More than 50000",
  ],
  rating_scale: ["Strongly agree", "Agree", "Neutral", "Disagree", "Strongly disagree"],
  rating_fields: [
    { field: "ease_and_convenient", label: "ease and convenient" },
    { field: "good_food_quality", label: "good food quality" },
    { field: "more_offers_and_discount", label: "more offers and discount" },
    { field: "good_tracking_system", label: "good tracking system" },
    { field: "late_delivery", label: "late delivery" },
    { field: "bad_past_experience", label: "bad past experience" },
    { field: "wrong_order_delivered", label: "wrong order delivered" },
    { field: "unaffordable", label: "unaffordable" },
    { field: "long_delivery_time", label: "long delivery time" },
    { field: "missing_item", label: "missing item" },
  ],
};

const SCALE_ABBREVIATION = {
  "Strongly agree": "SA",
  Agree: "A",
  Neutral: "N",
  Disagree: "D",
  "Strongly disagree": "SD",
};

const RISK_COLOR = {
  Low: "#1f8a5f",
  Moderate: "#a9782a",
  High: "#c0512f",
  Critical: "#b6362a",
};

const CIRCUMFERENCE = 2 * Math.PI * 52; // matches the SVG circle r=52

// Holds exactly the fields the /predict endpoint expects.
const state = {
  occupation: null,
  monthly_income: null,
};

let ratingFieldsInUse = FALLBACK_OPTIONS.rating_fields;

// ---------------------------------------------------------------------
// DOM references
// ---------------------------------------------------------------------
const el = {
  statusDot: document.getElementById("status-dot"),
  statusText: document.getElementById("status-text"),
  occupationSelect: document.getElementById("occupation"),
  incomeSelect: document.getElementById("income"),
  ratingRows: document.getElementById("rating-rows"),
  runBtn: document.getElementById("run-check"),
  formError: document.getElementById("form-error"),
  slotIdle: document.getElementById("slot-idle"),
  slotError: document.getElementById("slot-error"),
  slotErrorDetail: document.getElementById("slot-error-detail"),
  receipt: document.getElementById("receipt"),
  ticketNo: document.getElementById("ticket-no"),
  receiptTable: document.getElementById("receipt-table"),
  gaugeFill: document.getElementById("gauge-fill"),
  gaugeValue: document.getElementById("gauge-value"),
  riskLevel: document.getElementById("risk-level"),
  demoNote: document.getElementById("demo-note"),
  barcode: document.getElementById("barcode"),
  stamp: document.getElementById("stamp"),
  footerApiBase: document.getElementById("footer-api-base"),
};

el.footerApiBase.textContent = `API: ${API_BASE}`;
el.gaugeFill.style.strokeDasharray = String(CIRCUMFERENCE);
el.gaugeFill.style.strokeDashoffset = String(CIRCUMFERENCE);

// ---------------------------------------------------------------------
// Boot sequence
// ---------------------------------------------------------------------
init();

async function init() {
  checkHealth();
  const options = await loadOptions();
  ratingFieldsInUse = options.rating_fields;
  buildForm(options);
}

async function checkHealth() {
  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const body = await res.json();
    if (body.model_loaded) {
      setStatus("online", "connected · trained model loaded");
    } else {
      setStatus("demo", "connected · demo fallback (no trained model found)");
    }
  } catch (err) {
    setStatus("offline", `offline · could not reach ${API_BASE}`);
  }
}

function setStatus(kind, text) {
  el.statusDot.className = `topbar__dot topbar__dot--${kind}`;
  el.statusText.textContent = text;
}

async function loadOptions() {
  try {
    const res = await fetch(`${API_BASE}/options`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (err) {
    console.warn("Falling back to built-in form options:", err);
    return FALLBACK_OPTIONS;
  }
}

// ---------------------------------------------------------------------
// Form construction
// ---------------------------------------------------------------------
function buildForm(options) {
  fillSelect(el.occupationSelect, options.occupations);
  fillSelect(el.incomeSelect, options.monthly_incomes);
  state.occupation = options.occupations[0];
  state.monthly_income = options.monthly_incomes[0];

  el.occupationSelect.addEventListener("change", (e) => {
    state.occupation = e.target.value;
  });
  el.incomeSelect.addEventListener("change", (e) => {
    state.monthly_income = e.target.value;
  });

  el.ratingRows.innerHTML = "";
  options.rating_fields.forEach(({ field, label }) => {
    state[field] = "Neutral";
    el.ratingRows.appendChild(buildRatingRow(field, label, options.rating_scale));
  });

  el.runBtn.addEventListener("click", runCheck);
}

function fillSelect(selectEl, values) {
  selectEl.innerHTML = "";
  values.forEach((value) => {
    const opt = document.createElement("option");
    opt.value = value;
    opt.textContent = value;
    selectEl.appendChild(opt);
  });
}

function buildRatingRow(field, label, scale) {
  const row = document.createElement("div");
  row.className = "rating-row";

  const labelEl = document.createElement("span");
  labelEl.className = "rating-row__label";
  labelEl.textContent = sentenceCase(label);
  row.appendChild(labelEl);

  const chips = document.createElement("div");
  chips.className = "rating-row__chips";

  scale.forEach((value) => {
    const chip = document.createElement("button");
    chip.type = "button";
    chip.className = "chip";
    chip.textContent = SCALE_ABBREVIATION[value] || value.slice(0, 2).toUpperCase();
    chip.title = value;
    chip.setAttribute("aria-label", value);
    if (value === "Neutral") chip.classList.add("is-active");

    chip.addEventListener("click", () => {
      chips.querySelectorAll(".chip").forEach((c) => c.classList.remove("is-active"));
      chip.classList.add("is-active");
      state[field] = value;
    });

    chips.appendChild(chip);
  });

  row.appendChild(chips);
  return row;
}

function sentenceCase(str) {
  return str.charAt(0).toUpperCase() + str.slice(1);
}

// ---------------------------------------------------------------------
// Submit / render result
// ---------------------------------------------------------------------
class FormValidationError extends Error {
  constructor(body) {
    super("Validation error");
    this.body = body;
  }
}

async function runCheck() {
  el.formError.hidden = true;
  el.runBtn.disabled = true;
  const originalLabel = el.runBtn.innerHTML;
  el.runBtn.innerHTML = "Printing&hellip;";

  try {
    const res = await fetch(`${API_BASE}/predict`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(state),
    });

    if (res.status === 422) {
      const body = await res.json();
      throw new FormValidationError(body);
    }
    if (!res.ok) {
      throw new Error(`API responded with HTTP ${res.status}`);
    }

    const result = await res.json();
    renderReceipt(result);
    checkHealth(); // refresh the status dot too, now that we know it's reachable
  } catch (err) {
    if (err instanceof FormValidationError) {
      el.formError.hidden = false;
      el.formError.textContent =
        "The API rejected one of the selected values — check the console for details.";
      console.error("Validation error:", err.body);
    } else {
      showSlotError(err.message);
    }
  } finally {
    el.runBtn.disabled = false;
    el.runBtn.innerHTML = originalLabel;
  }
}

function showSlotError(detail) {
  el.slotIdle.hidden = true;
  el.receipt.hidden = true;
  el.slotError.hidden = false;
  el.slotErrorDetail.innerHTML = `${detail}<br/>Start the backend
    (<code>uvicorn app.main:app --reload --port 8000</code>) and try again.`;
}

function renderReceipt(result) {
  el.slotIdle.hidden = true;
  el.slotError.hidden = true;
  el.receipt.hidden = false;

  el.ticketNo.textContent = `#${ticketNumber()}`;

  // Itemize exactly what was submitted, in the order it appears on the form.
  el.receiptTable.innerHTML = "";
  addReceiptRow("Occupation", state.occupation);
  addReceiptRow("Monthly income", state.monthly_income);
  ratingFieldsInUse.forEach(({ field, label }) => {
    addReceiptRow(sentenceCase(label), state[field]);
  });

  const pct = Math.round(result.churn_probability * 100);
  const offset = CIRCUMFERENCE * (1 - result.churn_probability);
  el.gaugeFill.style.strokeDashoffset = String(offset);
  el.gaugeFill.style.stroke = RISK_COLOR[result.risk_level] || "#1f8a5f";
  el.gaugeValue.textContent = `${pct}%`;

  el.riskLevel.textContent = `${result.risk_level} risk`;
  el.riskLevel.className = `receipt__risk-level receipt__risk-level--${result.risk_level.toLowerCase()}`;

  el.demoNote.hidden = !result.demo_mode;

  el.stamp.textContent = result.prediction;
  el.stamp.className = `stamp stamp--${result.prediction.toLowerCase()}`;

  drawBarcode(pct);

  // Restart the print-in / stamp-thud animations on every prediction,
  // even if the same elements were just shown a moment ago.
  restartAnimation(el.receipt, "receipt--enter");
  restartAnimation(el.stamp, "stamp--enter");
}

function addReceiptRow(label, value) {
  const row = document.createElement("div");
  row.className = "receipt-row";

  const labelSpan = document.createElement("span");
  labelSpan.className = "receipt-row__label";
  labelSpan.textContent = label;

  const filler = document.createElement("span");
  filler.className = "receipt-row__filler";

  const valueSpan = document.createElement("span");
  valueSpan.className = "receipt-row__value";
  valueSpan.textContent = value;

  row.append(labelSpan, filler, valueSpan);
  el.receiptTable.appendChild(row);
}

function drawBarcode(seed) {
  el.barcode.innerHTML = "";
  // A small deterministic pseudo-random sequence, seeded off the risk
  // percentage, so the barcode "looks different" per result without
  // relying on Math.random() (keeps re-renders reproducible in tests).
  let x = seed + 1;
  const next = () => {
    x = (x * 9301 + 49297) % 233280;
    return x / 233280;
  };
  for (let i = 0; i < 46; i++) {
    const bar = document.createElement("span");
    const width = 1 + Math.round(next() * 2);
    bar.style.width = `${width}px`;
    bar.style.opacity = next() > 0.15 ? "1" : "0.25";
    el.barcode.appendChild(bar);
  }
}

function restartAnimation(element, className) {
  element.classList.remove(className);
  void element.offsetWidth; // force reflow so the animation can replay
  element.classList.add(className);
}

function ticketNumber() {
  return String(Math.floor(Date.now() % 1000000)).padStart(6, "0");
}
