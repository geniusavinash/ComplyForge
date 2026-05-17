# ComplyForge — EU AI Act Mapping

> **Not legal advice.** Article 11 / Annex IV / Article 27 mapping is for
> demonstration. Production submissions to a Notified Body or national
> supervisory authority require legal review by qualified counsel.

This file is the audit cross-reference between ComplyForge's outputs and
specific provisions of **Regulation (EU) 2024/1689** ("EU AI Act"). All
taxonomy IDs cited below are the literal `id` / `section_id` strings from
`backend/app/data/eu_ai_act_taxonomy.py` so the doc stays in sync with
code.

---

## 1. Risk-tier classification

`ClassifierAgent` returns one of four tiers per
`backend/app/schemas.py::RiskTier`:

| Tier | EU AI Act anchor | Notes |
| --- | --- | --- |
| `prohibited` | **Article 5** | Outright bans; eight categories below. |
| `high_risk` | **Article 6 + Annex III** | Eight Annex III domains below. Triggers Article 9, 10, 11, 14, 15, 27, 72 obligations. |
| `limited_risk` | **Article 50** | Transparency duties (chatbot disclosure, deepfake labelling). |
| `minimal_risk` | (default) | No specific obligations beyond voluntary codes (Article 95). |

The classifier emits `triggered_articles` strings that ComplyForge filters
against a closed set: `Article 5`, `Article 5(1)(a)..(h)`, `Article 6`,
`Article 9`, `Article 11`, `Article 27`, `Article 50`, `Article 50(1)`,
`Article 50(3)`, `Article 50(4)`, `Article 72`, `Article 99`, and
`Annex III(1)..(8)`. Any other string is dropped as a hallucinated
citation. The precautionary rule promotes confidence-below-0.5 outputs
that are not `prohibited` to `high_risk` (verified in
`tests/test_classifier.py::test_precautionary_low_confidence_promotes_to_high_risk`).

---

## 2. Article 5 — Prohibited practices (8 categories)

Source: `eu_ai_act_taxonomy.py::PROHIBITED_PRACTICES`. Each entry's `id`
is the stable handle the classifier and policy agents use.

| `id` | Article | Title |
| --- | --- | --- |
| `subliminal_manipulation` | Article 5(1)(a) | Subliminal or manipulative techniques causing harm |
| `exploitation_of_vulnerabilities` | Article 5(1)(b) | Exploitation of vulnerabilities (age, disability, socio-economic) |
| `social_scoring` | Article 5(1)(c) | Social scoring by public authorities or on their behalf |
| `predictive_policing_profiling` | Article 5(1)(d) | Predictive policing based solely on profiling |
| `untargeted_facial_scraping` | Article 5(1)(e) | Untargeted scraping of facial images |
| `emotion_recognition_workplace_education` | Article 5(1)(f) | Emotion recognition in workplaces and education |
| `biometric_categorisation_sensitive_attributes` | Article 5(1)(g) | Biometric categorisation inferring sensitive attributes |
| `real_time_remote_biometric_id_public_spaces` | Article 5(1)(h) | Real-time remote biometric identification in publicly accessible spaces |

Demonstration agents in `sample_agents.json` map to this list:
`EmotionPulse` exercises `emotion_recognition_workplace_education`. The
`sensitive-attribute-inference` attack payload exercises
`biometric_categorisation_sensitive_attributes`.

---

## 3. Article 6 + Annex III — High-risk domains (8 points)

Source: `eu_ai_act_taxonomy.py::HIGH_RISK_DOMAINS`.

| `id` | Annex III point | Title |
| --- | --- | --- |
| `biometrics` | Annex III(1) | Biometric identification and categorisation of natural persons |
| `critical_infrastructure` | Annex III(2) | Management and operation of critical infrastructure |
| `education_vocational_training` | Annex III(3) | Education and vocational training |
| `employment_workers_management` | Annex III(4) | Employment, workers management, and access to self-employment |
| `essential_private_public_services` | Annex III(5) | Access to and enjoyment of essential private and public services |
| `law_enforcement` | Annex III(6) | Law enforcement |
| `migration_asylum_border` | Annex III(7) | Migration, asylum, and border control management |
| `justice_democratic_processes` | Annex III(8) | Administration of justice and democratic processes |

`ResumeRanker` lands in `employment_workers_management` (Annex III(4));
`CreditDecider` lands in `essential_private_public_services` (Annex
III(5)). `SupportBot` is `limited_risk` under Article 50(1), not
high-risk.

---

## 4. Article 11 + Annex IV — Technical file (9 sections)

Source: `eu_ai_act_taxonomy.py::ARTICLE_11_SECTIONS`. The DocAgent
generates one body block per `section_id`, and the PDF renders one
chapter per `heading`. Annex IV's enumerated points are mapped below.

| `section_id` | Heading | Annex IV / EU AI Act anchor |
| --- | --- | --- |
| `general_description` | 1. General description of the AI system | Annex IV(1)(a) |
| `elements_and_development_process` | 2. Detailed description of the elements and the development process | Annex IV(1)(b) |
| `monitoring_functioning_control` | 3. Information on monitoring, functioning, and control | Annex IV(1)(c) |
| `risk_management_system` | 4. Risk management system (Article 9) | Article 9 + Annex IV(1)(d) |
| `lifecycle_changes` | 5. Changes made to the system through its lifecycle | Annex IV(1)(e) |
| `performance_metrics_and_misuse` | 6. Performance metrics including foreseeable misuse | Annex IV(1)(f) (informed by Article 15) |
| `standards_applied` | 7. Harmonised standards and common specifications applied | Annex IV(1)(g) |
| `declaration_of_conformity` | 8. EU declaration of conformity | Article 47 + Annex IV(1)(h) |
| `post_market_monitoring_plan` | 9. Post-market monitoring plan (Article 72) | Article 72 + Annex IV(1)(i) |

The PDF footer reads
`"Generated by ComplyForge | Not legal advice | Article 11 + Annex IV mapping"`
on every page. Verified in `backend/app/services/pdf_generator.py`.

---

## 5. Article 27 — FRIA (6 sections)

Source: `eu_ai_act_taxonomy.py::FRIA_SECTIONS`. Generated only when
`classification.tier == high_risk` (the orchestrator otherwise inserts
the canned "FRIA not required" note that cites Article 27 scope).

| `section_id` | Heading | Article 27 anchor |
| --- | --- | --- |
| `deployer_processes` | 1. Description of the deployer's processes | Article 27(1)(a) |
| `period_and_frequency` | 2. Period and frequency of intended use | Article 27(1)(b) |
| `affected_persons_and_groups` | 3. Categories of natural persons and groups likely to be affected | Article 27(1)(c) |
| `specific_risks_of_harm` | 4. Specific risks of harm to fundamental rights | Article 27(1)(d) |
| `human_oversight_measures` | 5. Human oversight measures | Article 27(1)(e) (links Article 14) |
| `measures_when_risks_materialise` | 6. Measures to be taken if risks materialise | Article 27(1)(f) |

---

## 6. Article 50 — Limited-risk transparency triggers

Source: `eu_ai_act_taxonomy.py::LIMITED_RISK_TRIGGERS`.

| `id` | Article | Title |
| --- | --- | --- |
| `chatbot_disclosure` | Article 50(1) | Chatbots must disclose AI interaction |
| `emotion_recognition_or_biometric_categorisation_disclosure` | Article 50(3) | Emotion recognition / biometric categorisation must inform users |
| `deepfake_labelling` | Article 50(4) [deepfakes] | Deepfakes must be labelled |
| `ai_generated_text_public_interest` | Article 50(4) [text] | AI-generated text on matters of public interest must be labelled |

`SupportBot` (limited-risk fixture) trips `chatbot_disclosure`. The
PolicyAgent's limited-risk skeleton emits a `MODIFY` rule that injects an
AI-disclosure preamble citing Article 50.

---

## 7. PolicyAgent — Lobster Trap rule mapping

Source: `backend/app/agents/policy_generator.py`. The `description`
field of every rule cites the Article it enforces. Per-tier counts are
guarded by `tests/test_policy_generator.py`.

### PROHIBITED (1 rule)

| Rule `name` | Action | Cited articles |
| --- | --- | --- |
| `prohibited_practice_block` | DENY | The specific `Article 5(1)(x)` from `triggered_articles`, falling back to `Article 5`. |

### HIGH_RISK (5 rules)

| Rule `name` | Action | Cited articles |
| --- | --- | --- |
| `prompt_injection_block` (ingress) | DENY | Article 15 (cybersecurity) |
| `decision_without_oversight_human_review` (ingress) | HUMAN_REVIEW | Article 14 (human oversight) |
| `rate_limit_unusual_surges` (ingress) | RATE_LIMIT | Article 15 (robustness) + Annex III tier rationale |
| `pii_egress_human_review` (egress) | HUMAN_REVIEW | Article 10 (data governance) |
| `comprehensive_logging` (egress) | LOG | Article 12 (record-keeping) + Article 72 (post-market monitoring) |

### LIMITED_RISK (2 rules)

| Rule `name` | Action | Cited articles |
| --- | --- | --- |
| `disclose_ai_interaction` (egress) | MODIFY | Article 50 (transparency) |
| `deepfake_generation_log` (egress) | LOG | Article 50(4) (deepfake labelling) |

### MINIMAL_RISK (1 rule)

| Rule `name` | Action | Cited articles |
| --- | --- | --- |
| `log_everything` (ingress) | LOG | Article 95 (voluntary codes) |

The full action vocabulary is locked at the documented Lobster Trap set:
`ALLOW`, `DENY`, `LOG`, `HUMAN_REVIEW`, `QUARANTINE`, `RATE_LIMIT`,
`MODIFY`, `REDIRECT`. ComplyForge raises if a rule slips through with any
other value (verified in
`tests/test_policy_generator.py::test_rule_actions_remain_in_documented_vocabulary`).

---

## 8. Article 99 — Penalties

Source: `eu_ai_act_taxonomy.py::PENALTY_TIERS`. ComplyForge surfaces these
numbers verbatim in the pitch deck.

| Violation class (taxonomy key) | Maximum fine (EUR) | Maximum % global turnover |
| --- | --- | --- |
| `prohibited_practice` | 35 000 000 | 7 % |
| `high_risk_violation` | 15 000 000 | 3 % |
| `misleading_information_to_authorities` | 7 500 000 | 1 % |

The "whichever is higher" rule applies under Article 99(3)–(5) for
undertakings.

---

## 9. Phased application timeline (regulation-level, not ComplyForge-level)

| Date | Event |
| --- | --- |
| 2024-08-01 | Regulation enters force |
| 2025-02-02 | Article 5 prohibitions binding · Article 4 AI literacy duty starts |
| 2025-08-02 | GPAI obligations (Chapter V) · governance bodies · Article 99 penalty framework |
| **2026-08-02** | **High-risk system rules become binding** — ComplyForge's countdown |
| 2027-08-02 | Annex I high-risk products (e.g. medical devices) phase in |

---

## 10. Caveat (re-stated)

ComplyForge produces **structurally complete first drafts** of Article 11
technical files and Article 27 FRIAs by mapping each section to its
Annex IV / Article 27 anchor. The drafts cite real Article numbers
because the prompts forbid hallucinated citations and the post-processor
filters anything outside the closed set. **Real submissions still need
human legal review.** The PDF footer says so on every page.
