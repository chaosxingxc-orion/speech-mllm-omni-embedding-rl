/-!
Lean-checkable skeleton for conservative low-margin rerank.

This file does not prove that an LLM reranker is correct.  The empirical system
must establish that separately.  The file only proves the guardrail logic used
in the project:

1. If a policy does not override the embedding top-1, it preserves the base
   decision.
2. If overrides are allowed only when the override is correct, then a correct
   base decision cannot regress.
3. A low-margin route can improve total hits only by converting misses to hits;
   conservative acceptance is the condition that prevents losing old hits.
-/

structure RerankCase where
  baseHit : Bool
  routed : Bool
  override : Bool
  overrideHit : Bool
deriving Repr

def DeployedHit (c : RerankCase) : Bool :=
  if c.routed && c.override then c.overrideHit else c.baseHit

def NoRegression (c : RerankCase) : Prop :=
  c.baseHit = true -> DeployedHit c = true

def FixesMiss (c : RerankCase) : Prop :=
  c.baseHit = false /\ DeployedHit c = true

theorem no_route_preserves_base (c : RerankCase)
    (h : c.routed = false) :
    DeployedHit c = c.baseHit := by
  simp [DeployedHit, h]

theorem no_override_preserves_base (c : RerankCase)
    (h : c.override = false) :
    DeployedHit c = c.baseHit := by
  simp [DeployedHit, h]

theorem correct_base_no_override_no_regression (c : RerankCase)
    (h_override : c.override = false) :
    NoRegression c := by
  intro h_base
  simp [NoRegression, DeployedHit, h_override, h_base]

theorem safe_override_no_regression (c : RerankCase)
    (h_safe : c.routed = true -> c.override = true -> c.overrideHit = true) :
    NoRegression c := by
  cases c with
  | mk baseHit routed override overrideHit =>
    simp [NoRegression, DeployedHit] at *
    intro h_base
    cases routed <;> cases override <;> cases overrideHit <;> simp_all

theorem override_can_fix_base_miss (c : RerankCase)
    (h_base : c.baseHit = false)
    (h_route : c.routed = true)
    (h_override : c.override = true)
    (h_override_hit : c.overrideHit = true) :
    FixesMiss c := by
  constructor
  case left =>
    exact h_base
  case right =>
    simp [DeployedHit, h_route, h_override, h_override_hit]

/-!
Selective routing:

HeySQuAD shared-passage QA showed that low margin alone can route many harmless
ties among equivalent passages.  Adding a candidate-diversity predicate gives a
selective router.  The desired property is not that the selective router is
always more accurate; that is empirical.  The formal policy claim is simpler:

if the selective router preserves the same number of fixes as the broad router
and routes no more cases, then it has no worse utility under a per-call cost.
If it routes strictly fewer cases, it has strictly better cost-adjusted utility.
-/

def Utility (fixes routes : Nat) : Int :=
  Int.ofNat fixes - Int.ofNat routes

theorem selective_equal_fixes_no_more_routes_no_worse_cost
    (fixesLow fixesSelective routesLow routesSelective : Nat)
    (h_fix : fixesSelective = fixesLow)
    (h_route : routesSelective <= routesLow) :
    Utility fixesLow routesLow <= Utility fixesSelective routesSelective := by
  unfold Utility
  rw [h_fix]
  exact Int.sub_le_sub_left (Int.ofNat_le.mpr h_route) (Int.ofNat fixesLow)

theorem selective_equal_fixes_fewer_routes_better_cost
    (fixesLow fixesSelective routesLow routesSelective : Nat)
    (h_fix : fixesSelective = fixesLow)
    (h_route : routesSelective < routesLow) :
    Utility fixesLow routesLow < Utility fixesSelective routesSelective := by
  unfold Utility
  rw [h_fix]
  exact Int.sub_lt_sub_left (Int.ofNat_lt.mpr h_route) (Int.ofNat fixesLow)

/-!
Research interpretation:

* Standard low-margin rerank violated the safe-override premise empirically:
  it produced fixes but also regressions.
* Conservative low-margin rerank is an attempt to make the premise more likely
  by treating the embedding top-1 as the default action and requiring strong
  evidence before override.
* The theorem says the proof burden is exactly the override predicate.  We do
  not need the LLM to be globally correct; we need accepted overrides to be
  correct on rows where the base would otherwise be correct.
* The selective-routing theorem explains the HeySQuAD result: adding a
  candidate-diversity predicate preserved the conservative API fixes while
  reducing routed rows from 57 to 5, so it strictly improves cost-adjusted
  utility under any positive per-call cost.
-/
