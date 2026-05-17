from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


class RiskTier(str, Enum):
    PROHIBITED = "prohibited"
    HIGH_RISK = "high_risk"
    LIMITED_RISK = "limited_risk"
    MINIMAL_RISK = "minimal_risk"


class AgentDescriptor(BaseModel):
    """User-supplied description of an enterprise AI agent."""
    name: str
    purpose: str
    domain: str = Field(description="e.g. HR, finance, healthcare, customer-service")
    inputs: list[str] = Field(default_factory=list, description="Types of data the agent receives")
    outputs: list[str] = Field(default_factory=list, description="Decisions or content the agent produces")
    affects_humans: bool = Field(default=True, description="Does the output affect a person's rights, access, or opportunity?")
    sample_prompts: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list, description="External tools / APIs the agent can call")


class ClassificationResult(BaseModel):
    tier: RiskTier
    confidence: float = Field(ge=0.0, le=1.0)
    triggered_articles: list[str] = Field(description="EU AI Act articles or annexes implicated")
    rationale: str
    obligations: list[str] = Field(description="What the operator must do for this tier")


class Article11Section(BaseModel):
    heading: str
    body: str


class TechnicalFile(BaseModel):
    agent_name: str
    risk_tier: RiskTier
    generated_at: datetime
    sections: list[Article11Section]
    fria_summary: str
    datasheet: dict[str, Any]


class LobsterTrapPolicy(BaseModel):
    name: str
    yaml: str
    purpose: str
    rules_count: int


class ComplianceReport(BaseModel):
    agent: AgentDescriptor
    classification: ClassificationResult
    technical_file: TechnicalFile
    policy: LobsterTrapPolicy
    pdf_path: str | None = None


class EnforcementEvent(BaseModel):
    timestamp: datetime
    agent_name: str
    rule_triggered: str
    action: str = Field(description="ALLOW | DENY | LOG | QUARANTINE | RATE_LIMIT")
    request_snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)
