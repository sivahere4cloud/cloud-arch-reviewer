import gradio as gr
from test_reviewer import FakeClient
from test_reviewer import make_settings

from cloud_arch_reviewer.app import build_app
from cloud_arch_reviewer.reviewer import Reviewer
from cloud_arch_reviewer.ui import ReviewHandler


def test_build_app_creates_a_blocks_app():
    reviewer = Reviewer(make_settings(), FakeClient(chunks=[]))
    app = build_app(ReviewHandler(reviewer))

    assert isinstance(app, gr.Blocks)