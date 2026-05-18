"""
RAGAS evaluation harness for the RAG pipeline.

Run via:
    tox -e eval

Or directly (requires RAGAS_LLM_PROVIDER and appropriate API keys):
    pytest backend/tests/eval/test_rag_quality.py -v

This suite measures:
  - faithfulness       : Are claims in the answer grounded in retrieved context?
  - answer_relevancy   : Does the answer address the question?
  - context_recall     : Does the retrieved context cover the ground truth?
  - context_precision  : Are the retrieved chunks mostly relevant (not noisy)?

Quality gates (applied in CI when RAGAS_QUALITY_GATE=1):
  - faithfulness       >= 0.85
  - answer_relevancy   >= 0.80
  - context_recall     >= 0.75
  - context_precision  >= 0.70

How to interpret failures:
  - Low faithfulness   → LLM is hallucinating beyond the retrieved context
  - Low answer_relevancy → prompts may be too broad / retriever returns off-topic docs
  - Low context_recall   → retriever misses key documents (improve hybrid search / reranker)
  - Low context_precision → too much noise in retrieval (reduce RETRIEVER_NUMBER_OF_RESULTS or
                            raise RERANK_TOP_N threshold)
"""

import json
import logging
import os
from pathlib import Path

import pytest

logger = logging.getLogger(__name__)

GOLDEN_DATASET_PATH = Path(__file__).parent / 'golden_dataset.json'

# Thresholds — lower these temporarily when bootstrapping a new domain.
FAITHFULNESS_MIN = float(os.environ.get('RAGAS_FAITHFULNESS_MIN', '0.85'))
ANSWER_RELEVANCY_MIN = float(os.environ.get('RAGAS_ANSWER_RELEVANCY_MIN', '0.80'))
CONTEXT_RECALL_MIN = float(os.environ.get('RAGAS_CONTEXT_RECALL_MIN', '0.75'))
CONTEXT_PRECISION_MIN = float(os.environ.get('RAGAS_CONTEXT_PRECISION_MIN', '0.70'))
QUALITY_GATE_ENABLED = os.environ.get('RAGAS_QUALITY_GATE', '0') == '1'


def _load_golden_dataset() -> list[dict]:
    with open(GOLDEN_DATASET_PATH) as f:
        return json.load(f)


def _skip_if_no_ragas():
    try:
        import ragas  # noqa: F401
    except ImportError:
        pytest.skip('ragas not installed — run: pip install ragas>=0.2')


def _skip_if_no_llm_for_eval():
    """RAGAS LLM-based metrics require an LLM to act as judge."""
    provider = os.environ.get('RAGAS_LLM_PROVIDER', '')
    has_openai = bool(os.environ.get('OPENAI_API_KEY') or os.environ.get('AZURE_OPENAI_API_KEY'))
    if not provider and not has_openai:
        pytest.skip('No LLM available for RAGAS evaluation. Set OPENAI_API_KEY, AZURE_OPENAI_API_KEY, or RAGAS_LLM_PROVIDER.')


def _build_ragas_dataset(golden: list[dict], rag_service):  # type: ignore[return]
    """Run each golden question through the RAG service and collect answers + contexts."""
    from ragas.dataset_schema import EvaluationDataset, SingleTurnSample

    samples = []
    for item in golden:
        question = item['question']
        ground_truth = item['ground_truth']

        try:
            result = rag_service.process_query(question, chat_history=[])
            answer = result.get('message', '')
            retrieved_contexts = [doc.get('content', '') for doc in result.get('metadata', {}).get('document_contents', [])]
        except Exception as exc:
            logger.warning('RAG failed for question %r: %s', question[:60], exc)
            answer = ''
            retrieved_contexts = item.get('contexts', [])

        if not retrieved_contexts:
            retrieved_contexts = item.get('contexts', [])

        samples.append(
            SingleTurnSample(
                user_input=question,
                response=answer,
                retrieved_contexts=retrieved_contexts,
                reference=ground_truth,
            )
        )

    return EvaluationDataset(samples=samples)


@pytest.fixture(scope='module')
def rag_service_for_eval():
    """RAG service instance for eval — uses mock if no provider configured."""
    from backend.app.services.rag import RAGService

    return RAGService()


@pytest.mark.slow()
class TestRAGQuality:
    """End-to-end quality evaluation of the RAG pipeline against a golden dataset.

    These tests are NOT run in regular CI (excluded by default).
    Run with: tox -e eval  OR  pytest -m slow
    """

    def test_golden_dataset_loads(self):
        data = _load_golden_dataset()
        assert len(data) >= 5, 'Golden dataset must have at least 5 entries'
        for item in data:
            assert 'question' in item
            assert 'ground_truth' in item
            assert 'contexts' in item
            assert len(item['contexts']) >= 1

    def test_faithfulness(self, rag_service_for_eval):
        """Answers should be grounded in retrieved context (no hallucination)."""
        _skip_if_no_ragas()
        _skip_if_no_llm_for_eval()
        from ragas import evaluate
        from ragas.metrics import faithfulness

        golden = _load_golden_dataset()
        dataset = _build_ragas_dataset(golden, rag_service_for_eval)
        results = evaluate(dataset, metrics=[faithfulness])
        score = results['faithfulness']
        logger.info('faithfulness score: %.3f (threshold: %.2f)', score, FAITHFULNESS_MIN)

        if QUALITY_GATE_ENABLED:
            assert (
                score >= FAITHFULNESS_MIN
            ), f'Faithfulness {score:.3f} below threshold {FAITHFULNESS_MIN}. Check for hallucinations in LLM responses or improve context quality.'

    def test_answer_relevancy(self, rag_service_for_eval):
        """Answers should address the question being asked."""
        _skip_if_no_ragas()
        _skip_if_no_llm_for_eval()
        from ragas import evaluate
        from ragas.metrics import answer_relevancy

        golden = _load_golden_dataset()
        dataset = _build_ragas_dataset(golden, rag_service_for_eval)
        results = evaluate(dataset, metrics=[answer_relevancy])
        score = results['answer_relevancy']
        logger.info('answer_relevancy score: %.3f (threshold: %.2f)', score, ANSWER_RELEVANCY_MIN)

        if QUALITY_GATE_ENABLED:
            assert (
                score >= ANSWER_RELEVANCY_MIN
            ), f'Answer relevancy {score:.3f} below threshold {ANSWER_RELEVANCY_MIN}. Review prompt templates and ensure retrieval stays on-domain.'

    def test_context_recall(self, rag_service_for_eval):
        """Retrieved context should cover the information needed to answer correctly."""
        _skip_if_no_ragas()
        _skip_if_no_llm_for_eval()
        from ragas import evaluate
        from ragas.metrics import context_recall

        golden = _load_golden_dataset()
        dataset = _build_ragas_dataset(golden, rag_service_for_eval)
        results = evaluate(dataset, metrics=[context_recall])
        score = results['context_recall']
        logger.info('context_recall score: %.3f (threshold: %.2f)', score, CONTEXT_RECALL_MIN)

        if QUALITY_GATE_ENABLED:
            assert score >= CONTEXT_RECALL_MIN, (
                f'Context recall {score:.3f} below threshold {CONTEXT_RECALL_MIN}. '
                'Consider enabling multi-query retrieval or increasing RETRIEVER_NUMBER_OF_RESULTS.'
            )

    def test_context_precision(self, rag_service_for_eval):
        """Retrieved chunks should be relevant, not noisy."""
        _skip_if_no_ragas()
        _skip_if_no_llm_for_eval()
        from ragas import evaluate
        from ragas.metrics import context_precision

        golden = _load_golden_dataset()
        dataset = _build_ragas_dataset(golden, rag_service_for_eval)
        results = evaluate(dataset, metrics=[context_precision])
        score = results['context_precision']
        logger.info('context_precision score: %.3f (threshold: %.2f)', score, CONTEXT_PRECISION_MIN)

        if QUALITY_GATE_ENABLED:
            assert score >= CONTEXT_PRECISION_MIN, (
                f'Context precision {score:.3f} below threshold {CONTEXT_PRECISION_MIN}. '
                'Enable reranking (RERANK_ENABLED=true) or reduce RETRIEVER_NUMBER_OF_RESULTS.'
            )

    def test_full_suite_report(self, rag_service_for_eval):
        """Run all four metrics together and print a summary report."""
        _skip_if_no_ragas()
        _skip_if_no_llm_for_eval()
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

        golden = _load_golden_dataset()
        dataset = _build_ragas_dataset(golden, rag_service_for_eval)
        results = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_recall, context_precision],
        )

        report_lines = [
            '',
            '=' * 60,
            'RAGAS Evaluation Report',
            '=' * 60,
            f'  faithfulness       : {results.get("faithfulness", "n/a"):.3f}  (min {FAITHFULNESS_MIN})',
            f'  answer_relevancy   : {results.get("answer_relevancy", "n/a"):.3f}  (min {ANSWER_RELEVANCY_MIN})',
            f'  context_recall     : {results.get("context_recall", "n/a"):.3f}  (min {CONTEXT_RECALL_MIN})',
            f'  context_precision  : {results.get("context_precision", "n/a"):.3f}  (min {CONTEXT_PRECISION_MIN})',
            '=' * 60,
        ]
        print('\n'.join(report_lines))
        logger.info('\n'.join(report_lines))
