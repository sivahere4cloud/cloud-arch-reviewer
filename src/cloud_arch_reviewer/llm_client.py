import logging
import time
from dataclasses import dataclass
from typing import Any

from openai import APIConnectionError
from openai import APIError
from openai import APIStatusError
from openai import APITimeoutError
from openai import AuthenticationError
from openai import BadRequestError
from openai import OpenAI
from openai import RateLimitError
from pydantic import ValidationError

from cloud_arch_reviewer.config import Settings
from cloud_arch_reviewer.pricing import UnknownModelError
from cloud_arch_reviewer.pricing import calculate_cost
from cloud_arch_reviewer.pricing import format_cost
from cloud_arch_reviewer.schemas import ArchitectureReview

logger = logging.getLogger(__name__)


class LLMError(Exception):
    pass


@dataclass(frozen=True)
class Usage:
    model: str
    input_tokens: int
    output_tokens: int
    cached_tokens: int
    cache_write_tokens: int
    reasoning_tokens: int
    cost_usd: float | None
    latency_seconds: float
    request_id: str | None

    def describe(self) -> str:
        if self.cost_usd is None:
            cost_text = "cost unavailable"
        else:
            cost_text = format_cost(self.cost_usd)

        text = (
            f"{self.model} | in {self.input_tokens} | out {self.output_tokens} "
            f"(reasoning {self.reasoning_tokens}) | {cost_text} | "
            f"{self.latency_seconds:.1f}s"
        )
        return text


def _read_number(source: Any, name: str) -> int:
    if source is None:
        return 0

    value = getattr(source, name, 0)
    if value is None:
        return 0

    return value


def build_usage(
    response_usage: Any,
    model: str,
    latency_seconds: float,
    request_id: str | None = None,
) -> Usage:
    input_tokens = _read_number(response_usage, "input_tokens")
    output_tokens = _read_number(response_usage, "output_tokens")

    input_details = getattr(response_usage, "input_tokens_details", None)
    cached_tokens = _read_number(input_details, "cached_tokens")
    cache_write_tokens = _read_number(input_details, "cache_write_tokens")

    output_details = getattr(response_usage, "output_tokens_details", None)
    reasoning_tokens = _read_number(output_details, "reasoning_tokens")

    try:
        cost = calculate_cost(
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cached_tokens=cached_tokens,
            cache_write_tokens=cache_write_tokens,
        )
    except UnknownModelError as error:
        logger.warning("%s", error)
        cost = None

    usage = Usage(
        model=model,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        cached_tokens=cached_tokens,
        cache_write_tokens=cache_write_tokens,
        reasoning_tokens=reasoning_tokens,
        cost_usd=cost,
        latency_seconds=latency_seconds,
        request_id=request_id,
    )
    return usage


def translate_error(error: APIError) -> LLMError:
    request_id = getattr(error, "request_id", None)
    logger.warning(
        "OpenAI call failed: %s (request id %s)", type(error).__name__, request_id
    )

    if isinstance(error, APITimeoutError):
        return LLMError("The request to OpenAI timed out. Please try again.")

    if isinstance(error, APIConnectionError):
        return LLMError(
            "Could not reach OpenAI. Check your internet connection and try again."
        )

    if isinstance(error, AuthenticationError):
        return LLMError(
            "OpenAI rejected the API key. Check OPENAI_API_KEY in your .env file."
        )

    if isinstance(error, RateLimitError):
        return LLMError("OpenAI rate limit reached. Wait a moment and try again.")

    if isinstance(error, BadRequestError):
        return LLMError(
            "OpenAI could not process this request. Try a different image or settings."
        )

    if isinstance(error, APIStatusError):
        return LLMError(
            f"OpenAI returned an error (status {error.status_code}). Please try again later."
        )

    return LLMError("The OpenAI request failed. Please try again.")


class LLMClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._client = OpenAI(
            api_key=settings.openai_api_key.get_secret_value(),
            timeout=settings.request_timeout_seconds,
            max_retries=settings.max_retries,
        )

    def review_structured(
        self,
        instructions: str,
        image_data_url: str,
        user_text: str,
    ) -> tuple[ArchitectureReview, Usage]:
        content = [
            {"type": "input_text", "text": user_text},
            {"type": "input_image", "image_url": image_data_url},
        ]
        input_items = [{"role": "user", "content": content}]
        model = self._settings.openai_model

        started = time.perf_counter()
        try:
            response = self._client.responses.parse(
                model=model,
                instructions=instructions,
                input=input_items,
                text_format=ArchitectureReview,
                reasoning={"effort": self._settings.openai_reasoning_effort},
                max_output_tokens=self._settings.max_output_tokens,
            )
        except APIError as error:
            raise translate_error(error) from error
        except ValidationError as error:
            logger.warning("Model output failed schema validation: %s", error)
            raise LLMError(
                "The model returned a review in an unexpected format. Please try again."
            ) from error
        latency = time.perf_counter() - started

        request_id = getattr(response, "_request_id", None)
        usage = build_usage(response.usage, model, latency, request_id)
        logger.info("Structured review finished: %s", usage.describe())

        if response.status == "incomplete":
            raise LLMError(
                "The review was cut off before it finished. "
                "Try again, or lower OPENAI_REASONING_EFFORT."
            )

        review = response.output_parsed
        if review is None:
            raise LLMError("The model did not return a review. Try a clearer diagram.")

        return review, usage