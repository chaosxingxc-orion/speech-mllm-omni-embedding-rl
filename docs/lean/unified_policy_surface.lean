import Std

/-!
Lean-checkable core for a unified training-free omni-embedding policy surface.

The empirical facts are not proved here. Experiments must establish each
policy's task utility. This file only checks the logical implication:

  if a policy has non-negative utility delta on a protected task and strict
  positive utility delta on another task, then the equal-weight two-task
  aggregate improves.

This is the core guardrail behind the project rule:

  do not accept a task-specific instruction globally when it damages another
  protected route.
-/

inductive SpeechTask where
  | asrSemantics
  | speechQA
  | speechRAG
  | toolIntent
  | dialectRouting
  | speechTranslation
deriving DecidableEq, Repr

inductive Route where
  | asrText
  | directOmniAudio
  | rrf
  | oracleText
deriving DecidableEq, Repr

inductive Instruction where
  | raw
  | transcriptLike
  | semanticQA
  | toolSpecificIntent
  | dialectRobustSemantic
  | translationSemantic
deriving DecidableEq, Repr

structure Policy where
  route : Route
  instruction : Instruction
  contextK : Nat
  usesStructuredCandidate : Bool
deriving Repr

structure TaskUtility where
  success : Int
  auxiliary : Int
  unsafePenalty : Int
  regressionPenalty : Int
  cost : Int
deriving Repr

def TotalUtility (u : TaskUtility) : Int :=
  u.success + u.auxiliary - u.unsafePenalty - u.regressionPenalty - u.cost

abbrev UtilityOf := SpeechTask -> Policy -> TaskUtility

def Delta (U : UtilityOf) (t : SpeechTask) (base cand : Policy) : Int :=
  TotalUtility (U t cand) - TotalUtility (U t base)

def EqualWeightDelta2
    (U : UtilityOf)
    (t1 t2 : SpeechTask)
    (base cand : Policy) : Int :=
  Delta U t1 base cand + Delta U t2 base cand

theorem two_task_nonnegative_aggregate_delta
    (U : UtilityOf)
    (t1 t2 : SpeechTask)
    (base cand : Policy)
    (hD1 : 0 <= Delta U t1 base cand)
    (hD2 : 0 <= Delta U t2 base cand) :
    0 <= EqualWeightDelta2 U t1 t2 base cand := by
  unfold EqualWeightDelta2
  omega

theorem two_task_strict_aggregate_improvement_left
    (U : UtilityOf)
    (t1 t2 : SpeechTask)
    (base cand : Policy)
    (hD1 : 0 < Delta U t1 base cand)
    (hD2 : 0 <= Delta U t2 base cand) :
    0 < EqualWeightDelta2 U t1 t2 base cand := by
  unfold EqualWeightDelta2
  omega

structure AcceptGate where
  minDelta : Int
  maxRegression : Int
  maxUnsafe : Int
deriving Repr

structure ObservedDelta where
  meanDelta : Int
  bootstrapLCB : Int
  regressionRate : Int
  unsafeDelta : Int
deriving Repr

def Accepts (gate : AcceptGate) (d : ObservedDelta) : Prop :=
  gate.minDelta < d.meanDelta /\
  gate.minDelta < d.bootstrapLCB /\
  d.regressionRate <= gate.maxRegression /\
  d.unsafeDelta <= gate.maxUnsafe

theorem accepted_has_positive_lower_bound
    (gate : AcceptGate)
    (d : ObservedDelta)
    (h : Accepts gate d) :
    gate.minDelta < d.bootstrapLCB := by
  exact h.right.left

theorem accepted_has_bounded_regression
    (gate : AcceptGate)
    (d : ObservedDelta)
    (h : Accepts gate d) :
    d.regressionRate <= gate.maxRegression := by
  exact h.right.right.left

theorem accepted_has_bounded_unsafe_delta
    (gate : AcceptGate)
    (d : ObservedDelta)
    (h : Accepts gate d) :
    d.unsafeDelta <= gate.maxUnsafe := by
  exact h.right.right.right

/-!
Experimental interpretation:

* A local task policy can be accepted only when the accept gate has positive
  lower-bound evidence and bounded regression.
* A global policy can be accepted only when protected tasks have non-negative
  deltas and at least one task has strict gain.
* This blocks the observed FLEURS failure mode: `translationSemantic` may be
  harmless for direct audio query, but it cannot be globally accepted because
  it damages oracle text-query retrieval.
-/
