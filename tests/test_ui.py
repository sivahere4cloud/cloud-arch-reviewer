from pathlib import Path

from test_reviewer import FakeClient
from test_reviewer import make_image
from test_reviewer import make_settings

from cloud_arch_reviewer.reviewer import Reviewer
from cloud_arch_reviewer.ui import ReviewHandler


def make_handler(client: FakeClient) -> ReviewHandler:
    reviewer = Reviewer(make_settings(), client)
    return ReviewHandler(reviewer)


def test_happy_path_ends_with_a_full_result(tmp_path):
    handler = make_handler(FakeClient(chunks=["Hello ", "world"]))

    outputs = list(handler.run(str(make_image(tmp_path)), None))

    last = outputs[-1]
    assert last[0] == "Done"
    assert "Overall score" in last[1]
    assert len(last[2]) == 6
    assert last[3] == "Hello world"
    assert "Total cost" in last[4]

    download_value = last[5].value
    assert last[5].interactive is True
    assert download_value["orig_name"] == "architecture-review.md"
    report_text = Path(download_value["path"]).read_text(encoding="utf-8")
    assert "# Architecture review" in report_text


def test_known_errors_are_shown_not_raised(tmp_path):
    handler = make_handler(FakeClient(chunks=[]))

    outputs = list(handler.run(str(tmp_path / "missing.png"), None))

    assert len(outputs) == 1
    assert "Problem" in outputs[0][0]
    assert outputs[0][5].interactive is False


def test_unexpected_errors_show_a_generic_message(tmp_path):
    client = FakeClient(chunks=[], structured_error=RuntimeError("secret detail"))
    handler = make_handler(client)

    outputs = list(handler.run(str(make_image(tmp_path)), None))

    assert "Something went wrong" in outputs[-1][0]
    assert "secret detail" not in outputs[-1][0]