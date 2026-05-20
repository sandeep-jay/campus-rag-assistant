"""CI guard: keep `.env.example` in sync with `DefaultSettings`.

If you add or rename a field in :class:`backend.app.config.default.DefaultSettings`,
update ``.env.example`` in the same commit. ``.env.example`` is the contract we
ship to operators — drift here is how secrets / required knobs go undocumented.

This file lives in ``backend/tests/core`` so it runs in the default backend tox
environment alongside the rest of the unit tests.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from backend.app.config.default import DefaultSettings

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_EXAMPLE = REPO_ROOT / '.env.example'

# Fields that are derived from other fields (validators) or otherwise should
# not appear verbatim in the operator-facing template. Keep this list small.
_DERIVED_FIELDS = frozenset(
    {
        # Built from DATABASE_URL by assemble_db_connection().
        'SQLALCHEMY_DATABASE_URI',
    },
)


def _template_keys() -> set[str]:
    text = ENV_EXAMPLE.read_text(encoding='utf-8')
    # Match VAR_NAME= even if the line is commented out (operators uncomment
    # them when wiring up).
    return set(re.findall(r'(?m)^\s*#?\s*([A-Z][A-Z0-9_]+)\s*=', text))


def test_env_example_exists() -> None:
    assert ENV_EXAMPLE.is_file(), f'.env.example missing at {ENV_EXAMPLE}'


def test_every_settings_field_is_documented_in_env_example() -> None:
    """Each ``DefaultSettings`` field must appear in ``.env.example``.

    Operators rely on the template to discover available knobs. Missing
    fields are silent regressions, especially for required credentials.
    """
    declared = set(DefaultSettings.model_fields.keys()) - _DERIVED_FIELDS
    documented = _template_keys()
    missing = sorted(declared - documented)
    assert not missing, (
        '.env.example is missing entries for Settings fields: '
        f'{missing}. Add them (commented or uncommented) with the appropriate '
        '[REQUIRED] / [OPTIONAL] annotation.'
    )


@pytest.mark.parametrize(
    'field',
    sorted(name for name, info in DefaultSettings.model_fields.items() if 'SecretStr' in str(info.annotation)),
)
def test_secret_fields_are_documented(field: str) -> None:
    """Every ``SecretStr``-typed field must be present in ``.env.example``.

    Per-field parametrization makes failures pinpoint the missing credential
    rather than dumping a list.
    """
    assert field in _template_keys(), (
        f'Secret field {field!r} is missing from .env.example. ' 'Document it (commented out, with no real value) so operators know ' 'it exists.'
    )


# Obvious placeholder patterns that ARE allowed as uncommented values for
# secret fields in ``.env.example``. Anything else uncommented = guard fail.
_PLACEHOLDER_MARKERS = (
    'change-me',
    'change_me',
    'changeme',
    'your-',
    'your_',
    'replace-me',
    'replace_me',
    'replaceme',
    'placeholder',
    'example',
    'xxx',
    '...',
    'todo',
)


def _is_placeholder(value: str) -> bool:
    v = value.lower()
    return any(marker in v for marker in _PLACEHOLDER_MARKERS)


def test_no_real_secret_values_in_env_example() -> None:
    """``.env.example`` must never contain a real-looking secret value.

    Uncommented SecretStr fields are only permitted to hold obvious
    placeholder strings (``change-me-…``, ``your-…``, etc.). Any other
    uncommented value is treated as a leaked credential and fails the test.
    """
    text = ENV_EXAMPLE.read_text(encoding='utf-8')
    secret_field_names = {name for name, info in DefaultSettings.model_fields.items() if 'SecretStr' in str(info.annotation)}
    bad: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith('#'):
            continue
        if '=' not in stripped:
            continue
        key, _, value = stripped.partition('=')
        key = key.strip()
        value = value.strip().strip('"\'')
        if key in secret_field_names and value and not _is_placeholder(value):
            bad.append(f'  {key}={value!r}')
    assert not bad, (
        '.env.example must not contain real values for secret fields. '
        'Use an obvious placeholder ("change-me-...", "your-...") or '
        'comment the line out:\n' + '\n'.join(bad)
    )
