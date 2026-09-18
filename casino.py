"""Rules for the Hungarian two-player Cassino game.

States are immutable: playing a move returns a new state.
"""

from dataclasses import dataclass
from itertools import combinations


RANKS = ("A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K")
CARDS = frozenset(rank + suit for suit in "SHDC" for rank in RANKS)


def value(card):
    """Return a card's value, from ace (1) through king (13)."""
    if card not in CARDS:
        raise ValueError(f"Invalid card: {card!r}")
    return RANKS.index(card[:-1]) + 1


@dataclass(frozen=True)
class Move:
    hand: frozenset[str]
    table: frozenset[str]


@dataclass(frozen=True)
class State:
    hands: tuple[tuple[str, ...], tuple[str, ...]]
    table: tuple[str, ...]
    talon: tuple[str, ...]
    piles: tuple[tuple[str, ...], tuple[str, ...]] = ((), ())
    sweeps: tuple[int, int] = (0, 0)
    player: int = 0
    last_capturer: int | None = None
    first: int = 0


def new_deal(deck, first=0):
    """Deal three cards each and four to the table, drawing from the front."""
    deck = tuple(deck)
    if len(deck) != 52 or frozenset(deck) != CARDS:
        raise ValueError("A deal needs all 52 distinct cards")
    if first not in (0, 1):
        raise ValueError("First player must be 0 or 1")
    hands = [(), ()]
    hands[first], hands[1 - first] = deck[:3], deck[3:6]
    return State(tuple(hands), deck[6:10], deck[10:], player=first, first=first)


def deal_over(state):
    """Whether the hands, stock, and table have all been cleared."""
    return not (any(state.hands) or state.talon or state.table)


def legal_moves(state):
    """List single-card placements and captures with equal sums on each side."""
    hand = state.hands[state.player]
    moves = [Move(frozenset((card,)), frozenset()) for card in hand]
    if not hand or not state.table:
        return moves

    # Only retain table subsets whose total could be matched by this hand.
    limit = sum(map(value, hand))
    subsets = {0: [frozenset()]}
    for card in state.table:
        additions = {}
        for total, groups in subsets.items():
            target = total + value(card)
            if target <= limit:
                additions[target] = [group | {card} for group in groups]
        for total, groups in additions.items():
            subsets.setdefault(total, []).extend(groups)

    for size in range(1, len(hand) + 1):
        for cards in combinations(hand, size):
            for captured in subsets.get(sum(map(value, cards)), ()):
                moves.append(Move(frozenset(cards), captured))
    return moves


def play(state, move):
    """Apply a legal move, then handle extra turns, dealing, and final pickup."""
    if not isinstance(move, Move) or not move.hand:
        raise ValueError("A move must play at least one card")
    player = state.player
    if (not move.hand <= set(state.hands[player])
            or not move.table <= set(state.table)
            or (not move.table and len(move.hand) != 1)
            or (move.table and sum(map(value, move.hand)) != sum(map(value, move.table)))):
        raise ValueError("Illegal move")

    hands, piles, sweeps = list(state.hands), list(state.piles), list(state.sweeps)
    played = tuple(card for card in hands[player] if card in move.hand)
    hands[player] = tuple(card for card in hands[player] if card not in move.hand)
    table = tuple(card for card in state.table if card not in move.table)
    last_capturer = state.last_capturer
    if move.table:
        piles[player] += played + tuple(card for card in state.table if card in move.table)
        last_capturer = player
        if not table:
            sweeps[player] += 1
    else:
        table += played

    # Placing onto an empty table is followed by another turn for that player.
    next_player = player if not state.table else 1 - player
    talon = state.talon
    if not any(hands):
        leader = last_capturer if last_capturer is not None else state.first
        if talon:
            hands[leader], hands[1 - leader] = talon[:3], talon[3:6]
            talon = talon[6:]
            next_player = leader
        else:
            # The final pickup is not a sweep. If nobody captured, the dealer's
            # first player receives the otherwise unclaimed cards.
            piles[leader] += table
            table = ()
    elif not hands[next_player]:
        next_player = 1 - next_player

    return State(tuple(hands), table, talon, tuple(piles), tuple(sweeps),
                 next_player, last_capturer, state.first)


def score(state):
    """Return deal points for cards, spades, aces, special cards, and sweeps."""
    points = []
    for player, pile in enumerate(state.piles):
        points.append(
            (3 if len(pile) >= 27 else 0)
            + (2 if sum(card.endswith("S") for card in pile) >= 7 else 0)
            + sum(card.startswith("A") for card in pile)
            + (2 if "10D" in pile else 0)
            + (1 if "2S" in pile else 0)
            + state.sweeps[player]
        )
    return tuple(points)
