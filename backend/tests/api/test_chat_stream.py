"""Tests for SSE chat streaming endpoint."""

import json

from starlette.testclient import TestClient


def test_chat_stream_returns_sse_events(client: TestClient, test_user_token: str, mock_rag_service):
    mock_rag_service._normalize_answer_formatting.side_effect = lambda text, _sources=None: text  # noqa: SLF001
    mock_rag_service.stream_query.return_value = iter(
        [
            {'type': 'token', 'token': 'Hello '},
            {'type': 'token', 'token': 'world'},
            {
                'type': 'done',
                'metadata': {'sources': [], 'document_contents': []},
            },
        ]
    )

    response = client.post(
        '/api/chat/stream',
        json={'content': 'Hi'},
        headers={'Authorization': f'Bearer {test_user_token}'},
    )
    assert response.status_code == 200
    assert 'text/event-stream' in response.headers.get('content-type', '')

    body = response.text
    assert 'data: ' in body
    assert '"type": "token"' in body
    assert '"type": "done"' in body

    events = []
    for block in body.split('\n\n'):
        if block.startswith('data: '):
            events.append(json.loads(block[6:]))
    assert any(e.get('type') == 'token' for e in events)
    done = next(e for e in events if e.get('type') == 'done')
    assert 'session_id' in done
