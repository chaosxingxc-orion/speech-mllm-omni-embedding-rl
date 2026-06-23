/-!
Lean-checkable core for the conditioning / utility argument.

This file does not prove empirical premises such as "CREMA-D is diagonal
dominant". Experiments must establish those premises. The file only checks that
our claimed implications follow from the stated premises.
-/

inductive Factor where
  | content
  | emotion
  | speaker
  | ragGrounding
  | toolIntent
  | transcriptLiteral
deriving DecidableEq, Repr

inductive Conditioning where
  | baseline
  | content
  | emotion
  | speaker
  | rag
  | tool
  | transcriptLike
  | dialectSemantic
deriving DecidableEq, Repr

abbrev Reward := Conditioning -> Factor -> Int

def Intended : Conditioning -> Option Factor
  | Conditioning.content => some Factor.content
  | Conditioning.emotion => some Factor.emotion
  | Conditioning.speaker => some Factor.speaker
  | Conditioning.rag => some Factor.ragGrounding
  | Conditioning.tool => some Factor.toolIntent
  | Conditioning.transcriptLike => some Factor.transcriptLiteral
  | _ => none

def Exposes (R : Reward) (c : Conditioning) (f : Factor) : Prop :=
  R Conditioning.baseline f < R c f

def BestFor
    (R : Reward)
    (Arms : Conditioning -> Prop)
    (c : Conditioning)
    (f : Factor) : Prop :=
  Arms c /\
  Intended c = some f /\
  forall c', Arms c' -> R c' f <= R c f

def DiagonalDominant
    (R : Reward)
    (Arms : Conditioning -> Prop)
    (Factors : Factor -> Prop) : Prop :=
  forall f, Factors f -> exists c, BestFor R Arms c f

theorem diagonal_supports_factor_claim
    (R : Reward)
    (Arms : Conditioning -> Prop)
    (Factors : Factor -> Prop)
    (hdiag : DiagonalDominant R Arms Factors) :
    forall f, Factors f -> exists c, BestFor R Arms c f := by
  exact hdiag

structure Utility where
  success : Int
  auxiliary : Int
  penalty : Int
  cost : Int
  complexity : Int
deriving Repr

def TotalUtility (u : Utility) : Int :=
  u.success + u.auxiliary - u.penalty - u.cost - u.complexity

abbrev TaskUtility := Conditioning -> Factor -> Utility

def ImprovesTask (U : TaskUtility) (c : Conditioning) (f : Factor) : Prop :=
  TotalUtility (U Conditioning.baseline f) < TotalUtility (U c f)

theorem downstream_gain_from_bridge
    (R : Reward)
    (U : TaskUtility)
    (c : Conditioning)
    (f : Factor)
    (_h_exposes : Exposes R c f)
    (h_bridge : ImprovesTask U c f) :
    ImprovesTask U c f := by
  exact h_bridge

structure AcceptConfig where
  minGain : Int
  maxDrift : Int
  maxRegression : Int
deriving Repr

def Accept
    (cfg : AcceptConfig)
    (valReward : Conditioning -> Int)
    (drift : Conditioning -> Conditioning -> Int)
    (regressionRate : Conditioning -> Int)
    (old new : Conditioning) : Prop :=
  valReward old + cfg.minGain < valReward new /\
  drift old new <= cfg.maxDrift /\
  regressionRate new <= cfg.maxRegression

theorem accepted_policy_has_required_validation_gain
    (cfg : AcceptConfig)
    (valReward : Conditioning -> Int)
    (drift : Conditioning -> Conditioning -> Int)
    (regressionRate : Conditioning -> Int)
    (old new : Conditioning)
    (h : Accept cfg valReward drift regressionRate old new) :
    valReward old + cfg.minGain < valReward new := by
  exact h.left

theorem accepted_policy_has_bounded_regression
    (cfg : AcceptConfig)
    (valReward : Conditioning -> Int)
    (drift : Conditioning -> Conditioning -> Int)
    (regressionRate : Conditioning -> Int)
    (old new : Conditioning)
    (h : Accept cfg valReward drift regressionRate old new) :
    regressionRate new <= cfg.maxRegression := by
  exact h.right.right
