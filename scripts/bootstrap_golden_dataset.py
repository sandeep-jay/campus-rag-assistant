#!/usr/bin/env python3
"""
Bootstrap golden_dataset.draft.json from live RAG (AWS Bedrock KB).

Run from repo root with .env configured for live providers:
  ./venv/bin/python scripts/bootstrap_golden_dataset.py

Requires RAG_FORCE_MOCK=false and working AWS/LLM credentials.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SEEDS = REPO_ROOT / 'backend/tests/eval/seed_questions.json'
DEFAULT_OUTPUT = REPO_ROOT / 'backend/tests/eval/golden_dataset.draft.json'
MAX_CONTEXTS = 3
MAX_GROUND_TRUTH_CHARS = 2000

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)


def _load_dotenv() -> None:
    env_path = REPO_ROOT / '.env'
    if env_path.is_file():
        from dotenv import load_dotenv

        load_dotenv(env_path, override=False)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Bootstrap golden dataset from live RAG runs.')
    parser.add_argument(
        '--seeds',
        type=Path,
        default=DEFAULT_SEEDS,
        help=f'JSON file with a list of question strings (default: {DEFAULT_SEEDS})',
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f'Output draft JSON path (default: {DEFAULT_OUTPUT})',
    )
    parser.add_argument('--dry-run', action='store_true', help='Print seeds only; do not call RAG.')
    parser.add_argument('--only', type=int, metavar='N', help='Process only the first N seed questions.')
    return parser.parse_args()


def _load_seeds(path: Path) -> list[str]:
    with open(path, encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list) or not all(isinstance(q, str) for q in data):
        raise ValueError(f'{path}: expected a JSON array of question strings')
    return [q.strip() for q in data if q.strip()]


def _assert_live_config() -> None:
    if os.environ.get('RAG_FORCE_MOCK', '').lower() in ('1', 'true', 'yes'):
        logger.error('RAG_FORCE_MOCK is enabled. Set RAG_FORCE_MOCK=false in .env for live bootstrap.')
        sys.exit(1)
    provider = (os.environ.get('LLM_PROVIDER') or 'aws').strip().lower()
    if provider == 'mock':
        logger.error('LLM_PROVIDER=mock. Use aws (or azure) with credentials for live bootstrap.')
        sys.exit(1)


def _clean_ground_truth(text: str) -> str:
    cleaned = ' '.join(text.split())
    if len(cleaned) > MAX_GROUND_TRUTH_CHARS:
        cleaned = cleaned[: MAX_GROUND_TRUTH_CHARS - 3].rstrip() + '...'
    return cleaned


def _extract_contexts(metadata: dict) -> list[str]:
    contexts: list[str] = []
    for doc in metadata.get('document_contents') or []:
        if not isinstance(doc, dict):
            continue
        content = (doc.get('content') or '').strip()
        if content:
            contexts.append(content)
        if len(contexts) >= MAX_CONTEXTS:
            break
    return contexts


def _bootstrap_row(question: str) -> dict:
    from backend.app.services import rag as rag_mod

    rag_mod._rag_service_instance = None
    service = rag_mod.RAGService()

    result = service.process_query(question, chat_history=[])
    metadata = result.get('metadata') or {}
    message = result.get('message') or ''
    contexts = _extract_contexts(metadata)
    sources = metadata.get('sources') or []

    row: dict = {
        'question': question,
        'ground_truth': _clean_ground_truth(message),
        'contexts': contexts,
        '_bootstrap': {
            'needs_review': True,
            'source_count': len(sources),
            'context_count': len(contexts),
            'source_kind': metadata.get('source_kind', 'kb'),
        },
    }
    if not contexts:
        row['_bootstrap']['warning'] = 'empty_retrieval'
    return row


def main() -> int:
    if str(REPO_ROOT) not in sys.path:
        sys.path.insert(0, str(REPO_ROOT))

    args = _parse_args()
    _load_dotenv()

    seeds = _load_seeds(args.seeds)
    if args.only is not None:
        seeds = seeds[: args.only]

    logger.info('Loaded %d seed question(s) from %s', len(seeds), args.seeds)

    if args.dry_run:
        for i, q in enumerate(seeds, start=1):
            print(f'{i}. {q}')
        return 0

    _assert_live_config()

    from backend.app.core.config_manager import settings

    engine = getattr(settings, 'RAG_ENGINE', 'chain')
    provider = getattr(settings, 'LLM_PROVIDER', 'aws')
    logger.info('RAG_ENGINE=%s LLM_PROVIDER=%s — starting live bootstrap...', engine, provider)

    rows: list[dict] = []
    for i, question in enumerate(seeds, start=1):
        logger.info('[%d/%d] %s', i, len(seeds), question[:80])
        try:
            row = _bootstrap_row(question)
        except Exception as exc:
            logger.exception('RAG failed for question %r: %s', question[:60], exc)
            row = {
                'question': question,
                'ground_truth': '',
                'contexts': [],
                '_bootstrap': {'needs_review': True, 'error': str(exc)},
            }
        rows.append(row)
        ctx_n = len(row.get('contexts') or [])
        logger.info('  -> %d context chunk(s), ground_truth %d chars', ctx_n, len(row.get('ground_truth') or ''))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(rows, f, indent=2, ensure_ascii=False)
        f.write('\n')

    empty = sum(1 for r in rows if not r.get('contexts'))
    logger.info(
        'Wrote %d row(s) to %s (%d with empty contexts — review before promoting)',
        len(rows),
        args.output,
        empty,
    )
    logger.info('Edit ground_truth and contexts, then copy to golden_dataset.json')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
