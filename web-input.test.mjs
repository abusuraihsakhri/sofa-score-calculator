import test from "node:test";
import assert from "node:assert/strict";
import { numberInput, assessChange } from "./input.mjs";

test("valid numeric inputs retain boundaries", () => {
  assert.equal(numberInput("0", "value"), 0);
  assert.equal(numberInput("0.1", "dose"), 0.1);
  assert.equal(numberInput(" 15 ", "GCS", { integer: true, max: 15 }), 15);
  assert.equal(numberInput("", "MAP", { optional: true }), null);
});
test("missing, non-finite, negative and fractional integer inputs fail", () => {
  for (const raw of ["", "NaN", "Infinity", "-1", "1e999", "abc"]) {
    assert.throws(() => numberInput(raw, "value"));
  }
  assert.throws(() => numberInput("14.9", "GCS", { integer: true, max: 15 }));
  assert.throws(() => numberInput("16", "GCS", { integer: true, max: 15 }));
});
test("SOFA delta requires known baseline and infection for interpretation", () => {
  assert.equal(assessChange(5, null, "yes"), null);
  assert.deepEqual(assessChange(4, 2, "yes"),
    { delta: 2, meetsOperationalThreshold: true, infectionAssessed: true });
  assert.equal(assessChange(4, 2, "no").meetsOperationalThreshold, false);
  assert.equal(assessChange(4, 2, "").infectionAssessed, false);
});
