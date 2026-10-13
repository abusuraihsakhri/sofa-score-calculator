import { numberInput, assessChange } from "./input.mjs";

const PYODIDE_BASE = "https://cdn.jsdelivr.net/pyodide/v0.28.0/full/";
const status = document.getElementById("runtime-status");
const forms = [...document.querySelectorAll("form[data-mode]")];
let pyodide;

function field(form, name, label, options = {}) {
  const control = form.elements.namedItem(name);
  return numberInput(control?.value, label, options);
}
function makeResult(targetId, message, error = false) {
  const element = document.getElementById(targetId);
  element.textContent = message;
  element.classList.toggle("error", error);
  element.hidden = false;
}
function scoreInPython(functionName, data) {
  // JSON is passed as a Python global, never spliced into executable source.
  pyodide.globals.set("payload_json", JSON.stringify(data));
  return JSON.parse(pyodide.runPython(
    `json.dumps(${functionName}(**json.loads(payload_json)).to_dict())`
  ));
}
function readSofa(form) {
  const selected = form.querySelector('input[name="mechanical_ventilation"]:checked');
  if (!selected) throw new Error("Select whether respiratory support is being used.");
  const result = {
    pao2_fio2: field(form, "pao2_fio2", "PaO2/FiO2"),
    mechanical_ventilation: selected.value === "yes",
    platelets: field(form, "platelets", "Platelets"),
    bilirubin: field(form, "bilirubin", "Bilirubin"),
    map_mmhg: field(form, "map_mmhg", "MAP", { optional: true }),
    dopamine: field(form, "dopamine", "Dopamine", { optional: true }),
    dobutamine: field(form, "dobutamine", "Dobutamine", { optional: true }),
    norepinephrine: field(form, "norepinephrine", "Norepinephrine", { optional: true }),
    epinephrine: field(form, "epinephrine", "Epinephrine", { optional: true }),
    gcs: field(form, "gcs", "GCS", { integer: true, max: 15 }),
    creatinine: field(form, "creatinine", "Creatinine", { optional: true }),
    urine_output_ml_day: field(form, "urine_output_ml_day", "Urine output", { optional: true }),
  };
  if (result.gcs < 3) throw new Error("GCS must be 3–15.");
  if (result.creatinine === null && result.urine_output_ml_day === null) {
    throw new Error("Provide creatinine and/or 24-hour urine output.");
  }
  if (result.map_mmhg === null &&
      !["dopamine", "dobutamine", "norepinephrine", "epinephrine"]
        .some((key) => result[key] !== null && result[key] > 0)) {
    throw new Error("Provide MAP or an administered vasoactive drug dose.");
  }
  return result;
}
function runSofa(form) {
  const params = readSofa(form);
  const score = scoreInPython("calculate_sofa", params);
  const baseline = field(form, "baseline", "Baseline SOFA",
    { optional: true, integer: true, max: 24 });
  const infection = form.elements.namedItem("infection").value;
  const change = assessChange(score.total, baseline, infection);
  let interpretation = "Baseline SOFA not provided; change and Sepsis-3 threshold not assessed.";
  if (change) {
    interpretation = `Change from baseline: ${change.delta >= 0 ? "+" : ""}${change.delta}`;
    if (!change.infectionAssessed) {
      interpretation += "\nInfection status not assessed: cannot assess the operational Sepsis-3 threshold.";
    } else {
      interpretation += `\nOperational infection + SOFA increase ≥2 threshold: ${change.meetsOperationalThreshold ? "met" : "not met"} (not a clinical diagnosis or rule-out).`;
    }
  }
  makeResult("sofa-result",
    `SOFA total: ${score.total}/24\n\n` +
    `Respiratory         ${score.respiratory}/4\nCoagulation         ${score.coagulation}/4\nLiver               ${score.liver}/4\nCardiovascular      ${score.cardiovascular}/4\nCNS                 ${score.cns}/4\nRenal               ${score.renal}/4\n\n` + interpretation);
}
function runQsofa(form) {
  const params = {
    respiratory_rate: field(form, "respiratory_rate", "Respiratory rate",
      { integer: true }),
    gcs: field(form, "gcs", "GCS", { integer: true, max: 15 }),
    systolic_bp: field(form, "systolic_bp", "Systolic BP", { integer: true }),
  };
  if (params.gcs < 3) throw new Error("GCS must be 3–15.");
  const score = scoreInPython("calculate_qsofa", params);
  makeResult("qsofa-result",
    `qSOFA: ${score.score}/3\n\nRespiratory rate ≥22: ${score.respiratory_rate_ge_22 ? "Yes" : "No"}\nGCS <15:              ${score.altered_mentation ? "Yes" : "No"}\nSystolic BP ≤100:     ${score.systolic_bp_le_100 ? "Yes" : "No"}\n\n` +
    (score.score >= 2 ? "Higher risk of poor outcomes in suspected infection." :
      "Score below 2 does not exclude sepsis.") +
    "\nDo not use qSOFA alone to screen for or diagnose sepsis.");
}
for (const button of document.querySelectorAll('[role="tab"]')) {
  button.addEventListener("click", () => {
    const isSofa = button.dataset.target === "sofa-panel";
    document.getElementById("sofa-panel").hidden = !isSofa;
    document.getElementById("qsofa-panel").hidden = isSofa;
    for (const tab of document.querySelectorAll('[role="tab"]')) {
      tab.setAttribute("aria-selected", String(tab === button));
    }
  });
}
for (const form of forms) {
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    if (!pyodide) return;
    const mode = form.dataset.mode;
    try {
      if (mode === "sofa") runSofa(form);
      else runQsofa(form);
    } catch (error) {
      makeResult(mode === "sofa" ? "sofa-result" : "qsofa-result",
        error?.message || "Calculation failed.", true);
    }
  });
}
async function initialize() {
  try {
    await new Promise((resolve, reject) => {
      const script = document.createElement("script");
      script.src = PYODIDE_BASE + "pyodide.js";
      script.onload = resolve;
      script.onerror = () => reject(new Error("Cannot load the Python runtime from the CDN."));
      document.head.append(script);
    });
    pyodide = await window.loadPyodide({ indexURL: PYODIDE_BASE });
    const response = await fetch(new URL("./sofa.py", import.meta.url));
    if (!response.ok) throw new Error("Unable to load the scoring library.");
    await pyodide.runPythonAsync(await response.text());
    status.textContent = "Python engine ready. Calculations stay in this browser.";
    status.dataset.state = "ready";
    for (const form of forms) form.querySelector('button[type="submit"]').disabled = false;
  } catch (error) {
    status.textContent = `Python engine unavailable: ${error.message}. Internet access is required on first load.`;
    status.dataset.state = "error";
  }
}
initialize();
