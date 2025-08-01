import random
from enum import Enum

class Color(Enum):
    RED = "🔴"
    YELLOW = "🟡"
    GREEN = "🟢"
    BLUE = "🔵"
    WILD = "🃏"

class Card:
    def __init__(self, color, value):
        self.color = color
        self.value = value
        self.chosen_color = None
    def is_playable_on(self, top):
        top_color = top.chosen_color or top.color
        return self.color == Color.WILD or self.color == top_color or self.value == top.value
    def __str__(self):
        s = f"{self.color.value}{self.value}"
        if self.color == Color.WILD and self.chosen_color:
            s += f" →{self.chosen_color.value}"
        return s

def create_deck():
    colors = [Color.RED, Color.YELLOW, Color.GREEN, Color.BLUE]
    values = [str(i) for i in range(10)] + ["R", "S", "+2"]*2
    deck = [Card(c,v) for c in colors for v in values for _ in (range(1) if v=="0" else range(2))]
    deck += [Card(Color.WILD, "WILD")] * 4 + [Card(Color.WILD, "+4")] * 4
    random.shuffle(deck)
    return deck

class UnoGame:
    def __init__(self, players):
        self.players = players
        self.hands = {p: [] for p in players}
        self.deck = create_deck()
        self.discard = []
        self.current = 0
        self.direction = 1
        self.pending_draw = 0
        self.wait_color = False

    def deal(self):
        for _ in range(7):
            for p in self.players:
                self.hands[p].append(self.deck.pop())
        self.discard.append(self._draw_non_wild())

    def _draw_non_wild(self):
        c = self.deck.pop()
        if c.color == Color.WILD:
            self.deck.insert(0, c)
            return self._draw_non_wild()
        return c

    def current_player(self): return self.players[self.current]

    def play_card(self, pid, idx, chosen_color=None):
        if pid != self.current_player():
            return False, "Не твій хід"
        card = self.hands[pid][idx]
        top = self.discard[-1]
        if not card.is_playable_on(top):
            return False, "Неприпустима карта"
        self.hands[pid].pop(idx)
        if card.color == Color.WILD:
            card.chosen_color = chosen_color
        self.discard.append(card)

        v = card.value
        if v == "R": self.direction *= -1
        elif v == "S": self._advance()
        elif v == "+2": self.pending_draw += 2
        elif v == "+4":
            self.pending_draw += 4
            self.wait_color = True

        if not self.wait_color:
            self._advance()
        return True, card

    def draw_cards(self):
        count = self.pending_draw or 1
        for _ in range(count):
            if not self.deck: self._reshuffle()
            self.hands[self.current_player()].append(self.deck.pop())
        self.pending_draw = 0
        self._advance()

    def _reshuffle(self):
        top = self.discard.pop()
        random.shuffle(self.discard)
        self.deck = self.discard
        self.discard = [top]

    def set_color(self, color):
        self.discard[-1].chosen_color = color
        self.wait_color = False
        self._advance()

    def has_uno(self, pid): return len(self.hands[pid]) == 1

    def has_winner(self):
        for p, h in self.hands.items():
            if not h:
                return p
        return None
  
