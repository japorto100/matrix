"""Convert ConvoMem-style evidence files into the shared memory-eval schema.

Erwarteter Input:
- JSON-Datei mit einer Liste von Evidence-Items
- jedes Item enthaelt mindestens:
  - `question`
  - `answer`
  - `message_evidences` (optional, fuer exact substring checks)
  - `conversations`: Liste von Conversation-Objekten mit `messages`

Output:
- gemeinsames Schema fuer `run_hindsight_eval.py`, `run_fusion_eval.py`, ...
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _message_to_line(message: dict[str, Any]) -> str:
    speaker = str(message.get("speaker") or message.get("role") or "unknown").strip()
    text = str(message.get("text") or message.get("content") or "").strip()
    return f"{speaker}: {text}".strip()


def _conversation_text(conversation: dict[str, Any]) -> str:
    messages = list(conversation.get("messages") or [])
    return "\n".join(line for line in (_message_to_line(message) for message in messages) if line)


def _expected_substring(item: dict[str, Any]) -> str:
    evidences = list(item.get("message_evidences") or [])
    if evidences:
        first = evidences[0]
        return str(first.get("text") or "").strip()
    return str(item.get("answer") or "").strip()


def convert_convomem(
    data: list[dict[str, Any]],
    *,
    corpus_id: str,
    bank_id: str,
    category: str,
) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    queries: list[dict[str, Any]] = []

    for evidence_idx, evidence in enumerate(data):
        conversations = list(evidence.get("conversations") or [])
        expected_refs: list[str] = []

        for conv_idx, conversation in enumerate(conversations):
            source_ref = f"convomem-{evidence_idx:05d}-{conv_idx:02d}.jsonl#0"
            expected_refs.append(source_ref)
            items.append(
                {
                    "source_ref": source_ref,
                    "source_file": source_ref.split("#", 1)[0],
                    "text": _conversation_text(conversation),
                    "fact_type": "experience",
                    "tags": ["convomem", category],
                }
            )

        queries.append(
            {
                "query": str(evidence.get("question") or "").strip(),
                "expected_refs": expected_refs,
                "expected_substring": _expected_substring(evidence),
                "category": category,
                "answer": str(evidence.get("answer") or "").strip(),
            }
        )

    return {
        "corpus_id": corpus_id,
        "bank_id": bank_id,
        "items": items,
        "queries": queries,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_json")
    parser.add_argument("--out", required=True)
    parser.add_argument("--corpus-id", default="convomem-adapter")
    parser.add_argument("--bank-id", default="user_eval_convomem")
    parser.add_argument("--category", default="convomem")
    args = parser.parse_args()

    data = json.loads(Path(args.input_json).read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise SystemExit("Expected top-level JSON list for ConvoMem evidence file")

    converted = convert_convomem(
        data,
        corpus_id=args.corpus_id,
        bank_id=args.bank_id,
        category=args.category,
    )
    Path(args.out).write_text(json.dumps(converted, indent=2), encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
