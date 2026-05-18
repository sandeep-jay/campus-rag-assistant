"""Tests for RAGAS judge provider resolution."""

from unittest.mock import MagicMock, patch

import pytest

from backend.app.services.eval import ragas_judge


@pytest.fixture(autouse=True)
def _clear_judge_cache():
    ragas_judge.get_ragas_judge_llm.cache_clear()
    ragas_judge.get_ragas_judge_embeddings.cache_clear()
    yield
    ragas_judge.get_ragas_judge_llm.cache_clear()
    ragas_judge.get_ragas_judge_embeddings.cache_clear()


def test_resolve_judge_prefers_ragas_llm_provider_env():
    with patch.dict('os.environ', {'RAGAS_LLM_PROVIDER': 'azure'}, clear=False):
        assert ragas_judge.resolve_judge_provider() == 'azure'


def test_judge_not_configured_for_mock():
    with patch.object(ragas_judge, 'resolve_judge_provider', return_value='mock'):
        assert ragas_judge.judge_provider_configured() is False


def test_get_ragas_judge_llm_uses_app_provider():
    fake_llm = MagicMock()
    fake_provider = MagicMock(is_mock=False)
    fake_provider.get_streaming_llm.return_value = fake_llm
    with (
        patch.object(ragas_judge, 'resolve_judge_provider', return_value='aws'),
        patch('backend.app.services.providers.get_llm_provider', return_value=fake_provider),
    ):
        assert ragas_judge.get_ragas_judge_llm() is fake_llm


def test_get_ragas_judge_llm_rejects_mock_provider():
    fake_provider = MagicMock(is_mock=True)
    with (
        patch.object(ragas_judge, 'resolve_judge_provider', return_value='azure'),
        patch('backend.app.services.providers.get_llm_provider', return_value=fake_provider),
        pytest.raises(ValueError, match='mock'),
    ):
        ragas_judge.get_ragas_judge_llm()


def test_metric_score_averages_list():
    from backend.app.services.eval.ragas_judge import metric_score

    assert metric_score({'faithfulness': [0.8, 0.9, 0.7]}, 'faithfulness') == pytest.approx(0.8, rel=1e-3)


def test_metric_score_raises_when_all_nan():
    from backend.app.services.eval.ragas_judge import metric_score

    with pytest.raises(ValueError, match='all .* samples failed'):
        metric_score({'faithfulness': [float('nan')] * 3}, 'faithfulness')
