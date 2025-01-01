import random

class Player:
    def __init__(self, name, is_human=False):
        self.name = name
        self.is_human = is_human
        self.hand = []
        self.penalty_points = 0
        self.alive = True

    def choose_card(self):
        if not self.is_human and self.hand:
            return random.choice(self.hand)
        return None
    
    def remove_card_from_hand(self, card):
        if card in self.hand:
            self.hand.remove(card)

class Row:
    def __init__(self):
        self.cards = []
        
    def add_card(self, card):
        self.cards.append(card)
        
    def reset_with_card(self, card):
        old_cards = self.cards[:]
        self.cards = [card]
        return old_cards
        
    @property
    def last_card_value(self):
        if self.cards:
            return self.cards[-1].value
        return None 