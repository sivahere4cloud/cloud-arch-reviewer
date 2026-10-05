import gradio as gr

from cloud_arch_reviewer.config import get_settings
from cloud_arch_reviewer.logging_setup import setup_logging
from cloud_arch_reviewer.report import SCORECARD_HEADERS
from cloud_arch_reviewer.reviewer import Reviewer
from cloud_arch_reviewer.ui import DOWNLOAD_LABEL
from cloud_arch_reviewer.ui import ReviewHandler

TITLE = "Cloud Architecture Reviewer"
INTRO = (
    "Upload an AWS architecture diagram to get a Well-Architected review: "
    "a scorecard, risks and suggested fixes. "
    "The image and description are sent to OpenAI, so do not upload confidential "
    "diagrams. AI reviews can be wrong, so check every finding against your "
    "real architecture."
)
MAX_QUEUE_SIZE = 10
MAX_CONCURRENT_REVIEWS = 2


def build_app(handler: ReviewHandler) -> gr.Blocks:
    with gr.Blocks(title=TITLE) as demo:
        gr.Markdown(f"# {TITLE}")
        gr.Markdown(INTRO)

        with gr.Row():
            with gr.Column(scale=1):
                image = gr.Image(
                    label="Architecture diagram",
                    type="filepath",
                    sources=["upload", "clipboard"],
                    height=400,
                )
                description = gr.Textbox(
                    label="Description (optional)",
                    placeholder="For example: a three-tier web app. The database is not shown.",
                    lines=3,
                )
                review_button = gr.Button("Review diagram", variant="primary")
                status = gr.Markdown()
                usage = gr.Markdown()

            with gr.Column(scale=2):
                score = gr.Markdown()
                scorecard = gr.Dataframe(
                    headers=SCORECARD_HEADERS,
                    label="Scorecard",
                    interactive=False,
                    wrap=True,
                )
                narrative = gr.Markdown()
                download = gr.DownloadButton(label=DOWNLOAD_LABEL, interactive=False)

        review_button.click(
            fn=handler.run,
            inputs=[image, description],
            outputs=[status, score, scorecard, narrative, usage, download],
        )

    demo.queue(
        max_size=MAX_QUEUE_SIZE,
        default_concurrency_limit=MAX_CONCURRENT_REVIEWS,
    )
    return demo


def run() -> None:
    settings = get_settings()
    setup_logging(settings.log_level)

    reviewer = Reviewer(settings)
    handler = ReviewHandler(reviewer)
    app = build_app(handler)
    app.launch(theme=gr.themes.Soft())