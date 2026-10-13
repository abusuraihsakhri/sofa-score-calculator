// Pure input parsing shared by the browser forms and Node tests.
export function numberInput(raw, label, { optional = false, integer = false, max = null } = {}) {
  const value = String(raw ?? "").trim();
  if (!value) {
    if (optional) return null;
    throw new Error(`${label} is required.`);
  }
  const n = Number(value);
  if (!Number.isFinite(n) || n < 0 || (integer && !Number.isInteger(n)) ||
      (max !== null && n > max)) {
    throw new Error(`${label} must be a valid ${integer ? "whole" : "non-negative"} number${max !== null ? ` (up to ${max})` : ""}.`);
  }
  return n;
}

export function assessChange(current, baseline, infection) {
  if (baseline === null) return null;
  const delta = current - baseline;
  return { delta, meetsOperationalThreshold: infection === "yes" && delta >= 2,
    infectionAssessed: infection === "yes" || infection === "no" };
}
