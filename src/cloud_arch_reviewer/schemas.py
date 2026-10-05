from typing import Literal

from pydantic import BaseModel
from pydantic import Field
from pydantic import field_validator

PillarName = Literal[
    "Operational Excellence",
    "Security",
    "Reliability",
    "Performance Efficiency",
    "Cost Optimization",
    "Sustainability",
]

Severity = Literal["low", "medium", "high", "critical"]


class PillarScore(BaseModel):
    pillar: PillarName
    score: int = Field(description="Score from 1 (poor) to 5 (excellent)")
    rationale: str = Field(description="One or two sentences explaining the score")

    @field_validator("score")
    @classmethod
    def check_score_range(cls, value: int) -> int:
        if value < 1 or value > 5:
            raise ValueError("score must be between 1 and 5")
        return value


class Risk(BaseModel):
    pillar: PillarName
    severity: Severity
    title: str = Field(description="Short name for the risk")
    description: str = Field(description="What is wrong and why it matters")
    suggested_fix: str = Field(description="A concrete change that reduces the risk")


class ArchitectureReview(BaseModel):
    summary: str = Field(description="Two or three sentence overview of the architecture")
    detected_services: list[str] = Field(
        description="AWS services and components visible in the diagram"
    )
    pillar_scores: list[PillarScore]
    risks: list[Risk]
    unclear_items: list[str] = Field(
        description="Parts of the diagram that were hard to read or ambiguous"
    )

    def average_score(self) -> float:
        if len(self.pillar_scores) == 0:
            return 0.0

        total = 0
        for item in self.pillar_scores:
            total = total + item.score

        average = total / len(self.pillar_scores)
        return round(average, 1)