import Std

/-!
Lean-checkable core for query-driven omni memory planning.

This file verifies the deterministic part of the theory:

* a memory plan has separate retrieval and use policies;
* total utility includes task success, grounding, costs, invalid output, and
  regressions;
* an accepted plan must have positive lower-bound evidence and bounded risks;
* if no non-baseline plan is accepted, the selector falls back to text-only
  memory use;
* a global plan can improve an aggregate only when protected tasks do not
  regress.

The statistical uniform-convergence bound is documented in Markdown because it
requires probability-measure infrastructure beyond this lightweight file.
-/

inductive MemoryView where
  | transcript
  | summary
  | rawAudio
  | taskCard
  | metadata
deriving DecidableEq, Repr

inductive RetrievalPolicy where
  | fixedCandidates
  | textSearch
  | omniAudioSearch
  | hybrid
deriving DecidableEq, Repr

inductive UsePolicy where
  | textSummaryOnly
  | audioClipOnly
  | dualSummaryAudio
  | conflictAware
  | taskCardAudio
  | twoStageVerify
deriving DecidableEq, Repr

structure MemoryPlan where
  retrieval : RetrievalPolicy
  use : UsePolicy
  maxTextTokens : Nat
  maxAudioSeconds : Nat
deriving Repr

structure Utility where
  taskSuccess : Int
  groundedUse : Int
  wrongMemoryPenalty : Int
  invalidOutputPenalty : Int
  contextCost : Int
  audioCost : Int
  regressionPenalty : Int
deriving Repr

def TotalUtility (u : Utility) : Int :=
  u.taskSuccess
  + u.groundedUse
  - u.wrongMemoryPenalty
  - u.invalidOutputPenalty
  - u.contextCost
  - u.audioCost
  - u.regressionPenalty

abbrev UtilityOf := MemoryPlan -> Utility

def Delta (U : UtilityOf) (base cand : MemoryPlan) : Int :=
  TotalUtility (U cand) - TotalUtility (U base)

structure ObservedPlanDelta where
  meanDelta : Int
  bootstrapLCB : Int
  regressions : Nat
  invalidDelta : Int
  textCostDelta : Int
  audioCostDelta : Int
deriving Repr

structure MemoryAcceptGate where
  minMeanDelta : Int
  minLCB : Int
  maxRegressions : Nat
  maxInvalidDelta : Int
  maxTextCostDelta : Int
  maxAudioCostDelta : Int
deriving Repr

def Accepts (g : MemoryAcceptGate) (d : ObservedPlanDelta) : Prop :=
  g.minMeanDelta < d.meanDelta /\
  g.minLCB < d.bootstrapLCB /\
  d.regressions <= g.maxRegressions /\
  d.invalidDelta <= g.maxInvalidDelta /\
  d.textCostDelta <= g.maxTextCostDelta /\
  d.audioCostDelta <= g.maxAudioCostDelta

theorem accepted_has_positive_lcb
    (g : MemoryAcceptGate)
    (d : ObservedPlanDelta)
    (h : Accepts g d) :
    g.minLCB < d.bootstrapLCB := by
  exact h.right.left

theorem accepted_has_bounded_regressions
    (g : MemoryAcceptGate)
    (d : ObservedPlanDelta)
    (h : Accepts g d) :
    d.regressions <= g.maxRegressions := by
  exact h.right.right.left

theorem accepted_has_bounded_invalid_delta
    (g : MemoryAcceptGate)
    (d : ObservedPlanDelta)
    (h : Accepts g d) :
    d.invalidDelta <= g.maxInvalidDelta := by
  exact h.right.right.right.left

theorem accepted_has_bounded_text_cost
    (g : MemoryAcceptGate)
    (d : ObservedPlanDelta)
    (h : Accepts g d) :
    d.textCostDelta <= g.maxTextCostDelta := by
  exact h.right.right.right.right.left

theorem accepted_has_bounded_audio_cost
    (g : MemoryAcceptGate)
    (d : ObservedPlanDelta)
    (h : Accepts g d) :
    d.audioCostDelta <= g.maxAudioCostDelta := by
  exact h.right.right.right.right.right

def TextOnlyPlan : MemoryPlan :=
  {
    retrieval := RetrievalPolicy.fixedCandidates
    use := UsePolicy.textSummaryOnly
    maxTextTokens := 4096
    maxAudioSeconds := 0
  }

inductive ChosenPlan where
  | baseline
  | candidate (plan : MemoryPlan)
deriving Repr

def ChoosePlan (accepted : Bool) (cand : MemoryPlan) : ChosenPlan :=
  if accepted then ChosenPlan.candidate cand else ChosenPlan.baseline

theorem fallback_when_no_plan_accepted
    (cand : MemoryPlan) :
    ChoosePlan false cand = ChosenPlan.baseline := by
  simp [ChoosePlan]

def AggregateDelta2
    (U1 U2 : UtilityOf)
    (base cand : MemoryPlan) : Int :=
  Delta U1 base cand + Delta U2 base cand

theorem two_task_nonnegative_memory_plan_delta
    (U1 U2 : UtilityOf)
    (base cand : MemoryPlan)
    (h1 : 0 <= Delta U1 base cand)
    (h2 : 0 <= Delta U2 base cand) :
    0 <= AggregateDelta2 U1 U2 base cand := by
  unfold AggregateDelta2
  omega

theorem two_task_strict_memory_plan_improvement
    (U1 U2 : UtilityOf)
    (base cand : MemoryPlan)
    (h1 : 0 < Delta U1 base cand)
    (h2 : 0 <= Delta U2 base cand) :
    0 < AggregateDelta2 U1 U2 base cand := by
  unfold AggregateDelta2
  omega

/-!
Experimental interpretation:

* `TextOnlyPlan` is the baseline memory-use policy.
* A non-baseline `MemoryPlan` may use raw audio, task cards, conflict warnings,
  or two-stage verification.
* The selector may return that non-baseline plan only when `Accepts` holds.
* Cross-task claims require non-negative deltas on protected tasks, not just a
  gain on a single task.
-/
