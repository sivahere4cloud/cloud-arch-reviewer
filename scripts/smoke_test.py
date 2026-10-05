import sys

from cloud_arch_reviewer.config import get_settings
from cloud_arch_reviewer.image_utils import InvalidImageError
from cloud_arch_reviewer.image_utils import image_to_data_url
from cloud_arch_reviewer.llm_client import LLMClient
from cloud_arch_reviewer.llm_client import LLMError
from cloud_arch_reviewer.llm_client import Usage
from cloud_arch_reviewer.logging_setup import setup_logging
from cloud_arch_reviewer.prompts import load_prompt

PROMPT_FILES = ["system_prompt.md", "pillars.md", "few_shot_examples.md"]
USER_TEXT = "Review this architecture diagram against the six Well-Architected pillars."


def build_instructions() -> str:
    parts = []
    for name in PROMPT_FILES:
        text = load_prompt(name)
        parts.append(text)

    instructions = "\n\n".join(parts)
    return instructions


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/smoke_test.py samples/image_1.png")
        return 2

    image_path = sys.argv[1]
    settings = get_settings()
    setup_logging(settings.log_level)

    try:
        data_url = image_to_data_url(image_path, settings.max_image_mb)
        client = LLMClient(settings)
        instructions = build_instructions()
        review, usage = client.review_structured(instructions, data_url, USER_TEXT)

        print(f"Average score: {review.average_score()} | risks: {len(review.risks)}")
        print(usage.describe())
        print()

        narrative_instructions = load_prompt("narrative_prompt.md")
        for item in client.stream_narrative(narrative_instructions, review):
            if isinstance(item, Usage):
                print()
                print(item.describe())
            else:
                print(item, end="", flush=True)
    except (InvalidImageError, LLMError) as error:
        print(f"Error: {error}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())