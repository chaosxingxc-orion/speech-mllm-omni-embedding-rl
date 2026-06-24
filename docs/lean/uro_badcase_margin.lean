/-!
Lean-checkable skeleton for the URO-Bench QA/reasoning bad-case diagnosis.

The empirical numbers are outside Lean.  This file only formalizes the logical
claims used by the research note:

1. Audio-side instruction can help only by increasing the positive-vs-negative
   score margin.
2. If candidate text is not discriminative, query-side instruction alone is not
   enough; a candidate-side wrapper or a task gate must increase margin.
3. A two-stage task gate cannot hurt a sample when the gold candidate is kept
   and all removed candidates scored above the gold candidate.
-/

structure RetrievalState where
  goldScore : Int
  topNegativeScore : Int
deriving Repr

def Margin (s : RetrievalState) : Int :=
  s.goldScore - s.topNegativeScore

def HitAt1 (s : RetrievalState) : Prop :=
  0 < Margin s

structure Transformation where
  goldGain : Int
  topNegativeGain : Int
deriving Repr

def Apply (s : RetrievalState) (t : Transformation) : RetrievalState :=
  { goldScore := s.goldScore + t.goldGain
    topNegativeScore := s.topNegativeScore + t.topNegativeGain }

theorem hit_from_positive_margin (s : RetrievalState) :
    0 < Margin s -> HitAt1 s := by
  intro h
  exact h

theorem transformation_improves_margin
    (s : RetrievalState)
    (t : Transformation)
    (h : t.topNegativeGain < t.goldGain) :
    Margin s < Margin (Apply s t) := by
  simp [Margin, Apply]
  omega

theorem rescued_if_gain_exceeds_deficit
    (s : RetrievalState)
    (t : Transformation)
    (h_gain : 0 < Margin s + (t.goldGain - t.topNegativeGain)) :
    HitAt1 (Apply s t) := by
  have h_gain' :
      0 < s.goldScore - s.topNegativeScore + (t.goldGain - t.topNegativeGain) := by
    simpa [Margin] using h_gain
  simp [HitAt1, Margin, Apply]
  omega

/- Candidate-side insufficiency:

If a transformation changes only the query side but does not increase the gold
candidate more than the top negative candidate, it cannot improve the margin.
This models URO cases where the target is only "B" or a very short span; the
candidate embedding itself carries too little discriminative information.
-/
theorem no_margin_gain_without_relative_gain
    (s : RetrievalState)
    (t : Transformation)
    (h : t.goldGain <= t.topNegativeGain) :
    Margin (Apply s t) <= Margin s := by
  simp [Margin, Apply]
  omega

/- Task gate:

`removedGap` is the amount by which removed cross-task distractors exceeded the
best remaining negative.  If the gate keeps the gold candidate and removes a
negative that was above the gold candidate, the effective top-negative score is
lower and margin increases.
-/
structure TaskGate where
  keepsGold : Bool
  removedGap : Int
deriving Repr

def ApplyGate (s : RetrievalState) (g : TaskGate) : RetrievalState :=
  if g.keepsGold then
    { goldScore := s.goldScore
      topNegativeScore := s.topNegativeScore - g.removedGap }
  else s

theorem gold_preserving_gate_improves_margin
    (s : RetrievalState)
    (g : TaskGate)
    (hkeep : g.keepsGold = true)
    (hgap : 0 < g.removedGap) :
    Margin s < Margin (ApplyGate s g) := by
  simp [Margin, ApplyGate, hkeep]
  omega

theorem gate_rescues_when_gap_exceeds_deficit
    (s : RetrievalState)
    (g : TaskGate)
    (hkeep : g.keepsGold = true)
    (h : 0 < Margin s + g.removedGap) :
    HitAt1 (ApplyGate s g) := by
  have h' : 0 < s.goldScore - s.topNegativeScore + g.removedGap := by
    simpa [Margin] using h
  simp [HitAt1, Margin, ApplyGate, hkeep]
  omega

/- Research interpretation:

* `policy_grounding` is useful when it increases gold-vs-distractor margin.
* If errors remain because the candidate side is under-specified, use candidate
  wrappers or answer cards.
* If errors remain because distractors come from another URO subtask, use a
  task gate before same-task retrieval.
-/
