"""Automated HTTP integration checks; these are not human play-testing."""
from http.cookiejar import CookieJar
from http.server import HTTPServer
import json
import threading
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

import pytest

from app import Handler


@pytest.fixture
def client():
    server = HTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    opener = build_opener(HTTPCookieProcessor(CookieJar()))

    def request(path, data=None):
        req = Request(f'http://127.0.0.1:{server.server_port}{path}',
                      data=None if data is None else json.dumps(data).encode(),
                      headers={'Content-Type': 'application/json'})
        with opener.open(req) as response:
            body = response.read()
            return body.decode() if path == '/' else json.loads(body)

    yield request
    server.shutdown()
    server.server_close()
    thread.join()


def test_browser_api_complete_deal(client):
    assert 'Available legal actions' in client('/')
    state = client('/api/state')
    assert 'opponent_count' in state and 'hands' not in state
    for _ in range(100):
        if state['over']:
            break
        if state['player'] == 0:
            move = max(state['moves'], key=lambda m: len(m['table']))
            state = client('/api/play', dict(move, revision=state['revision']))
        else:
            assert state['moves'] == []
            state = client('/api/computer', {'revision': state['revision']})
    assert state['over']
    assert sum(state['captured']) == 52
    assert not state['hand'] and not state['table'] and not state['stock']
    assert state['moves'] == []
    assert client('/api/state') == state
    restarted = client('/api/new', {'revision': state['revision']})
    assert not restarted['over'] and restarted['captured'] == [0, 0]


def test_api_rejects_invalid_and_stale_moves(client):
    state = client('/api/state')
    for path, body in [('/api/play', {'hand': ['invalid'], 'table': []}),
                       ('/api/computer', {}),
                       ('/api/play', dict(state['moves'][0], revision=-1))]:
        with pytest.raises(HTTPError) as error:
            client(path, {'revision': state['revision'], **body})
        assert error.value.code == 400
        assert client('/api/state') == state
