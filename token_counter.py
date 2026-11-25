"""Count Claude input tokens before sending a request.

Uses the free `POST /v1/messages/count_tokens` endpoint through the official
Anthropic Python SDK. Supports plain text, text files, images and PDFs
(sent as base64, since the endpoint rejects `url` / `file` sources), an
optional system prompt, and comparing the same request across several models
(models from Claude Opus 4.7 onward use a newer tokenizer).
"""

from __future__ import annotations

import argparse
import base64
import mimetypes
import sys
from pathlib import Path
from typing import Any, Sequence

import anthropic

DEFAULT_MODEL = "claude-opus-5-5"

IMAGE_TYPES = {"image/jpeg", "image/png", "image/gif", "image/webp"}
PDF_TYPE = "application/pdf"


def file_to_block(path: Path) -> dict[str, Any]:
    """Turn a local file into a content block: image, PDF document, or text."""
    media_type, _ = mimetypes.guess_type(path.name)
    if media_type in IMAGE_TYPES or media_type == PDF_TYPE:
        data = base64.standard_b64encode(path.read_bytes()).decode("ascii")
        block_type = "document" if media_type == PDF_TYPE else "image"
        return {
            "type": block_type,
            "source": {"type": "base64", "media_type": media_type, "data": data},
        }
    return {"type": "text", "text": path.read_text(encoding="utf-8")}


def build_content(texts: Sequence[str], files: Sequence[Path]) -> list[dict[str, Any]]:
    # Images and documents go before the text, as the API docs recommend.
    file_blocks = [file_to_block(p) for p in files]
    media = [b for b in file_blocks if b["type"] != "text"]
    file_texts = [b for b in file_blocks if b["type"] == "text"]
    text_blocks = [{"type": "text", "text": t} for t in texts]
    content = media + file_texts + text_blocks
    if not content:
        raise ValueError("nothing to count: pass text, --file or --stdin")
    return content


def count_tokens(
    client: anthropic.Anthropic,
    model: str,
    content: list[dict[str, Any]],
    system: str | None = None,
) -> int:
    params: dict[str, Any] = {
        "model": model,
        "messages": [{"role": "user", "content": content}],
    }
    if system:
        params["system"] = system
    return client.messages.count_tokens(**params).input_tokens


def parse_args(argv: Sequence[str] | None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Count Claude input tokens via the count_tokens endpoint."
    )
    p.add_argument("text", nargs="*", help="text to count")
    p.add_argument("-f", "--file", action="append", default=[], type=Path,
                   help="text, image (jpg/png/gif/webp) or PDF file; repeatable")
    p.add_argument("--stdin", action="store_true", help="read text from stdin")
    p.add_argument("-s", "--system", help="system prompt to include")
    p.add_argument("-m", "--model", action="append", dest="models",
                   help=f"model ID; repeat to compare models (default {DEFAULT_MODEL})")
    return p.parse_args(argv)


def main(argv: Sequence[str] | None = None, client: anthropic.Anthropic | None = None) -> int:
    args = parse_args(argv)
    texts = list(args.text)
    if args.stdin:
        texts.append(sys.stdin.read())
    try:
        content = build_content(texts, args.file)
    except (ValueError, OSError) as e:
        print(f"error: {e}", file=sys.stderr)
        return 2

    models = args.models or [DEFAULT_MODEL]
    client = client or anthropic.Anthropic()
    results: list[tuple[str, int]] = []
    for model in models:
        try:
            results.append((model, count_tokens(client, model, content, args.system)))
        except anthropic.BadRequestError as e:
            print(f"error ({model}): invalid request: {e.message}", file=sys.stderr)
            return 1
        except anthropic.RateLimitError:
            print(f"error ({model}): rate limited, try again later", file=sys.stderr)
            return 1
        except anthropic.APIStatusError as e:
            print(f"error ({model}): HTTP {e.status_code}: {e.message}", file=sys.stderr)
            return 1
        except anthropic.APIConnectionError as e:
            print(f"error ({model}): connection failed: {e}", file=sys.stderr)
            return 1
        except TypeError as e:
            if "authentication" not in str(e):
                raise
            print("error: no credentials; set ANTHROPIC_API_KEY or run `ant auth login`",
                  file=sys.stderr)
            return 1

    if len(results) == 1:
        print(results[0][1])
    else:
        base = results[0][1]
        width = max(len(m) for m, _ in results)
        for model, n in results:
            delta = f"{(n - base) / base:+.1%}" if base else "n/a"
            print(f"{model:<{width}}  {n:>10}  {delta}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
