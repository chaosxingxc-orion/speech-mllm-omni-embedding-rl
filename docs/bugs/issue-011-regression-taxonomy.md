# Issue 011: Regression And Bad-Case Taxonomy For Accepted Controllers

This appendix summarizes remaining failures for accepted training-free
controllers.  It is generated from row-level result artifacts and is meant
to support paper writing, not to introduce new model runs.

## heysquad_packed_retrieval_use

- `n`: 200
- `original_success`: 0.28
- `packed_success`: 0.595
- `fixes`: 68
- `regressions`: 5
- `remaining_failures`: 81
- `invalid_after_packing`: 0.0

Taxonomy:
- `main_regression_mode`: packing may sharpen/shorten evidence enough that the model chooses a nearby wrong memory
- `main_remaining_failure_mode`: gold memory absent from retrieved top-k or wrong packed memory selected
- `accepted_mitigation`: keep packing, then add rerank/verifier for remaining low-confidence top-k rows

Representative cases:
- `heysquad_human_val200_answerable_local_000007`: `packed_wrong_memory`
  - `gold_answer`: incorrectly
  - `gold_memory_id`: heysquad_human_val200_answerable_local_000007
  - `original_prediction`: heysquad_human_val200_answerable_local_000009
  - `packed_prediction`: heysquad_human_val200_answerable_local_000009
  - `packed_prediction_position`: candidate_1
  - `packed_model_output`: A
  - `original_success`: False
  - `packed_success`: False
  - `packed_invalid`: False
  - `packed_text_cost`: 231
- `heysquad_human_val200_answerable_local_000012`: `packed_wrong_memory`
  - `gold_answer`: air
  - `gold_memory_id`: heysquad_human_val200_answerable_local_000012
  - `original_prediction`: heysquad_human_val200_answerable_local_000011
  - `packed_prediction`: heysquad_human_val200_answerable_local_000011
  - `packed_prediction_position`: candidate_1
  - `packed_model_output`: A
  - `original_success`: False
  - `packed_success`: False
  - `packed_invalid`: False
  - `packed_text_cost`: 229
- `heysquad_human_val200_answerable_local_000013`: `packed_wrong_memory`
  - `gold_answer`: Oxygen is the oxidant
  - `gold_memory_id`: heysquad_human_val200_answerable_local_000013
  - `original_prediction`: heysquad_human_val200_answerable_local_000019
  - `packed_prediction`: heysquad_human_val200_answerable_local_000018
  - `packed_prediction_position`: candidate_4
  - `packed_model_output`: D
  - `original_success`: False
  - `packed_success`: False
  - `packed_invalid`: False
  - `packed_text_cost`: 218
- `heysquad_human_val200_answerable_local_000014`: `packed_wrong_memory`
  - `gold_answer`: compounds of oxygen with a high oxidative
  - `gold_memory_id`: heysquad_human_val200_answerable_local_000014
  - `original_prediction`: heysquad_human_val200_answerable_local_000020
  - `packed_prediction`: heysquad_human_val200_answerable_local_000020
  - `packed_prediction_position`: candidate_1
  - `packed_model_output`: A
  - `original_success`: False
  - `packed_success`: False
  - `packed_invalid`: False
  - `packed_text_cost`: 223
- `heysquad_human_val200_answerable_local_000015`: `packed_wrong_memory`
  - `gold_answer`: Oxygen
  - `gold_memory_id`: heysquad_human_val200_answerable_local_000015
  - `original_prediction`: heysquad_human_val200_answerable_local_000018
  - `packed_prediction`: heysquad_human_val200_answerable_local_000018
  - `packed_prediction_position`: candidate_1
  - `packed_model_output`: A
  - `original_success`: False
  - `packed_success`: False
  - `packed_invalid`: False
  - `packed_text_cost`: 206
- `heysquad_human_val200_answerable_local_000018`: `packed_wrong_memory`
  - `gold_answer`: oxidant
  - `gold_memory_id`: heysquad_human_val200_answerable_local_000018
  - `original_prediction`: heysquad_human_val200_answerable_local_000020
  - `packed_prediction`: heysquad_human_val200_answerable_local_000013
  - `packed_prediction_position`: candidate_3
  - `packed_model_output`: C
  - `original_success`: False
  - `packed_success`: False
  - `packed_invalid`: False
  - `packed_text_cost`: 214
- `heysquad_human_val200_answerable_local_000019`: `packed_wrong_memory`
  - `gold_answer`: chemical energy
  - `gold_memory_id`: heysquad_human_val200_answerable_local_000019
  - `original_prediction`: heysquad_human_val200_answerable_local_000020
  - `packed_prediction`: heysquad_human_val200_answerable_local_000018
  - `packed_prediction_position`: candidate_4
  - `packed_model_output`: D
  - `original_success`: False
  - `packed_success`: False
  - `packed_invalid`: False
  - `packed_text_cost`: 192
- `heysquad_human_val200_answerable_local_000020`: `packed_wrong_memory`
  - `gold_answer`: compounds of oxygen
  - `gold_memory_id`: heysquad_human_val200_answerable_local_000020
  - `original_prediction`: heysquad_human_val200_answerable_local_000014
  - `packed_prediction`: heysquad_human_val200_answerable_local_000014
  - `packed_prediction_position`: candidate_1
  - `packed_model_output`: A
  - `original_success`: False
  - `packed_success`: False
  - `packed_invalid`: False
  - `packed_text_cost`: 208

## budgeted_query_audio_gate_selector

- `CoVoST2 ar`: decision=accepted, selected_gate=audio_on_hint_pred_overlap_ge_0_80, selected_utility=0.1769230769230769, selected_delta=0.18846153846153846, selected_ci95=[0.1423076923076923, 0.23846153846153847], selected_success=0.9538461538461539, selected_audio_cost=0.23076923076923078, selected_gate_rate=0.23076923076923078, selected_fixes=49, selected_regressions=0, selected_regression_rate=0.0, selected_clean_success=0.995, selected_stress_success=0.8166666666666667, candidate_count=5, accepted_count=4, candidates=[{'gate': 'audio_on_text_equals_noquery', 'accepted': True, 'reject_reasons': [], 'utility': 0.025192307692307694, 'mixed_success': 0.8, 'delta_vs_text': 0.03461538461538462, 'ci95': [0.015384615384615385, 0.06153846153846154], 'audio_cost': 0.18846153846153846, 'gate_rate': 0.18846153846153846, 'fixes': 9, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 1.0, 'stress_success': 0.13333333333333333}, {'gate': 'audio_on_hint_pred_overlap_ge_0_80', 'accepted': True, 'reject_reasons': [], 'utility': 0.1769230769230769, 'mixed_success': 0.9538461538461539, 'delta_vs_text': 0.18846153846153846, 'ci95': [0.1423076923076923, 0.23846153846153847], 'audio_cost': 0.23076923076923078, 'gate_rate': 0.23076923076923078, 'fixes': 49, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.995, 'stress_success': 0.8166666666666667}, {'gate': 'audio_on_hint_pred_overlap_ge_0_95', 'accepted': True, 'reject_reasons': [], 'utility': 0.1769230769230769, 'mixed_success': 0.9538461538461539, 'delta_vs_text': 0.18846153846153846, 'ci95': [0.1423076923076923, 0.23846153846153847], 'audio_cost': 0.23076923076923078, 'gate_rate': 0.23076923076923078, 'fixes': 49, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.995, 'stress_success': 0.8166666666666667}, {'gate': 'audio_on_text_first_candidate', 'accepted': True, 'reject_reasons': [], 'utility': 0.12192307692307693, 'mixed_success': 0.9038461538461539, 'delta_vs_text': 0.13846153846153847, 'ci95': [0.09615384615384616, 0.18076923076923077], 'audio_cost': 0.33076923076923076, 'gate_rate': 0.33076923076923076, 'fixes': 36, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.995, 'stress_success': 0.6}, {'gate': 'audio_on_invalid', 'accepted': False, 'reject_reasons': ['non_positive_delta', 'ci_lower_not_positive'], 'utility': 0.0, 'mixed_success': 0.7653846153846153, 'delta_vs_text': 0.0, 'ci95': [0.0, 0.0], 'audio_cost': 0.0, 'gate_rate': 0.0, 'fixes': 0, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.995, 'stress_success': 0.0}]
- `HeySQuAD`: decision=accepted, selected_gate=audio_on_text_equals_noquery, selected_utility=0.02730769230769231, selected_delta=0.046153846153846156, selected_ci95=[0.019230769230769232, 0.07307692307692308], selected_success=0.8923076923076924, selected_audio_cost=0.3, selected_gate_rate=0.3, selected_fixes=13, selected_regressions=1, selected_regression_rate=0.0038461538461538464, selected_clean_success=0.905, selected_stress_success=0.85, candidate_count=5, accepted_count=2, candidates=[{'gate': 'audio_on_text_equals_noquery', 'accepted': True, 'reject_reasons': [], 'utility': 0.02730769230769231, 'mixed_success': 0.8923076923076924, 'delta_vs_text': 0.046153846153846156, 'ci95': [0.019230769230769232, 0.07307692307692308], 'audio_cost': 0.3, 'gate_rate': 0.3, 'fixes': 13, 'regressions': 1, 'regression_rate': 0.0038461538461538464, 'clean_success': 0.905, 'stress_success': 0.85}, {'gate': 'audio_on_hint_pred_overlap_ge_0_80', 'accepted': False, 'reject_reasons': ['non_positive_delta', 'ci_lower_not_positive'], 'utility': -0.0042307692307692315, 'mixed_success': 0.8461538461538461, 'delta_vs_text': 0.0, 'ci95': [0.0, 0.0], 'audio_cost': 0.08461538461538462, 'gate_rate': 0.08461538461538462, 'fixes': 0, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.865, 'stress_success': 0.7833333333333333}, {'gate': 'audio_on_hint_pred_overlap_ge_0_95', 'accepted': False, 'reject_reasons': ['non_positive_delta', 'ci_lower_not_positive'], 'utility': -0.00019230769230769233, 'mixed_success': 0.8461538461538461, 'delta_vs_text': 0.0, 'ci95': [0.0, 0.0], 'audio_cost': 0.0038461538461538464, 'gate_rate': 0.0038461538461538464, 'fixes': 0, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.865, 'stress_success': 0.7833333333333333}, {'gate': 'audio_on_text_first_candidate', 'accepted': True, 'reject_reasons': [], 'utility': 0.020576923076923076, 'mixed_success': 0.8807692307692307, 'delta_vs_text': 0.03461538461538462, 'ci95': [0.015384615384615385, 0.057692307692307696], 'audio_cost': 0.28076923076923077, 'gate_rate': 0.28076923076923077, 'fixes': 9, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.895, 'stress_success': 0.8333333333333334}, {'gate': 'audio_on_invalid', 'accepted': False, 'reject_reasons': ['non_positive_delta', 'ci_lower_not_positive'], 'utility': -0.00019230769230769233, 'mixed_success': 0.8461538461538461, 'delta_vs_text': 0.0, 'ci95': [0.0, 0.0], 'audio_cost': 0.0038461538461538464, 'gate_rate': 0.0038461538461538464, 'fixes': 0, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.865, 'stress_success': 0.7833333333333333}]
- `MInDS`: decision=accepted, selected_gate=audio_on_text_first_candidate, selected_utility=0.12937500000000002, selected_delta=0.14583333333333334, selected_ci95=[0.10416666666666667, 0.19166666666666668], selected_success=0.8708333333333333, selected_audio_cost=0.32916666666666666, selected_gate_rate=0.32916666666666666, selected_fixes=35, selected_regressions=0, selected_regression_rate=0.0, selected_clean_success=0.9777777777777777, selected_stress_success=0.55, candidate_count=5, accepted_count=2, candidates=[{'gate': 'audio_on_text_equals_noquery', 'accepted': True, 'reject_reasons': [], 'utility': 0.06937499999999999, 'mixed_success': 0.8041666666666667, 'delta_vs_text': 0.07916666666666666, 'ci95': [0.04583333333333333, 0.1125], 'audio_cost': 0.19583333333333333, 'gate_rate': 0.19583333333333333, 'fixes': 19, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.9833333333333333, 'stress_success': 0.26666666666666666}, {'gate': 'audio_on_hint_pred_overlap_ge_0_80', 'accepted': False, 'reject_reasons': ['audio_cost_exceeds_budget'], 'utility': 0.16541666666666666, 'mixed_success': 0.9375, 'delta_vs_text': 0.2125, 'ci95': [0.1625, 0.26666666666666666], 'audio_cost': 0.9416666666666667, 'gate_rate': 0.9416666666666667, 'fixes': 51, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.9666666666666667, 'stress_success': 0.85}, {'gate': 'audio_on_hint_pred_overlap_ge_0_95', 'accepted': False, 'reject_reasons': ['audio_cost_exceeds_budget'], 'utility': 0.16541666666666666, 'mixed_success': 0.9375, 'delta_vs_text': 0.2125, 'ci95': [0.1625, 0.26666666666666666], 'audio_cost': 0.9416666666666667, 'gate_rate': 0.9416666666666667, 'fixes': 51, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.9666666666666667, 'stress_success': 0.85}, {'gate': 'audio_on_text_first_candidate', 'accepted': True, 'reject_reasons': [], 'utility': 0.12937500000000002, 'mixed_success': 0.8708333333333333, 'delta_vs_text': 0.14583333333333334, 'ci95': [0.10416666666666667, 0.19166666666666668], 'audio_cost': 0.32916666666666666, 'gate_rate': 0.32916666666666666, 'fixes': 35, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.9777777777777777, 'stress_success': 0.55}, {'gate': 'audio_on_invalid', 'accepted': False, 'reject_reasons': ['non_positive_delta', 'ci_lower_not_positive'], 'utility': 0.0, 'mixed_success': 0.725, 'delta_vs_text': 0.0, 'ci95': [0.0, 0.0], 'audio_cost': 0.0, 'gate_rate': 0.0, 'fixes': 0, 'regressions': 0, 'regression_rate': 0.0, 'clean_success': 0.9666666666666667, 'stress_success': 0.0}]

Taxonomy:
- `accepted_pattern`: different semantic tasks need different cheap audio triggers
- `remaining_risk`: QA gate can regress when audio branch selects a plausible but wrong memory
- `accepted_mitigation`: budgeted accept gate plus regression audit; keep task-level rather than universal gate

## covost2_ar_low_margin_verifier

- `n`: 1695
- `raw_acc`: 0.6407079646017699
- `policy_acc`: 0.7510324483775811
- `delta`: 0.11032448377581117
- `ci95`: [0.09616519174041298, 0.1256637168141593]
- `route_rate`: 0.49734513274336284
- `fixes`: 193
- `regressions`: 6

Taxonomy:
- `main_fix_mode`: low-margin top-3 contains the exact target and the verifier resolves near-translation ambiguity
- `main_regression_mode`: verifier sometimes prefers a semantically plausible or more idiomatic translation over the dataset target
- `accepted_mitigation`: report regression count; use conservative prompts and keep paired regression gate

Representative cases:
- `covost2_ar_en_test_full_000206`: `translation_style_or_boundary_conflict`
  - `query_text`: .من المحتمل أن تندلع الحرب
  - `target_text`: Probably the war will start.
  - `base_prediction`: Probably the war will start.
  - `selected_candidate`: The war may break out.
  - `selected_choice`: B
  - `reason`: 'من المحتمل أن تندلع الحرب' translates to 'The war may break out' or 'It is likely that the war will break out.' Candidate B captures the meaning of possibility and the verb 'br...
  - `margin`: 0.0060707032680511475
- `covost2_ar_en_test_full_000342`: `translation_style_or_boundary_conflict`
  - `query_text`: .الأرض ، المريخ ، و المشتري كلهم كواكب
  - `target_text`: Earth, Martian, and Jupiter are all planets.
  - `base_prediction`: Earth, Martian, and Jupiter are all planets.
  - `selected_candidate`: Earth ,Mars,and Jupiter are planets.
  - `selected_choice`: B
  - `reason`: B correctly translates 'المريخ' as 'Mars' and matches the source meaning exactly; A uses 'Martian' which is incorrect.
  - `margin`: 0.005708083510398865
- `covost2_ar_en_test_full_000554`: `translation_style_or_boundary_conflict`
  - `query_text`: هل كتبت هذا الكتاب ؟
  - `target_text`: Have you wrote this book?
  - `base_prediction`: Have you wrote this book?
  - `selected_candidate`: Are you the author of this book?
  - `selected_choice`: B
  - `reason`: Candidate B accurately captures the meaning of the source utterance 'Did you write this book?' while A has a grammatical error and C changes the object to 'homework'.
  - `margin`: 0.01416674256324768
- `covost2_ar_en_test_full_001401`: `translation_style_or_boundary_conflict`
  - `query_text`: من يعلم ؟
  - `target_text`: Who can know?
  - `base_prediction`: Who can know?
  - `selected_candidate`: Who knows?
  - `selected_choice`: B
  - `reason`: 'Who knows?' is the idiomatic English equivalent of the Arabic rhetorical question 'من يعلم؟', while 'Who can know?' is less natural and 'Good only knows' is incorrect.
  - `margin`: 0.014821887016296387
- `covost2_ar_en_test_full_001536`: `semantic_neighbor_translation`
  - `query_text`: أخبرني كيف أحل هذه المسألة.
  - `target_text`: Tell me how can I answer this question.
  - `base_prediction`: Tell me how can I answer this question.
  - `selected_candidate`: Teach me how to solve this problem.
  - `selected_choice`: B
  - `reason`: B directly translates 'أخبرني كيف أحل هذه المسألة' as 'Tell me how to solve this problem,' matching meaning and imperative mood; A uses 'answer this question' which is less prec...
  - `margin`: 0.015181571245193481
- `covost2_ar_en_test_full_001586`: `translation_style_or_boundary_conflict`
  - `query_text`: ما الذي فعلته بآلة التصوير تلك ؟
  - `target_text`: What did you do with the camera?
  - `base_prediction`: What did you do with the camera?
  - `selected_candidate`: What did you do with that camera?
  - `selected_choice`: B
  - `reason`: B includes 'that' which directly translates the demonstrative 'تلك' in the source, making it more meaning-equivalent than A.
  - `margin`: 0.0005751550197601318
