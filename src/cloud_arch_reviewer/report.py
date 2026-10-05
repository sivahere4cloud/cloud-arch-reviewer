from cloud_arch_reviewer.llm_client import Usage
from cloud_arch_reviewer.schemas import ArchitectureReview

SCORECARD_HEADERS = ["Pillar", "Score", "Rationale"]
SEVERITY_ORDER = ["critical", "high", "medium", "low"]


def _clean_cell(text: str) -> str:
    cleaned = text.replace("|", "\\|")
    cleaned = cleaned.replace("\r", " ")
    cleaned = cleaned.replace("\n", " ")
    return cleaned


def _demote_headings(text: str) -> str:
    lines = []
    for line in text.splitlines():
        if line.startswith("## "):
            line = "#" + line
        lines.append(line)

    return "\n".join(lines)


def scorecard_rows(review: ArchitectureReview) -> list[list[str | int]]:
    rows: list[list[str | int]] = []
    for item in review.pillar_scores:
        row: list[str | int] = [item.pillar, item.score, item.rationale]
        rows.append(row)

    return rows


def build_markdown_report(
    review: ArchitectureReview,
    narrative: str,
    usages: list[Usage],
) -> str:
    lines: list[str] = []

    lines.append("# Architecture review")
    lines.append("")
    lines.append(f"**Overall score:** {review.average_score()} / 5")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(review.summary)
    lines.append("")

    lines.append("## Scorecard")
    lines.append("")
    lines.append("| Pillar | Score | Rationale |")
    lines.append("|---|---|---|")
    for item in review.pillar_scores:
        rationale = _clean_cell(item.rationale)
        lines.append(f"| {item.pillar} | {item.score} | {rationale} |")
    lines.append("")

    lines.append("## Risks")
    lines.append("")
    if len(review.risks) == 0:
        lines.append("No risks were reported.")
        lines.append("")
    for severity in SEVERITY_ORDER:
        for risk in review.risks:
            if risk.severity != severity:
                continue
            lines.append(f"### {severity.upper()}: {risk.title}")
            lines.append("")
            lines.append(f"*Pillar: {risk.pillar}*")
            lines.append("")
            lines.append(risk.description)
            lines.append("")
            lines.append(f"**Fix:** {risk.suggested_fix}")
            lines.append("")

    if narrative.strip() != "":
        lines.append("## Written review")
        lines.append("")
        lines.append(_demote_headings(narrative.strip()))
        lines.append("")

    if len(review.unclear_items) > 0:
        lines.append("## Could not be confirmed from the diagram")
        lines.append("")
        for unclear in review.unclear_items:
            lines.append(f"- {unclear}")
        lines.append("")

    lines.append("## Detected services")
    lines.append("")
    for service in review.detected_services:
        lines.append(f"- {service}")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append(
        "Generated with cloud-arch-reviewer. AI reviews can be wrong, "
        "so check every finding against your real architecture."
    )
    lines.append("")
    for usage in usages:
        lines.append(f"- `{usage.describe()}`")
    lines.append("")

    return "\n".join(lines)