import pygame
import sys
import random
from pygame.locals import *

pygame.init()

# Window dimensions
WIDTH, HEIGHT = 1200, 800
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Card Placement Game")

# Fonts
FONT = pygame.font.SysFont(None, 32)
BIG_FONT = pygame.font.SysFont(None, 64)

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GREEN = (0, 200, 0)
RED = (200, 0, 0)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)
BLUE = (0, 0, 200)

# Number of players, 1 human + rest bots
NUM_PLAYERS = 4

# Cards constants
CARD_WIDTH = 70
CARD_HEIGHT = 100

# Generate deck: cards from 1 to 110 with penalty points from 1 to 6, weighted
# Weighted distribution: let's assume a linear distribution such that:
# Probability(1) > Probability(2) > ... > Probability(6)
# For instance: weights = [6,5,4,3,2,1] meaning '1' is most common.
weights = [6,5,4,3,2,1]
values = range(1, 7)
penalty_distribution = []
for v, w in zip(values, weights):
    penalty_distribution.extend([v]*w)

class Card:
    def __init__(self, value, penalty):
        self.value = value
        self.penalty = penalty
        self.rect = pygame.Rect(0,0,CARD_WIDTH,CARD_HEIGHT)
    def draw(self, surface, x, y, highlight=False):
        self.rect.topleft = (x,y)
        color = YELLOW if highlight else WHITE
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        val_text = FONT.render(str(self.value), True, BLACK)
        penalty_text = FONT.render(str(self.penalty), True, RED)
        surface.blit(val_text, (x+CARD_WIDTH//2 - val_text.get_width()//2, y+10))
        surface.blit(penalty_text, (x+CARD_WIDTH//2 - penalty_text.get_width()//2, y+CARD_HEIGHT-30))

class Player:
    def __init__(self, name, is_human=False):
        self.name = name
        self.is_human = is_human
        self.hand = []
        self.penalty_points = 0
        self.alive = True

    def choose_card(self):
        # For bot: choose a random card
        # For human: This will be handled by GUI events before calling place cards.
        if not self.is_human:
            if self.hand:
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

class Game:
    def __init__(self):
        self.players = [Player(f"Player {i+1}", is_human=(i==0)) for i in range(NUM_PLAYERS)]
        self.rows = [Row() for _ in range(4)]
        self.deck = []
        self.discard = []
        self.state = "setup" # setup -> play -> round -> pick_row -> leaderboard
        self.selected_card = None
        self.selected_player = None
        self.selected_row = None
        self.leaderboard = []
        self.active_players = NUM_PLAYERS
        self.player_cards_placed = {}
        self.current_player_index = 0
        self.round_complete = False
        self.setup_game()

    def setup_game(self):
        self.generate_deck()
        self.shuffle_deck()
        self.start_new_play()

    def generate_deck(self):
        self.deck = []
        for v in range(1,111):
            # Weighted penalty
            penalty = random.choice(penalty_distribution)
            self.deck.append(Card(v, penalty))

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def start_new_play(self):
        # Deal 10 cards to each player
        # Place 4 cards in rows
        if len(self.deck) < (10*len(self.get_alive_players())+4):
            # If deck is too small, regenerate and shuffle
            self.generate_deck()
            self.shuffle_deck()
        for p in self.players:
            if p.alive:
                p.hand = [self.deck.pop() for _ in range(10)]
        self.rows = [Row() for _ in range(4)]
        for row in self.rows:
            row.add_card(self.deck.pop())
        self.state = "round"
        self.player_cards_placed = {}

    def get_alive_players(self):
        return [p for p in self.players if p.alive]

    def all_players_placed(self):
        alive = self.get_alive_players()
        return len(self.player_cards_placed) == len(alive)

    def handle_card_placement(self):
        # Once all players have chosen a card, we order them by card value and place them
        placements = sorted(self.player_cards_placed.items(), key=lambda x: x[1].value)
        for player, card in placements:
            placed = self.place_card_in_rows(player, card)
            if not placed:
                # Player must pick a row. If player is human, we must wait for row selection.
                # For now, choose a row randomly if bot.
                if player.is_human:
                    # Wait for user input, highlight all rows for selection
                    self.state = "pick_row"
                    self.selected_card = card
                    self.selected_player = player
                    return
                else:
                    chosen_row = random.choice(self.rows)
                    penalty_cards = chosen_row.reset_with_card(card)
                    # Add penalty points
                    for c in penalty_cards:
                        player.penalty_points += c.penalty
        # If we reached here without needing human input, round ends
        self.end_round()

    def place_card_in_rows(self, player, card):
        # Try to place card according to rules:
        # 1. Card must be greater than last card in row
        # 2. If multiple possible rows, choose the one with minimal difference
        possible_rows = []
        for r in self.rows:
            if card.value > r.last_card_value:
                possible_rows.append(r)
        if possible_rows:
            # Find minimal difference
            diffs = [(r, card.value - r.last_card_value) for r in possible_rows]
            diffs.sort(key=lambda x:x[1])
            chosen_row = diffs[0][0]
            chosen_row.add_card(card)
            # Remove card from player hand
            player.remove_card_from_hand(card)
            return True
        return False

    def pick_row_for_player(self, row):
        # Human player picks a row when no placement possible
        penalty_cards = row.reset_with_card(self.selected_card)
        self.selected_player.remove_card_from_hand(self.selected_card)
        for c in penalty_cards:
            self.selected_player.penalty_points += c.penalty
        # Reset pick state
        self.selected_card = None
        self.selected_player = None
        self.state = "round_end_pending"
        self.end_round()

    def end_round(self):
        # Check if all players have cards
        still_have_cards = any([len(p.hand)>0 and p.alive for p in self.players])
        # Eliminate players over 60 points
        for p in self.players:
            if p.alive and p.penalty_points > 60:
                p.alive = False
                self.leaderboard.append((p.name, p.penalty_points))
        alive_count = sum([p.alive for p in self.players])
        if alive_count == 1:
            # Game ends
            self.leaderboard.sort(key=lambda x:x[1])
            self.state = "leaderboard"
            return
        if not still_have_cards:
            # start new play
            self.start_new_play()
        else:
            # new round
            self.player_cards_placed = {}
            self.state = "round"

    def update(self, events):
        # Game state machine
        if self.state == "round":
            # If all players are bots except human, we must wait for human to pick card via GUI
            # Bots choose card immediately
            alive_players = self.get_alive_players()
            for p in alive_players:
                if p not in self.player_cards_placed:
                    if not p.is_human:
                        chosen = p.choose_card()
                        if chosen:
                            self.player_cards_placed[p] = chosen
            if self.all_players_placed():
                self.handle_card_placement()

        elif self.state == "pick_row":
            # We are waiting for human to pick a row with a click
            # This is handled in event section
            pass

    def draw(self):
        SCREEN.fill(GREEN)
        if self.state in ["round", "pick_row", "round_end_pending"]:
            # Draw players' hands
            # Draw human player's hand at bottom
            human = self.players[0]
            x_start = 50
            y_start = HEIGHT - CARD_HEIGHT - 50
            for i, c in enumerate(human.hand):
                highlight = False
                # If it's the round state and human hasn't chosen a card yet, highlight on hover
                if self.state == "round" and self.players[0] not in self.player_cards_placed:
                    mx, my = pygame.mouse.get_pos()
                    if pygame.Rect(x_start+i*(CARD_WIDTH+5), y_start, CARD_WIDTH, CARD_HEIGHT).collidepoint(mx,my):
                        highlight = True
                c.draw(SCREEN, x_start+i*(CARD_WIDTH+5), y_start, highlight=highlight)

            # Draw rows in the center
            row_y = HEIGHT//2 - 2*(CARD_HEIGHT+10)
            for i, row in enumerate(self.rows):
                row_x = WIDTH//2 - 2*(CARD_WIDTH+20) + i*(CARD_WIDTH+100)
                # Draw row background
                pygame.draw.rect(SCREEN, GRAY, (row_x, row_y, CARD_WIDTH+40, CARD_HEIGHT+150), border_radius=5)
                # Draw row cards stacked
                cy = row_y+10
                for card in row.cards:
                    card.draw(SCREEN, row_x+20, cy)
                    cy += CARD_HEIGHT//2
                # If state is pick_row, highlight row if hovered
                if self.state == "pick_row" and self.selected_player.is_human:
                    mx,my = pygame.mouse.get_pos()
                    rect = pygame.Rect(row_x, row_y, CARD_WIDTH+40, CARD_HEIGHT+150)
                    if rect.collidepoint(mx,my):
                        pygame.draw.rect(SCREEN, YELLOW, rect, 4, border_radius=5)

            # Draw info about players
            info_y = 10
            for p in self.players:
                color = BLACK
                if not p.alive:
                    color = RED
                txt = FONT.render(f"{p.name}: {p.penalty_points} pts {'(OUT)' if not p.alive else ''}", True, color)
                SCREEN.blit(txt, (10, info_y))
                info_y += 30

            # If waiting for pick_row and human player, give instructions
            if self.state == "pick_row":
                msg = "Select a row to take."
                txt = BIG_FONT.render(msg, True, BLACK)
                SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, 50))

        elif self.state == "leaderboard":
            SCREEN.fill(BLUE)
            leaderboard_text = BIG_FONT.render("Leaderboard", True, WHITE)
            SCREEN.blit(leaderboard_text, (WIDTH//2 - leaderboard_text.get_width()//2, 50))
            sorted_leaderboard = sorted(self.leaderboard, key=lambda x: x[1])
            start_y = 200
            for i,(name,points) in enumerate(sorted_leaderboard):
                line = f"{i+1}. {name}: {points} pts"
                line_surf = FONT.render(line, True, WHITE)
                SCREEN.blit(line_surf, (WIDTH//2 - line_surf.get_width()//2, start_y))
                start_y += 40

def main():
    clock = pygame.time.Clock()
    game = Game()

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == QUIT:
                running = False
            elif event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    # Handle click
                    mx,my = event.pos
                    if game.state == "round":
                        # If human hasn't chosen a card yet, allow pick
                        human = game.players[0]
                        if human.alive and human not in game.player_cards_placed:
                            # Check card click
                            x_start = 50
                            y_start = HEIGHT - CARD_HEIGHT - 50
                            for i, c in enumerate(human.hand):
                                rect = pygame.Rect(x_start+i*(CARD_WIDTH+5), y_start, CARD_WIDTH, CARD_HEIGHT)
                                if rect.collidepoint(mx,my):
                                    # Player chooses this card
                                    game.player_cards_placed[human] = c
                                    # Check if all placed
                                    if game.all_players_placed():
                                        game.handle_card_placement()
                                    break
                    elif game.state == "pick_row":
                        # Human must pick a row
                        row_y = HEIGHT//2 - 2*(CARD_HEIGHT+10)
                        for i, row in enumerate(game.rows):
                            row_x = WIDTH//2 - 2*(CARD_WIDTH+20) + i*(CARD_WIDTH+100)
                            rect = pygame.Rect(row_x, row_y, CARD_WIDTH+40, CARD_HEIGHT+150)
                            if rect.collidepoint(mx,my):
                                game.pick_row_for_player(row)
                                break
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False

        game.update(events)
        game.draw()

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
