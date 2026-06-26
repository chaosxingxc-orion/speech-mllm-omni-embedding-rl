import Std

/-!
Lean-checkable skeleton for task-level frozen-omni policy selection.

The probability bound used in the paper note is a statistical theorem outside
this lightweight file.  This file checks the deterministic acceptance logic:

* accepted evidence has positive lower-bound gain and bounded regression;
* positive affine score transforms preserve pairwise ordering;
* if no non-raw action is accepted, the selector may safely fall back to raw.
-/

structure PolicyEvidence where
  meanDelta : Int
  bootstrapLCB : Int
  regressionRate : Int
  worstGroupDelta : Int
deriving Repr

structure SelectorGate where
  minMeanDelta : Int
  minLCB : Int
  maxRegressionRate : Int
  minWorstGroupDelta : Int
deriving Repr

def Accepts (g : SelectorGate) (e : PolicyEvidence) : Prop :=
  g.minMeanDelta < e.meanDelta /\
  g.minLCB < e.bootstrapLCB /\
  e.regressionRate <= g.maxRegressionRate /\
  g.minWorstGroupDelta <= e.worstGroupDelta

theorem accepted_has_positive_lcb
    (g : SelectorGate)
    (e : PolicyEvidence)
    (h : Accepts g e) :
    g.minLCB < e.bootstrapLCB := by
  exact h.right.left

theorem accepted_has_bounded_regression
    (g : SelectorGate)
    (e : PolicyEvidence)
    (h : Accepts g e) :
    e.regressionRate <= g.maxRegressionRate := by
  exact h.right.right.left

theorem accepted_has_bounded_worst_group
    (g : SelectorGate)
    (e : PolicyEvidence)
    (h : Accepts g e) :
    g.minWorstGroupDelta <= e.worstGroupDelta := by
  exact h.right.right.right

theorem positive_affine_preserves_lt
    (a b alpha beta : Int)
    (hAlpha : 0 < alpha)
    (h : a < b) :
    alpha * a + beta < alpha * b + beta := by
  exact Int.add_lt_add_right (Int.mul_lt_mul_of_pos_left h hAlpha) beta

inductive Action where
  | raw
  | candidate (name : String)
deriving DecidableEq, Repr

def ChosenAction (acceptedNonRaw : Bool) (name : String) : Action :=
  if acceptedNonRaw then Action.candidate name else Action.raw

theorem fallback_when_no_non_raw_accepted
    (name : String) :
    ChosenAction false name = Action.raw := by
  simp [ChosenAction]

/-!
Interpretation:

The implementation may search over a finite set of dataset/task-level actions,
but it should only return a non-raw action when `Accepts` holds on the selection
split.  Otherwise the conservative fallback is raw.
-/
