# Cassino

The **Hungarian two-player version** of Cassino, with a 52-card French deck —
in the browser, you against the computer.

## Play in your browser

From this project directory, run:

```sh
uv run python app.py
```

This starts the local server and opens **http://127.0.0.1:8000** in your
browser. If the browser does not open automatically, visit that address.
Keep the terminal running while you play; press Ctrl+C to stop the server.

Under **Your move**, choose a move from the dropdown. Its cards are highlighted
on the table and in your hand so you can preview it. Click **Play move** to
confirm. Every listed move is legal: captures match the totals of your cards
and table cards, while placements leave one of your cards on the table.

The computer takes its turns automatically. Scores, captured-card counts,
sweeps, stock size, and move history update as you play. After the final pickup,
the table announces the winner and final score. **New deal** starts again.
The Rules & scoring section explains card values and points.

Enter your name above the table and click **Save name**. Your name and personal
best score from completed deals are saved in this browser and displayed on every
new deal, including after restarting the server. Clearing browser data removes
this record. Changing your name renames the same player profile.

Each browser session has its own deal. Refreshing resumes it while the server
is running; restarting the server clears deals. No extra runtime dependencies
or external card assets are needed.

## Run the tests

```sh
uv run pytest
```

Without `uv`: `python -m pip install pytest`, then `python -m pytest`.

## The interface the tests use

```python
from casino import value, Move, new_deal, legal_moves, play, deal_over, score
```

A card is a string: rank, then suit. Ranks `A 2 3 4 5 6 7 8 9 10 J Q K`,
suits `S H D C`. So `"10D"`, `"AS"`, `"QH"`.

| Name | What it is |
|---|---|
| `value(card)` | The card's value. |
| `Move(hand, table)` | Two `frozenset`s of cards: what the player plays from hand, and what they take from the table. Placing a card without taking anything is `Move(frozenset({"7H"}), frozenset())`. |
| `new_deal(deck, first=0)` | Deals from `deck`, a sequence of the 52 cards in order: the first three go to player `first`, the next three to the other player, the next four face up on the table. The rest is the stock, drawn from the front. |
| `legal_moves(state)` | Every legal `Move` for the player to move. |
| `play(state, move)` | The state after the move — including everything the rules make happen before the next move. Raises `ValueError` if the move is not legal. |
| `deal_over(state)` | `True` once every card has been taken. |
| `score(state)` | A pair: the points each player earned in the finished deal. |

The tests read these fields of a state:

| Field | What it is |
|---|---|
| `hands` | A pair of tuples: each player's cards. |
| `table` | A tuple: the cards face up on the table. |
| `talon` | A tuple: the stock, next card first. |
| `piles` | A pair of tuples: the cards each player has taken. |
| `sweeps` | A pair: the points each player has earned from sweeps so far. |
| `player` | Whose turn it is, `0` or `1`. |
