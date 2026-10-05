import logging
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import gradio as gr

from cloud_arch_reviewer.llm_client import Usage
from cloud_arch_reviewer.pricing import format_cost
from cloud_arch_reviewer.report import build_markdown_report
from cloud_arch_reviewer.report import scorecard_rows
from cloud_arch_reviewer.reviewer import USER_FACING_ERRORS
from cloud_arch_reviewer.reviewer import ReviewState
from cloud_arch_reviewer.reviewer import Reviewer

logger = logging.getLogger(__name__)

UPDATE_INTERVAL_SECONDS = 0.15
REPORT_FILE_NAME = "architecture-review.md"
DOWNLOAD_LABEL = "Download report (.md)"


def format_score(state: ReviewState) -> str:
    if state.review is None:
        return ""

    return f"### Overall score: {state.review.average_score()} / 5"


def format_usage(usages: tuple[Usage, ...]) -> str:
    if len(usages) == 0:
        return ""

    lines = []
    total = 0.0
    has_unknown_cost = False
    for usage in usages:
        lines.append(f"- `{usage.describe()}`")
        if usage.cost_usd is None:
            has_unknown_cost = True
        else:
            total = total + usage.cost_usd

    if not has_unknown_cost:
        lines.append("")
        lines.append(f"**Total cost: {format_cost(total)}**")

    return "\n".join(lines)


def write_report_file(report: str) -> str:
    folder = Path(tempfile.mkdtemp(prefix="cloud-arch-reviewer-"))
    path = folder / REPORT_FILE_NAME
    path.write_text(report, encoding="utf-8")
    return str(path)


def build_outputs(state: ReviewState, report_path: str | None) -> tuple[Any, ...]:
    rows: list[list[str | int]] = []
    if state.review is not None:
        rows = scorecard_rows(state.review)

    if report_path is None:
        download = gr.DownloadButton(label=DOWNLOAD_LABEL, interactive=False)
    else:
        download = gr.DownloadButton(
            label=DOWNLOAD_LABEL, value=report_path, interactive=True
        )

    return (
        state.stage,
        format_score(state),
        rows,
        state.narrative,
        format_usage(state.usages),
        download,
    )


def error_outputs(message: str) -> tuple[Any, ...]:
    download = gr.DownloadButton(label=DOWNLOAD_LABEL, interactive=False)
    return (f"**Problem:** {message}", "", [], "", "", download)


class ReviewHandler:
    def __init__(self, reviewer: Reviewer) -> None:
        self._reviewer = reviewer

    def run(
        self,
        image_path: str | None,
        description: str | None,
    ) -> Iterator[tuple[Any, ...]]:
        last_yield = 0.0
        last_stage = ""
        final_state: ReviewState | None = None

        try:
            for state in self._reviewer.review_diagram(image_path, description):
                final_state = state
                if state.finished:
                    continue

                now = time.monotonic()
                stage_changed = state.stage != last_stage
                update_due = now - last_yield >= UPDATE_INTERVAL_SECONDS
                if stage_changed or update_due:
                    yield build_outputs(state, None)
                    last_yield = now
                    last_stage = state.stage
        except USER_FACING_ERRORS as error:
            yield error_outputs(str(error))
            return
        except Exception:
            logger.exception("Unexpected error during review")
            yield error_outputs("Something went wrong. Please try again.")
            return

        if final_state is None or final_state.review is None:
            yield error_outputs("No review was produced. Please try again.")
            return

        report = build_markdown_report(
            final_state.review, final_state.narrative, list(final_state.usages)
        )
        report_path = write_report_file(report)
        yield build_outputs(final_state, report_path)