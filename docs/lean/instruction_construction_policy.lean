import Std

/-!
Lean-checkable skeleton for task-conditioned audio instruction construction.

The file deliberately does not claim that a natural-language instruction will
improve a frozen embedding model.  Experiments estimate that.  Lean only checks
the decision logic used by the project:

* positive retrieval margin is sufficient for top-1 correctness;
* accepted policy evidence has positive lower-bound gain and bounded
  regression;
* when two task families have conflicting preferences, no single instruction
  among the two can dominate both.
-/

inductive SemanticTask where
  | asrTranscript
  | ragGrounding
  | toolIntent
  | translation
deriving DecidableEq, Repr

inductive EquivalenceKind where
  | literalTranscript
  | groundedAnswer
  | executableIntent
  | crossLingualMeaning
deriving DecidableEq, Repr

structure InstructionCard where
  task : SemanticTask
  targetEquivalence : EquivalenceKind
  hasBoundaryCondition : Bool
  hasNegativeWarning : Bool
deriving Repr

structure RetrievalScores where
  positive : Int
  hardestNegative : Int
deriving Repr

def Margin (s : RetrievalScores) : Int :=
  s.positive - s.hardestNegative

def Top1Correct (s : RetrievalScores) : Prop :=
  0 < Margin s

theorem positive_margin_implies_top1
    (s : RetrievalScores)
    (h : 0 < Margin s) :
    Top1Correct s := by
  exact h

structure PolicyEvidence where
  pairedMeanDelta : Int
  bootstrapLCB : Int
  regressionRate : Int
  drift : Int
deriving Repr

structure RobustGate where
  minDelta : Int
  maxRegressionRate : Int
  maxDrift : Int
deriving Repr

def Accepts (g : RobustGate) (e : PolicyEvidence) : Prop :=
  g.minDelta < e.pairedMeanDelta /\
  g.minDelta < e.bootstrapLCB /\
  e.regressionRate <= g.maxRegressionRate /\
  e.drift <= g.maxDrift

theorem accepted_has_positive_lcb
    (g : RobustGate)
    (e : PolicyEvidence)
    (h : Accepts g e) :
    g.minDelta < e.bootstrapLCB := by
  exact h.right.left

theorem accepted_has_bounded_regression
    (g : RobustGate)
    (e : PolicyEvidence)
    (h : Accepts g e) :
    e.regressionRate <= g.maxRegressionRate := by
  exact h.right.right.left

theorem accepted_has_bounded_drift
    (g : RobustGate)
    (e : PolicyEvidence)
    (h : Accepts g e) :
    e.drift <= g.maxDrift := by
  exact h.right.right.right

/-!
No universal instruction among two conflicting policies.

`Better t p q` means policy `p` is strictly preferred to policy `q` for task
`t`, under an empirically defined task utility.  The theorem states that if ASR
prefers an ASR-style instruction over a QA-style instruction, while RAG prefers
the QA-style instruction over the ASR-style instruction, then neither of these
two policies can strictly dominate the other on both tasks.
-/

theorem no_two_policy_universal_under_conflict
    (Policy : Type)
    (Better : SemanticTask -> Policy -> Policy -> Prop)
    (asrInstr qaInstr : Policy)
    (asym : forall t p q, Better t p q -> Not (Better t q p))
    (asrPrefersAsr : Better SemanticTask.asrTranscript asrInstr qaInstr)
    (ragPrefersQa : Better SemanticTask.ragGrounding qaInstr asrInstr) :
    Not (
      (Better SemanticTask.asrTranscript qaInstr asrInstr /\
       Better SemanticTask.ragGrounding qaInstr asrInstr) \/
      (Better SemanticTask.asrTranscript asrInstr qaInstr /\
       Better SemanticTask.ragGrounding asrInstr qaInstr)
    ) := by
  intro h
  cases h with
  | inl qaDominates =>
      exact asym SemanticTask.asrTranscript asrInstr qaInstr asrPrefersAsr qaDominates.left
  | inr asrDominates =>
      exact asym SemanticTask.ragGrounding qaInstr asrInstr ragPrefersQa asrDominates.right

/-!
Experimental interpretation:

* URO QA can accept a grounding-style instruction only after validation shows
  positive lower-bound gain and bounded regression.
* HeySQuAD answerable validation rejects the same instruction because observed
  paired gain is negative.
* The conflict theorem explains why this is expected rather than embarrassing:
  task families can induce different equivalence relations, so the project
  should construct and validate task-conditioned instructions instead of
  searching for a universal prompt.
-/
