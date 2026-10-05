import logging
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Protocol

from cloud_arch_reviewer.config import Settings
from cloud_arch_reviewer.image_utils import InvalidImageError
from cloud_arch_reviewer.image_utils import image_to_data_url
from cloud_arch_reviewer.llm_client import LLMClient
from cloud_arch_reviewer.llm_client import LLMError
from cloud_arch_reviewer.llm_client import Usage
from cloud_arch_reviewer.prompts import load_prompt
from cloud_arch_reviewer.schemas import ArchitectureReview

logger = logging.getLogger(__name__)

PROMPT_FILES = ["system_prompt.md", "pillars.md", "few_shot_examples.md"]
BASE_USER_TEXT = (
    "Review this architecture diagram against the six Well-Architected pillars."
)
MAX_DESCRIPTION_CHARS = 2000

STAGE_READING = "Reading the diagram..."
STAGE_WRITING = "Writing the review..."
STAGE_DONE = "Done"


class ReviewInputError(Exception):
    pass


USER_FACING_ERRORS = (InvalidImageError, LLMError, ReviewInputError)


class ReviewClient(Protocol):
    def review_structured(
        self,
        instructions: str,
        image_data_url: str,
        user_text: str,
    ) -> tuple[ArchitectureReview, Usage]: ...

    def stream_narrative(
        self,
        instructions: str,
        review: ArchitectureReview,
    ) -> Iterator[str | Usage]: ...


@dataclass(frozen=True)
class ReviewState:
    stage: str
    finished: bool
    review: ArchitectureReview | None
    narrative: str
    usages: tuple[Usage, ...]


def build_instructions() -> str:
    parts = []
    for name in PROMPT_FILES:
        text = load_prompt(name)
        parts.append(text)

    instructions = "\n\n".join(parts)
    return instructions


def build_user_text(description: str | None) -> str:
    text = BASE_USER_TEXT
    cleaned = (description or "").strip()
    if cleaned != "":
        text = text + "\n\nDescription from the author:\n" + cleaned

    return text


class Reviewer:
    def __init__(self, settings: Settings, client: ReviewClient | None = None) -> None:
        self._settings = settings
        if client is None:
            client = LLMClient(settings)
        self._client = client
        self._instructions = build_instructions()
        self._narrative_instructions = load_prompt("narrative_prompt.md")

    def review_diagram(
        self,
        image_path: str | None,
        description: str | None,
    ) -> Iterator[ReviewState]:
        if len(description or "") > MAX_DESCRIPTION_CHARS:
            raise ReviewInputError(
                f"The description is too long. The limit is {MAX_DESCRIPTION_CHARS} characters."
            )

        data_url = image_to_data_url(image_path, self._settings.max_image_mb)
        user_text = build_user_text(description)

        yield ReviewState(
            stage=STAGE_READING,
            finished=False,
            review=None,
            narrative="",
            usages=(),
        )

        review, usage = self._client.review_structured(
            self._instructions, data_url, user_text
        )
        usages = [usage]

        yield ReviewState(
            stage=STAGE_WRITING,
            finished=False,
            review=review,
            narrative="",
            usages=tuple(usages),
        )

        narrative = ""
        try:
            for item in self._client.stream_narrative(
                self._narrative_instructions, review
            ):
                if isinstance(item, Usage):
                    usages.append(item)
                    continue

                narrative = narrative + item
                yield ReviewState(
                    stage=STAGE_WRITING,
                    finished=False,
                    review=review,
                    narrative=narrative,
                    usages=tuple(usages),
                )
        except LLMError as error:
            logger.warning("Written review failed after the scorecard: %s", error)
            yield ReviewState(
                stage=f"Scorecard ready, but the written review failed: {error}",
                finished=True,
                review=review,
                narrative=narrative,
                usages=tuple(usages),
            )
            return

        yield ReviewState(
            stage=STAGE_DONE,
            finished=True,
            review=review,
            narrative=narrative,
            usages=tuple(usages),
        )