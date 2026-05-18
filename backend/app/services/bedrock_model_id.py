"""Map Bedrock foundation model IDs to regional inference profiles when required."""

from __future__ import annotations


def inference_profile_prefix(region: str | None) -> str | None:
    """Bedrock cross-region inference profile prefix for an AWS region."""
    r = (region or 'us-east-1').lower()
    if r.startswith('us-gov'):
        return 'us-gov'
    if r.startswith('us-'):
        return 'us'
    if r.startswith('eu-'):
        return 'eu'
    if r.startswith(('ap-northeast', 'ap-southeast', 'ap-south', 'ap-east')):
        return 'apac'
    return None


def _needs_inference_profile(model_id: str) -> bool:
    """Models that reject on-demand invoke without a regional inference profile."""
    return model_id.startswith(
        (
            'anthropic.claude-3-5',
            'anthropic.claude-3-7',
            'anthropic.claude-sonnet-4',
            'anthropic.claude-haiku-4',
        ),
    )


def resolve_bedrock_model_id(model_id: str, region: str | None = None) -> str:
    """
    Return modelId suitable for invoke_model / ChatBedrock.

    Newer Anthropic models (e.g. claude-3-5-haiku) must use IDs like
    ``us.anthropic.claude-3-5-haiku-20241022-v1:0`` instead of ``anthropic.*``.
    """
    model_id = (model_id or '').strip()
    if not model_id:
        return model_id
    if model_id.startswith(('us.', 'eu.', 'apac.', 'us-gov.')):
        return model_id
    if not _needs_inference_profile(model_id):
        return model_id
    prefix = inference_profile_prefix(region)
    if not prefix:
        return model_id
    return f'{prefix}.{model_id}'
