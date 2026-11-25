import base64
from types import SimpleNamespace

import pytest

import token_counter as tc


class FakeMessages:
    def __init__(self, counts):
        self.counts = counts
        self.calls = []

    def count_tokens(self, **params):
        self.calls.append(params)
        return SimpleNamespace(input_tokens=self.counts[params["model"]])


class FakeClient:
    def __init__(self, counts):
        self.messages = FakeMessages(counts)


def test_text_file_becomes_text_block(tmp_path):
    p = tmp_path / "a.md"
    p.write_text("hello", encoding="utf-8")
    assert tc.file_to_block(p) == {"type": "text", "text": "hello"}


def test_image_and_pdf_are_base64(tmp_path):
    img = tmp_path / "x.png"
    img.write_bytes(b"\x89PNG")
    pdf = tmp_path / "d.pdf"
    pdf.write_bytes(b"%PDF-1.4")
    ib, db = tc.file_to_block(img), tc.file_to_block(pdf)
    assert ib["type"] == "image" and ib["source"]["media_type"] == "image/png"
    assert base64.b64decode(ib["source"]["data"]) == b"\x89PNG"
    assert db["type"] == "document" and db["source"]["media_type"] == "application/pdf"


def test_media_blocks_come_first(tmp_path):
    img = tmp_path / "x.jpg"
    img.write_bytes(b"jpg")
    content = tc.build_content(["question"], [img])
    assert [b["type"] for b in content] == ["image", "text"]


def test_empty_input_is_an_error():
    with pytest.raises(ValueError):
        tc.build_content([], [])


def test_single_model_prints_count(capsys):
    client = FakeClient({tc.DEFAULT_MODEL: 14})
    assert tc.main(["Hello, Claude", "-s", "You are a scientist"], client=client) == 0
    assert capsys.readouterr().out.strip() == "14"
    call = client.messages.calls[0]
    assert call["system"] == "You are a scientist"
    assert call["messages"][0]["role"] == "user"


def test_compare_models(capsys):
    client = FakeClient({"claude-sonnet-4-6": 100, "claude-opus-5-5": 130})
    rc = tc.main(["hi", "-m", "claude-sonnet-4-6", "-m", "claude-opus-5-5"], client=client)
    assert rc == 0
    out = capsys.readouterr().out
    assert "+30.0%" in out and "+0.0%" in out
