import Std

/-!
Lean-checkable skeleton for the V3 margin-gated frozen-omni policy.

The statistical claim about confidence intervals lives in the surrounding
method note.  This file checks the deterministic core:

* low-margin rows use the candidate action;
* high-margin rows preserve the baseline action exactly;
* therefore high-margin baseline-correct rows cannot be regressed by the gate.
-/

structure Row where
  margin : Nat
  baselineHit : Bool
  candidateHit : Bool
deriving Repr

def GatedHit (tau : Nat) (r : Row) : Bool :=
  if r.margin <= tau then r.candidateHit else r.baselineHit

theorem low_margin_uses_candidate
    (tau : Nat) (r : Row)
    (h : r.margin <= tau) :
    GatedHit tau r = r.candidateHit := by
  simp [GatedHit, h]

theorem high_margin_preserves_baseline
    (tau : Nat) (r : Row)
    (h : tau < r.margin) :
    GatedHit tau r = r.baselineHit := by
  simp [GatedHit, Nat.not_le_of_gt h]

theorem high_margin_correct_not_regressed
    (tau : Nat) (r : Row)
    (hMargin : tau < r.margin)
    (hCorrect : r.baselineHit = true) :
    GatedHit tau r = true := by
  rw [high_margin_preserves_baseline tau r hMargin]
  exact hCorrect

structure MarginGateEvidence where
  lowMarginMeanDelta : Int
  bootstrapLCB : Int
  lowMarginRegressionRate : Int
  highMarginRegressionRate : Int
deriving Repr

structure MarginGateThresholds where
  minLowMarginMeanDelta : Int
  minLCB : Int
  maxLowMarginRegressionRate : Int
  maxHighMarginRegressionRate : Int
deriving Repr

def AcceptsMarginGate
    (g : MarginGateThresholds)
    (e : MarginGateEvidence) : Prop :=
  g.minLowMarginMeanDelta < e.lowMarginMeanDelta /\
  g.minLCB < e.bootstrapLCB /\
  e.lowMarginRegressionRate <= g.maxLowMarginRegressionRate /\
  e.highMarginRegressionRate <= g.maxHighMarginRegressionRate

theorem accepted_margin_gate_has_positive_lcb
    (g : MarginGateThresholds)
    (e : MarginGateEvidence)
    (h : AcceptsMarginGate g e) :
    g.minLCB < e.bootstrapLCB := by
  exact h.right.left

theorem accepted_margin_gate_bounds_high_margin_regression
    (g : MarginGateThresholds)
    (e : MarginGateEvidence)
    (h : AcceptsMarginGate g e) :
    e.highMarginRegressionRate <= g.maxHighMarginRegressionRate := by
  exact h.right.right.right

/-!
Interpretation:

The margin threshold is selected at dataset/task level.  The gate can be used
as a regularizer around an instruction or encode-method candidate, but the
candidate remains reportable only when paired validation evidence passes the
acceptance thresholds.
-/
