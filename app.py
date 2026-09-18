"""Local browser table. Run with: uv run python app.py"""
import argparse
from dataclasses import dataclass, field
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
from pathlib import Path
import random
import secrets
import threading
import webbrowser

from casino import CARDS, Move, deal_over, legal_moves, new_deal, play, score, value


@dataclass
class Game:
    state: object = field(default_factory=lambda: new_deal(random.sample(sorted(CARDS), 52)))
    revision: int = 0
    history: list = field(default_factory=lambda: ["New deal. You lead."])

    def advance(self, move):
        actor = "You" if self.state.player == 0 else "Computer"
        previous = self.state
        self.state = play(previous, move)
        message = f"{actor} played {', '.join(sorted(move.hand))}"
        message += f" and captured {', '.join(sorted(move.table))}." if move.table else "."
        if self.state.sweeps != previous.sweeps:
            message += " Sweep!"
        if len(self.state.talon) < len(previous.talon):
            message += " New hands dealt; last capturer leads."
        if deal_over(self.state):
            message += " Deal over. Remaining table cards awarded to the last capturer."
        self.history.append(message)
        self.revision += 1

    def payload(self):
        s = self.state
        over = deal_over(s)
        return dict(hand=s.hands[0], opponent_count=len(s.hands[1]), table=s.table,
                    stock=len(s.talon), captured=[len(p) for p in s.piles],
                    spades=[sum(c.endswith('S') for c in p) for p in s.piles],
                    sweeps=s.sweeps, scores=score(s), player=s.player, over=over,
                    revision=self.revision, history=self.history,
                    moves=[dict(hand=sorted(m.hand), table=sorted(m.table))
                           for m in legal_moves(s)] if s.player == 0 and not over else [])


def computer_move(state):
    """Prefer sweeps and valuable captures; otherwise place a low card."""
    def priority(move):
        cards = move.hand | move.table
        return (bool(move.table), bool(move.table) and len(move.table) == len(state.table),
                sum(2 if c == '10D' else 1 if c == '2S' or c.startswith('A') else 0 for c in cards),
                len(move.table), -len(move.hand), -sum(map(value, move.hand)))
    return max(legal_moves(state), key=priority)


class Handler(BaseHTTPRequestHandler):
    games = {}

    def respond(self, status, data, content_type='application/json', cookie=None):
        body = json.dumps(data).encode() if content_type == 'application/json' else data
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        if cookie:
            self.send_header('Set-Cookie', f'casino={cookie}; HttpOnly; SameSite=Strict; Path=/')
        self.end_headers()
        self.wfile.write(body)

    def session(self):
        cookie = SimpleCookie(self.headers.get('Cookie', ''))
        token = cookie['casino'].value if 'casino' in cookie else None
        if token not in self.games:
            token = secrets.token_hex(24)
            self.games[token] = Game()
        return token, self.games[token]

    def do_GET(self):
        if self.path == '/':
            self.respond(200, (Path(__file__).parent / 'static/index.html').read_bytes(), 'text/html; charset=utf-8')
        elif self.path == '/api/state':
            token, game = self.session()
            self.respond(200, game.payload(), cookie=token)
        else:
            self.respond(404, {'error': 'Not found'})

    def do_POST(self):
        if self.path not in ('/api/new', '/api/play', '/api/computer'):
            self.respond(404, {'error': 'Not found'})
            return
        token, game = self.session()
        try:
            size = int(self.headers.get('Content-Length', 0))
            if not 0 < size <= 8192:
                raise ValueError('Invalid request size')
            data = json.loads(self.rfile.read(size))
            if not isinstance(data, dict):
                raise ValueError('Invalid request')
            if data.get('revision') != game.revision:
                raise ValueError('The table changed. Reload to see the latest turn.')
            if self.path == '/api/new':
                fresh = Game()
                fresh.revision = game.revision + 1
                self.games[token] = game = fresh
            else:
                if deal_over(game.state):
                    raise ValueError('This deal is over')
                if self.path == '/api/computer':
                    if game.state.player != 1:
                        raise ValueError('It is your turn')
                    move = computer_move(game.state)
                else:
                    if game.state.player != 0:
                        raise ValueError('It is the computer’s turn')
                    hand, table = data.get('hand'), data.get('table')
                    if not all(isinstance(cards, list) and all(isinstance(c, str) for c in cards)
                               for cards in (hand, table)):
                        raise ValueError('Select cards for your move')
                    move = Move(frozenset(hand), frozenset(table))
                game.advance(move)
            self.respond(200, game.payload(), cookie=token)
        except (ValueError, TypeError) as exc:
            self.respond(400, {'error': str(exc)}, cookie=token)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8000)
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    server = HTTPServer(('127.0.0.1', args.port), Handler)
    url = f'http://127.0.0.1:{server.server_port}'
    print(f'Casino table: {url}\nPress Ctrl+C to stop.', flush=True)
    if not args.no_browser:
        threading.Timer(0.3, webbrowser.open, args=(url,)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
