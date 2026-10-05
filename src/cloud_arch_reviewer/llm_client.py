import logging
from dataclasses import dataclass
from typing import Any

from cloud_arch_reviewer.pricing import UnknownModelError
from cloud_arch_reviewer.pricing import calculate_cost
from cloud_arch_reviewer.pricing import format_cost

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