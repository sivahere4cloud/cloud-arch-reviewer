from dataclasses import dataclass

# Source: https://developers.openai.com/api/docs/pricing
# Standard processing, short context, US dollars per 1M tokens.
PRICES_CHECKED_ON = "2026-10-05"

TOKENS_PER_MILLION = 1_000_000


@dataclass(frozen=True)
class ModelPrice:
    input_per_million: float
    cached_input_per_million: float
    output_per_million: float


PRICES = {
    "gpt-6-luna": ModelPrice(
        input_per_million=0.10,
        cached_input_per_million=0.01,
        output_per_million=0.50,
    ),
    "gpt-6.1-sol": ModelPrice(
        input_per_million=2.00,
        cached_input_per_million=0.10,
        output_per_million=10.00,
    ),
}


class UnknownModelError(Exception):
    pass


def calculate_cost(
    model: str,
    input_tokens: int,
    output_tokens: int,
    cached_tokens: int = 0,
) -> float:
    price = PRICES.get(model)
    if price is None:
        known = ", ".join(PRICES)
        raise UnknownModelError(f"No price for model '{model}'. Known models: {known}.")

    uncached_tokens = input_tokens - cached_tokens
    if uncached_tokens < 0:
        raise ValueError("cached_tokens cannot be greater than input_tokens")

    input_cost = uncached_tokens * price.input_per_million / TOKENS_PER_MILLION
    cached_cost = cached_tokens * price.cached_input_per_million / TOKENS_PER_MILLION
    output_cost = output_tokens * price.output_per_million / TOKENS_PER_MILLION

    total = input_cost + cached_cost + output_cost
    return total


def format_cost(cost: float) -> str:
    return f"${cost:.4f}"