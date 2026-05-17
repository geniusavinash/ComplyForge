"""EU AI Act taxonomy — pure-Python data module.

Used by ClassifierAgent, DocAgent, and PolicyAgent to ground all reasoning in
Regulation (EU) 2024/1689. Articles referenced: 5 (prohibited), 6 + Annex III
(high-risk), 9 (risk mgmt), 11 + Annex IV (technical file), 27 (FRIA),
50 (transparency), 72 (post-market), 99 (penalties).
"""

from __future__ import annotations

from typing import Any


# Article 5 — Prohibited practices (8 categories)
PROHIBITED_PRACTICES: list[dict[str, Any]] = [
    {"id": "subliminal_manipulation", "article": "Article 5(1)(a)",
     "title": "Subliminal or manipulative techniques causing harm",
     "description": "AI systems deploying subliminal techniques beyond a person's consciousness, or purposefully manipulative or deceptive techniques, with the objective or effect of materially distorting behaviour and causing significant harm.",
     "examples": ["Hidden audio cues in ads designed to coerce purchases",
                  "Dark-pattern chatbots manipulating vulnerable users into financial decisions"]},
    {"id": "exploitation_of_vulnerabilities", "article": "Article 5(1)(b)",
     "title": "Exploitation of vulnerabilities (age, disability, socio-economic)",
     "description": "AI systems that exploit vulnerabilities of a natural person or specific group due to their age, disability, or social/economic situation, in a way likely to cause significant harm.",
     "examples": ["Predatory lending agent targeting low-income users",
                  "AI-voiced toy pressuring children into in-app purchases"]},
    {"id": "social_scoring", "article": "Article 5(1)(c)",
     "title": "Social scoring by public authorities or on their behalf",
     "description": "AI evaluating or classifying natural persons over time based on social behaviour or personal characteristics, leading to detrimental treatment in unrelated contexts or treatment that is unjustified or disproportionate.",
     "examples": ["Government citizen reputation score affecting housing access",
                  "Public-benefits eligibility based on social-media behaviour"]},
    {"id": "predictive_policing_profiling", "article": "Article 5(1)(d)",
     "title": "Predictive policing based solely on profiling",
     "description": "AI making risk assessments of natural persons to predict criminal offending, based solely on profiling or assessing personality traits and characteristics.",
     "examples": ["Tool flagging individuals as future offenders from demographic profiles",
                  "Risk scoring for arrest decisions based on personality traits alone"]},
    {"id": "untargeted_facial_scraping", "article": "Article 5(1)(e)",
     "title": "Untargeted scraping of facial images",
     "description": "AI creating or expanding facial-recognition databases through the untargeted scraping of facial images from the internet or CCTV footage.",
     "examples": ["Crawler ingesting social-media photos to build a face database",
                  "CCTV face-harvesting service sold to third parties"]},
    {"id": "emotion_recognition_workplace_education", "article": "Article 5(1)(f)",
     "title": "Emotion recognition in workplaces and education",
     "description": "AI inferring emotions of natural persons in workplace and education settings, except where intended for medical or safety reasons.",
     "examples": ["Webcam-based emotion analytics for call-centre agents",
                  "Classroom camera scoring student engagement by inferred mood"]},
    {"id": "biometric_categorisation_sensitive_attributes", "article": "Article 5(1)(g)",
     "title": "Biometric categorisation inferring sensitive attributes",
     "description": "Biometric categorisation deducing race, political opinions, trade-union membership, religious or philosophical beliefs, sex life, or sexual orientation from biometric data.",
     "examples": ["Face-based ethnicity classifier for ad targeting",
                  "Voice analysis inferring political affiliation"]},
    {"id": "real_time_remote_biometric_id_public_spaces", "article": "Article 5(1)(h)",
     "title": "Real-time remote biometric identification in publicly accessible spaces",
     "description": "Use of real-time remote biometric ID in publicly accessible spaces for law enforcement, except in narrowly defined exceptions (missing persons, imminent terrorist threat, identification of suspects of specific serious crimes).",
     "examples": ["Live face-recognition cameras in public squares for general policing",
                  "Real-time biometric ID at protests without judicial authorisation"]},
]

# Article 6 + Annex III — High-risk domains (8 points)
HIGH_RISK_DOMAINS: list[dict[str, Any]] = [
    {"id": "biometrics", "annex_iii_point": "Annex III(1)",
     "title": "Biometric identification and categorisation of natural persons",
     "description": "Remote biometric identification (excluding identity verification), biometric categorisation by sensitive/protected attributes, and emotion-recognition systems not prohibited under Article 5.",
     "examples": ["Airport identity verification kiosk",
                  "Border control face matching against watchlists"]},
    {"id": "critical_infrastructure", "annex_iii_point": "Annex III(2)",
     "title": "Management and operation of critical infrastructure",
     "description": "AI used as safety components in critical digital infrastructure, road traffic, and supply of water, gas, heating, and electricity.",
     "examples": ["AI controller for an electricity grid load balancer",
                  "Traffic-light optimisation safety component on a motorway"]},
    {"id": "education_vocational_training", "annex_iii_point": "Annex III(3)",
     "title": "Education and vocational training",
     "description": "AI used to determine access/admission, evaluate learning outcomes, assess education level, or detect prohibited behaviour during exams.",
     "examples": ["University admissions ranking system",
                  "Online-exam proctoring with cheating-detection AI"]},
    {"id": "employment_workers_management", "annex_iii_point": "Annex III(4)",
     "title": "Employment, workers management, and access to self-employment",
     "description": "AI for recruitment/selection (filtering applications, evaluating candidates), terms of work, promotion, termination, task allocation by traits, and monitoring/evaluating performance and behaviour.",
     "examples": ["Resume-screening / candidate-ranking agent",
                  "Gig-platform task allocation and performance scoring"]},
    {"id": "essential_private_public_services", "annex_iii_point": "Annex III(5)",
     "title": "Access to and enjoyment of essential private and public services",
     "description": "AI evaluating eligibility for essential public benefits, creditworthiness/credit scoring of natural persons (except financial-fraud detection), risk and pricing for life/health insurance, and emergency-response triage and dispatch.",
     "examples": ["Consumer credit scoring agent",
                  "Emergency call triage and ambulance dispatch prioritisation"]},
    {"id": "law_enforcement", "annex_iii_point": "Annex III(6)",
     "title": "Law enforcement",
     "description": "AI used by/for law-enforcement authorities for individual risk assessment, polygraphs, evaluating evidence reliability, profiling during detection/investigation/prosecution, and crime analytics on natural persons.",
     "examples": ["Recidivism risk assessment for sentencing recommendations",
                  "Investigative profiling tool used by a police unit"]},
    {"id": "migration_asylum_border", "annex_iii_point": "Annex III(7)",
     "title": "Migration, asylum, and border control management",
     "description": "AI as polygraphs/similar tools, assessing risks of incoming persons, assisting examination of asylum/visa/residence applications, or detection/identification of natural persons in the migration context.",
     "examples": ["Asylum-claim credibility assessment assistant",
                  "Border-risk scoring of incoming travellers"]},
    {"id": "justice_democratic_processes", "annex_iii_point": "Annex III(8)",
     "title": "Administration of justice and democratic processes",
     "description": "AI assisting judicial authorities in researching/interpreting facts and law, or used in alternative dispute resolution; AI intended to influence elections, referenda, or voting behaviour of natural persons.",
     "examples": ["Judicial decision-support tool drafting reasoning for a judge",
                  "Targeted political-ad optimiser influencing voter behaviour"]},
]

# Article 50 — Limited-risk transparency triggers
LIMITED_RISK_TRIGGERS: list[dict[str, Any]] = [
    {"id": "chatbot_disclosure", "article": "Article 50(1)",
     "title": "Chatbots must disclose AI interaction",
     "description": "Providers of AI systems intended to interact directly with natural persons must ensure those persons are informed they are interacting with an AI, unless this is obvious from context."},
    {"id": "emotion_recognition_or_biometric_categorisation_disclosure", "article": "Article 50(3)",
     "title": "Emotion recognition / biometric categorisation must inform users",
     "description": "Deployers of permitted emotion-recognition or biometric-categorisation systems must inform exposed natural persons and process personal data in accordance with EU data-protection law."},
    {"id": "deepfake_labelling", "article": "Article 50(4) [deepfakes]",
     "title": "Deepfakes must be labelled",
     "description": "Deployers of AI systems generating or manipulating image/audio/video content constituting a deepfake must disclose that the content has been artificially generated or manipulated."},
    {"id": "ai_generated_text_public_interest", "article": "Article 50(4) [text]",
     "title": "AI-generated text on matters of public interest must be labelled",
     "description": "Deployers of AI generating or manipulating text published to inform the public on matters of public interest must disclose its artificial origin, unless human review and editorial responsibility apply."},
]

# Annex IV / Article 11 — Technical documentation sections (9 sections)
ARTICLE_11_SECTIONS: list[dict[str, Any]] = [
    {"section_id": "general_description", "heading": "1. General description of the AI system",
     "prompt_hint": "Summarise the agent's intended purpose, provider, version, hardware/software interactions, and the categories of natural persons or groups intended to use or be affected by it."},
    {"section_id": "elements_and_development_process", "heading": "2. Detailed description of the elements and the development process",
     "prompt_hint": "Describe system architecture, methods, design choices, training methodologies, datasets used, validation/testing procedures, and built-in human oversight measures."},
    {"section_id": "monitoring_functioning_control", "heading": "3. Information on monitoring, functioning, and control",
     "prompt_hint": "Describe how the system is monitored in operation, metrics collected, controls available to the deployer, and known operational limits or conditions of use."},
    {"section_id": "risk_management_system", "heading": "4. Risk management system (Article 9)",
     "prompt_hint": "Document risk identification, analysis, estimation, evaluation of foreseeable risks, and the risk-mitigation measures across the lifecycle."},
    {"section_id": "lifecycle_changes", "heading": "5. Changes made to the system through its lifecycle",
     "prompt_hint": "Describe substantial modifications, version history, and the criteria used to determine whether a change requires re-classification or new conformity assessment."},
    {"section_id": "performance_metrics_and_misuse", "heading": "6. Performance metrics including foreseeable misuse",
     "prompt_hint": "List accuracy, robustness, and cybersecurity metrics, performance on subgroups, foreseeable misuse cases, and any known discriminatory outcomes or biases."},
    {"section_id": "standards_applied", "heading": "7. Harmonised standards and common specifications applied",
     "prompt_hint": "List harmonised standards (ISO/IEC 42001, ISO/IEC 23894, ISO/IEC 25059, IEEE 7000-series) or common specifications applied, or alternative technical solutions used."},
    {"section_id": "declaration_of_conformity", "heading": "8. EU declaration of conformity",
     "prompt_hint": "Reference the EU declaration of conformity drawn up under Article 47, including provider identifiers and a statement that the system meets the relevant requirements."},
    {"section_id": "post_market_monitoring_plan", "heading": "9. Post-market monitoring plan (Article 72)",
     "prompt_hint": "Describe the post-market monitoring system: data sources, metrics tracked, incident-reporting procedure (Article 73), and corrective actions for serious incidents."},
]

# Article 27 — FRIA sections (6 sections)
FRIA_SECTIONS: list[dict[str, Any]] = [
    {"section_id": "deployer_processes", "heading": "1. Description of the deployer's processes",
     "prompt_hint": "Describe the deployer's processes in which the high-risk AI system will be used, in line with its intended purpose."},
    {"section_id": "period_and_frequency", "heading": "2. Period and frequency of intended use",
     "prompt_hint": "State the period of time within which, and the frequency with which, each high-risk AI system is intended to be used."},
    {"section_id": "affected_persons_and_groups", "heading": "3. Categories of natural persons and groups likely to be affected",
     "prompt_hint": "Identify categories of natural persons and groups likely to be affected, with attention to vulnerable groups."},
    {"section_id": "specific_risks_of_harm", "heading": "4. Specific risks of harm to fundamental rights",
     "prompt_hint": "Describe specific risks of harm likely to impact the identified categories, taking into account information from the provider's instructions for use."},
    {"section_id": "human_oversight_measures", "heading": "5. Human oversight measures",
     "prompt_hint": "Describe implementation of human oversight measures, including organisational and technical controls."},
    {"section_id": "measures_when_risks_materialise", "heading": "6. Measures to be taken if risks materialise",
     "prompt_hint": "Describe internal governance arrangements and complaint mechanisms to be invoked when identified risks materialise."},
]

# Article 99 — Penalty tiers
PENALTY_TIERS: dict[str, dict[str, float]] = {
    "prohibited_practice": {"max_eur": 35_000_000.0, "max_pct_turnover": 7.0},
    "high_risk_violation": {"max_eur": 15_000_000.0, "max_pct_turnover": 3.0},
    "misleading_information_to_authorities": {"max_eur": 7_500_000.0, "max_pct_turnover": 1.0},
}

__all__ = [
    "PROHIBITED_PRACTICES", "HIGH_RISK_DOMAINS", "LIMITED_RISK_TRIGGERS",
    "ARTICLE_11_SECTIONS", "FRIA_SECTIONS", "PENALTY_TIERS",
]
