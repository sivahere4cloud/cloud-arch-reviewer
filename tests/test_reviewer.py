from pathlib import Path

import pytest

from cloud_arch_reviewer.config import Settings
from cloud_arch_reviewer.image_utils import InvalidImageError
from cloud_arch_reviewer.llm_client import LLMError
from cloud_arch_reviewer.llm_client import Usage
from cloud_arch_reviewer.reviewer import MAX_DESCRIPTION_CHARS
from cloud_arch_reviewer.reviewer import STAGE_DONE
from cloud_arch_reviewer.reviewer import STAGE_READING
from cloud_arch_reviewer.reviewer import ReviewInputError
from cloud_arch_reviewer.reviewer import Reviewer
from cloud_arch_reviewer.schemas import ArchitectureReview
from cloud_arch_reviewer.schemas import PillarScore
from cloud_arch_reviewer.schemas import Risk

PILLARS = [
    "Operational Excellence",
    "Security",
    "Reliability",
    "Performance Efficiency",
    "Cost Optimization",
    "Sustainability",
]


def make_settings() -> Settings:
    return Settings(_env_file=None, openai_api_key="sk-test")


def make_image(tmp_path: Path) -> Path:
    path = tmp_path / "diagram.png"
    path.write_bytes(b"\x89PNG\r\n\x1a\n" + b"0" * 20)
    return path


def make_review() -> ArchitectureReview:
    scores = []
    for pillar in PILLARS:
        score = PillarScore(pillar=pillar, score=3, rationale="ok")
        scores.append(score)

    risk = Risk(
        pillar="Security",
        severity="high",
        title="Test risk",
        description="Test description",
        suggested_fix="Test fix",
    )
    review = ArchitectureReview(
        summary="Test summary",
        detected_services=["ALB"],
        pillar_scores=scores,
        risks=[risk],
        unclear_items=["Test unclear item"],
    )
    return review


def make_usage() -> Usage:
    usage = Usage(
        model="gpt-6-luna",
        input_tokens=100,
        output_tokens=50,
        cached_tokens=0,
        cache_write_tokens=0,
        reasoning_tokens=0,
        cost_usd=0.001,
        latency_seconds=1.0,
        request_id=None,
    )
    return usage


class FakeClient:
    def __init__(
        self,
        chunks: list[str],
        narrative_fails: bool = False,
        structured_error: Exception | None = None,
    ) -> None:
        self.chunks = chunks
        self.narrative_fails = narrative_fails
        self.structured_error = structured_error
        self.structured_calls = 0

    def review_structured(self, instructions, image_data_url, user_text):
        self.structured_calls = self.structured_calls + 1
        if self.structured_error is not None:
            raise self.structured_error

        return make_review(), make_usage()

    def stream_narrative(self, instructions, review):
        for chunk in self.chunks:
            yield chunk

        if self.narrative_fails:
            raise LLMError("fake narrative failure")

        yield make_usage()


def test_review_runs_all_stages(tmp_path):
    client = FakeClient(chunks=["Hello ", "world"])
    reviewer = Reviewer(make_settings(), client)

    states = list(reviewer.review_diagram(str(make_image(tmp_path)), None))

    final = states[-1]
    assert states[0].stage == STAGE_READING
    assert final.finished is True
    assert final.stage == STAGE_DONE
    assert final.narrative == "Hello world"
    assert len(final.usages) == 2
    assert final.review is not None


def test_failed_narrative_keeps_the_scorecard(tmp_path):
    client = FakeClient(chunks=["Partial "], narrative_fails=True)
    reviewer = Reviewer(make_settings(), client)

    states = list(reviewer.review_diagram(str(make_image(tmp_path)), None))

    final = states[-1]
    assert final.finished is True
    assert final.review is not None
    assert final.narrative == "Partial "
    assert len(final.usages) == 1
    assert final.stage.startswith("Scorecard ready")


def test_structured_failure_is_raised(tmp_path):
    client = FakeClient(chunks=[], structured_error=LLMError("fake failure"))
    reviewer = Reviewer(make_settings(), client)

    with pytest.raises(LLMError):
        list(reviewer.review_diagram(str(make_image(tmp_path)), None))


def test_long_description_is_blocked_before_any_call(tmp_path):
    client = FakeClient(chunks=[])
    reviewer = Reviewer(make_settings(), client)
    too_long = "x" * (MAX_DESCRIPTION_CHARS + 1)

    with pytest.raises(ReviewInputError):
        list(reviewer.review_diagram(str(make_image(tmp_path)), too_long))

    assert client.structured_calls == 0


def test_missing_image_is_blocked_before_any_call(tmp_path):
    client = FakeClient(chunks=[])
    reviewer = Reviewer(make_settings(), client)

    with pytest.raises(InvalidImageError):
        list(reviewer.review_diagram(str(tmp_path / "missing.png"), None))

    assert client.structured_calls == 0