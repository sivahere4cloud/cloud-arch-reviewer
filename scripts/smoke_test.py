import sys
from pathlib import Path

from cloud_arch_reviewer.config import get_settings
from cloud_arch_reviewer.logging_setup import setup_logging
from cloud_arch_reviewer.report import build_markdown_report
from cloud_arch_reviewer.reviewer import USER_FACING_ERRORS
from cloud_arch_reviewer.reviewer import ReviewState
from cloud_arch_reviewer.reviewer import Reviewer

REPORT_PATH = Path("samples") / "report.md"


def main() -> int:
    if len(sys.argv) < 2:
        print('Usage: uv run python scripts/smoke_test.py samples/image_1.png "optional description"')
        return 2

    image_path = sys.argv[1]
    description = " ".join(sys.argv[2:])
    settings = get_settings()
    setup_logging(settings.log_level)

    final_state: ReviewState | None = None
    update_count = 0
    last_stage = ""

    try:
        reviewer = Reviewer(settings)
        for state in reviewer.review_diagram(image_path, description):
            update_count = update_count + 1
            if state.stage != last_stage:
                print(f"[stage] {state.stage}")
                last_stage = state.stage
            final_state = state
    except USER_FACING_ERRORS as error:
        print(f"Error: {error}")
        return 1

    if final_state is None or final_state.review is None:
        print("Error: no review was produced.")
        return 1

    print(f"{update_count} updates")
    print(f"Average score: {final_state.review.average_score()}")
    for usage in final_state.usages:
        print(usage.describe())

    usages = list(final_state.usages)
    report = build_markdown_report(final_state.review, final_state.narrative, usages)
    REPORT_PATH.parent.mkdir(exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(f"Report saved to {REPORT_PATH} ({len(report.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())