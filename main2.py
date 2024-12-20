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

# Cards constants
CARD_WIDTH = 70
CARD_HEIGHT = 100

# Weighted penalty distribution: More 1's than 6's
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

    def draw(self, surface, x, y, highlight=False, face_up=True):
        self.rect.topleft = (x,y)
        color = YELLOW if highlight else WHITE
        if not face_up:
            # Face-down card: blue back
            color = BLUE
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, BLACK, self.rect, 2, border_radius=5)

        if face_up:
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

class CardAnimation:
    def __init__(self, player, card, start_pos, end_pos, take_row, row_obj, speed=0.05):
        self.player = player
        self.card = card
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.take_row = take_row
        self.row_obj = row_obj
        self.progress = 0.0
        self.speed = speed

    def update(self):
        self.progress += self.speed
        if self.progress > 1.0:
            self.progress = 1.0
        return self.progress >= 1.0

    def draw(self, surface):
        sx, sy = self.start_pos
        ex, ey = self.end_pos
        x = sx + (ex - sx)*self.progress
        y = sy + (ey - sy)*self.progress
        self.card.draw(surface, x, y, face_up=True)

class Game:
    def __init__(self):
        self.players = []
        self.rows = [Row() for _ in range(4)]
        self.deck = []
        self.discard = []
        self.state = "menu" # menu -> setup -> round -> reveal -> animate -> pick_row -> leaderboard
        self.selected_card = None
        self.selected_player = None
        self.selected_row = None
        self.leaderboard = []
        self.player_cards_placed = {}
        self.num_bots = 0

        # For reveal and animation steps
        self.reveal_timer = 0
        self.reveal_delay = 60  # frames before flipping face-up
        self.animation_cards = []
        self.pending_placements = []

    def generate_deck(self):
        self.deck = []
        for v in range(1,111):
            penalty = random.choice(penalty_distribution)
            self.deck.append(Card(v, penalty))

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def setup_players(self):
        # First player is human
        self.players = [Player("Player 1", is_human=True)]
        for i in range(self.num_bots):
            self.players.append(Player(f"Bot {i+1}"))
        self.active_players = len(self.players)

    def start_new_play(self):
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

    def handle_card_placement_prep(self):
        self.state = "reveal"
        self.reveal_timer = 0

    def handle_card_placement_final(self):
        placements = sorted(self.player_cards_placed.items(), key=lambda x: x[1].value)
        self.animation_cards = []
        self.pending_placements = []
        for player, card in placements:
            placed_row = self.can_place_card_in_rows(card)
            if not placed_row:
                # Player must pick a row - if human, wait, if bot pick random row
                if player.is_human:
                    self.state = "pick_row"
                    self.selected_card = card
                    self.selected_player = player
                    return
                else:
                    chosen_row = random.choice(self.rows)
                    self.pending_placements.append((player, card, chosen_row, True))
            else:
                self.pending_placements.append((player, card, placed_row, False))

        self.start_animation()

    def can_place_card_in_rows(self, card):
        possible_rows = []
        for r in self.rows:
            if r.last_card_value is None:
                continue
            if card.value > r.last_card_value:
                possible_rows.append(r)
        if possible_rows:
            # Find minimal difference
            diffs = [(r, card.value - r.last_card_value) for r in possible_rows]
            diffs.sort(key=lambda x:x[1])
            chosen_row = diffs[0][0]
            return chosen_row
        return None

    def start_animation(self):
        self.animation_cards = []
        cx = WIDTH//2
        cy = HEIGHT//2

        placements = self.pending_placements
        reveal_count = len(placements)
        reveal_start_x = cx - (reveal_count*(CARD_WIDTH+10))//2

        for i, (player, card, row_obj, take_row) in enumerate(placements):
            # Compute final position
            row_index = self.rows.index(row_obj)
            row_x = WIDTH//2 - 2*(CARD_WIDTH+20) + row_index*(CARD_WIDTH+100) + 20
            if take_row:
                # If taking the row, just place at the top position of the row
                final_y = HEIGHT//2 - 2*(CARD_HEIGHT+10) + 10
            else:
                final_y = HEIGHT//2 - 2*(CARD_HEIGHT+10) + 10 + len(row_obj.cards)*(CARD_HEIGHT//2)

            start_x = reveal_start_x + i*(CARD_WIDTH+10)
            start_y = cy - CARD_HEIGHT//2

            anim = CardAnimation(player, card, (start_x, start_y), (row_x, final_y), take_row, row_obj, speed=0.05)
            self.animation_cards.append(anim)

        self.state = "animate"

    def animate_step(self):
        done = True
        for anim in self.animation_cards:
            if not anim.update():
                done = False
        if done:
            # Finish placements
            self.finish_placements()
            self.end_round()

    def finish_placements(self):
        for anim in self.animation_cards:
            player = anim.player
            card = anim.card
            take_row = anim.take_row
            row_obj = anim.row_obj
            if take_row:
                penalty_cards = row_obj.reset_with_card(card)
                player.remove_card_from_hand(card)
                for c in penalty_cards:
                    player.penalty_points += c.penalty
            else:
                row_obj.add_card(card)
                player.remove_card_from_hand(card)

        self.animation_cards = []
        self.pending_placements = []

    def pick_row_for_player(self, row):
        penalty_cards = row.reset_with_card(self.selected_card)
        self.selected_player.remove_card_from_hand(self.selected_card)
        for c in penalty_cards:
            self.selected_player.penalty_points += c.penalty
        self.selected_card = None
        self.selected_player = None
        self.end_round()

    def end_round(self):
        # First, eliminate players over 60 points
        for p in self.players:
            if p.alive and p.penalty_points > 60:
                p.alive = False
                self.leaderboard.append((p.name, p.penalty_points))

        # Check how many are still alive after elimination
        alive_count = sum(p.alive for p in self.players)
        if alive_count == 1:
            # Only one player remains, game ends
            self.state = "leaderboard"
            return

        # Check if all alive players have no cards left
        still_have_cards = any(len(p.hand) > 0 and p.is_human for p in self.get_alive_players())
        if not still_have_cards:
            # All players are out of cards, start a new play
            self.start_new_play()
        else:
            # Continue the round (players still have cards)
            self.player_cards_placed = {}
            self.state = "round"

    def update(self, events):
        if self.state == "round":
            # Bots choose if they haven't
            alive_players = self.get_alive_players()
            for p in alive_players:
                if p not in self.player_cards_placed:
                    if not p.is_human:
                        chosen = p.choose_card()
                        if chosen:
                            self.player_cards_placed[p] = chosen
            if self.all_players_placed():
                self.handle_card_placement_prep()

        elif self.state == "reveal":
            self.reveal_timer += 1
            if self.reveal_timer > self.reveal_delay:
                # Flip cards face-up and move to final placement
                self.handle_card_placement_final()

        elif self.state == "pick_row":
            pass
        elif self.state == "setup":
            # Once setup is done, start the play
            self.generate_deck()
            self.shuffle_deck()
            self.setup_players()
            self.start_new_play()
        elif self.state == "animate":
            self.animate_step()

    def draw_reveal_cards(self):
        # Draw chosen cards in a central play zone
        cx = WIDTH//2
        cy = HEIGHT//2
        chosen = list(self.player_cards_placed.items())
        chosen.sort(key=lambda x: x[1].value)
        count = len(chosen)
        start_x = cx - (count*(CARD_WIDTH+10))//2
        for i,(p,c) in enumerate(chosen):
            face_up = p.is_human or self.reveal_timer > self.reveal_delay
            c.draw(SCREEN, start_x+i*(CARD_WIDTH+10), cy - CARD_HEIGHT//2, face_up=face_up)

    def draw_rows(self):
        row_y = HEIGHT//2 - 2*(CARD_HEIGHT+10)
        for i, row in enumerate(self.rows):
            row_x = WIDTH//2 - 2*(CARD_WIDTH+20) + i*(CARD_WIDTH+100)
            pygame.draw.rect(SCREEN, GRAY, (row_x, row_y, CARD_WIDTH+40, CARD_HEIGHT+150), border_radius=5)
            cy = row_y+10
            for card in row.cards:
                card.draw(SCREEN, row_x+20, cy)
                cy += CARD_HEIGHT//2
            # Highlight if pick_row state
            if self.state == "pick_row" and self.selected_player and self.selected_player.is_human:
                mx,my = pygame.mouse.get_pos()
                rect = pygame.Rect(row_x, row_y, CARD_WIDTH+40, CARD_HEIGHT+150)
                if rect.collidepoint(mx,my):
                    pygame.draw.rect(SCREEN, YELLOW, rect, 4, border_radius=5)

    def draw_player_info(self):
        info_y = 10
        for p in self.players:
            color = BLACK
            if not p.alive:
                color = RED
            txt = FONT.render(f"{p.name}: {p.penalty_points} pts {'(OUT)' if not p.alive else ''}", True, color)
            SCREEN.blit(txt, (10, info_y))
            info_y += 30

    def draw_hand(self):
        human = self.players[0]
        x_start = 50
        y_start = HEIGHT - CARD_HEIGHT - 50
        if self.state == "round" and human.alive and human not in self.player_cards_placed:
            for i, c in enumerate(human.hand):
                mx, my = pygame.mouse.get_pos()
                highlight = pygame.Rect(x_start+i*(CARD_WIDTH+5), y_start, CARD_WIDTH, CARD_HEIGHT).collidepoint(mx,my)
                c.draw(SCREEN, x_start+i*(CARD_WIDTH+5), y_start, highlight=highlight, face_up=True)
        else:
            # Just show the hand without highlight if not selecting
            for i, c in enumerate(human.hand):
                c.draw(SCREEN, x_start+i*(CARD_WIDTH+5), y_start, face_up=True)

    def draw_animation(self):
        # Draw rows, player info, etc. also draw the cards that are not animating
        self.draw_rows()
        self.draw_player_info()
        self.draw_hand()

        # Draw cards currently animating
        for anim in self.animation_cards:
            anim.draw(SCREEN)

    def draw(self):
        SCREEN.fill(GREEN)
        if self.state == "menu":
            title = BIG_FONT.render("Select number of bots (1-9):", True, WHITE)
            SCREEN.blit(title, (WIDTH//2 - title.get_width()//2, HEIGHT//2 - 50))
            info = FONT.render("Press a key from 1 to 9 to select how many bots", True, WHITE)
            SCREEN.blit(info, (WIDTH//2 - info.get_width()//2, HEIGHT//2 + 10))

        elif self.state in ["round", "pick_row"]:
            self.draw_hand()
            self.draw_rows()
            self.draw_player_info()
            if self.state == "pick_row":
                msg = "Select a row to take."
                txt = BIG_FONT.render(msg, True, BLACK)
                SCREEN.blit(txt, (WIDTH//2 - txt.get_width()//2, 50))

        elif self.state == "reveal":
            self.draw_rows()
            self.draw_player_info()
            self.draw_hand()
            self.draw_reveal_cards()

        elif self.state == "animate":
            self.draw_animation()

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
                    if game.state == "round":
                        # Human picks a card
                        human = game.players[0]
                        if human.alive and human not in game.player_cards_placed:
                            mx, my = event.pos
                            x_start = 50
                            y_start = HEIGHT - CARD_HEIGHT - 50
                            for i, c in enumerate(human.hand):
                                rect = pygame.Rect(x_start+i*(CARD_WIDTH+5), y_start, CARD_WIDTH, CARD_HEIGHT)
                                if rect.collidepoint(mx,my):
                                    game.player_cards_placed[human] = c
                                    if game.all_players_placed():
                                        game.handle_card_placement_prep()
                                    break
                    elif game.state == "pick_row":
                        mx,my = event.pos
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
                if game.state == "menu":
                    # If user pressed a digit from 1 to 9, set number of bots
                    if event.unicode.isdigit():
                        num = int(event.unicode)
                        if 1 <= num <= 9:
                            game.num_bots = num
                            game.state = "setup"

        game.update(events)
        game.draw()

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
