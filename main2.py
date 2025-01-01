import pygame
import sys
import random
from pygame.locals import *
from config import GameConfig
from card import Card
from player import Player, Row
from animation_manager import AnimationManager

pygame.init()

SCREEN = pygame.display.set_mode((GameConfig.WIDTH, GameConfig.HEIGHT))
pygame.display.set_caption("Samurai Frog Card Placement Game")

# Load images
background_img = pygame.image.load("background.png").convert()
card_back_img = pygame.image.load("card_back_img.png").convert_alpha()
frog_images = {}
for i in range(1, 7):
    frog_images[i] = pygame.image.load(f"frog_{i}.png").convert_alpha()

class Game:
    def __init__(self):
        self.players = []
        self.rows = [Row() for _ in range(GameConfig.NUM_ROWS)]
        self.deck = []
        self.discard = []
        self.state = "menu"
        self.selected_card = None
        self.selected_player = None
        self.selected_row = None
        self.leaderboard = []
        self.player_cards_placed = {}
        self.num_bots = 0
        self.reveal_timer = 0
        self.animation_manager = AnimationManager(self)
        
    def generate_deck(self):
        self.deck = []
        penalty_distribution = GameConfig.get_penalty_distribution()
        for v in range(1, 111):
            penalty = random.choice(penalty_distribution)
            self.deck.append(Card(v, penalty))

    def shuffle_deck(self):
        random.shuffle(self.deck)

    def setup_players(self):
        self.players = [Player("Player 1", is_human=True)]
        for i in range(self.num_bots):
            self.players.append(Player(f"Bot {i+1}"))
        self.active_players = len(self.players)

    def start_new_play(self):
        cards_needed = GameConfig.CARDS_PER_PLAYER * len(self.get_alive_players()) + GameConfig.NUM_ROWS
        if len(self.deck) < cards_needed:
            self.generate_deck()
            self.shuffle_deck()
        for p in self.players:
            if p.alive:
                p.hand = [self.deck.pop() for _ in range(GameConfig.CARDS_PER_PLAYER)]
        self.rows = [Row() for _ in range(GameConfig.NUM_ROWS)]
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
        for player, card in placements:
            placed_row = self.can_place_card_in_rows(card)
            if not placed_row:
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
            diffs = [(r, card.value - r.last_card_value) for r in possible_rows]
            diffs.sort(key=lambda x: x[1])
            return diffs[0][0]
        return None

    def start_animation(self):
        self.animation_manager.create_card_animations(self.pending_placements)
        self.state = "animate"

    def animate_step(self):
        if self.animation_manager.update():
            self.animation_cards, self.pending_placements = self.animation_manager.get_results()
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
        for p in self.players:
            if p.alive and p.penalty_points > GameConfig.MAX_PENALTY_POINTS:
                p.alive = False
                self.leaderboard.append((p.name, p.penalty_points))

        alive_count = sum(p.alive for p in self.players)
        if alive_count == 1:
            self.state = "leaderboard"
            return

        still_have_cards = any(len(p.hand) > 0 and p.is_human for p in self.get_alive_players())
        if not still_have_cards:
            self.start_new_play()
        else:
            self.player_cards_placed = {}
            self.state = "round"

    def draw_reveal_cards(self):
        cx = GameConfig.WIDTH//2
        cy = GameConfig.HEIGHT//2
        chosen = list(self.player_cards_placed.items())
        chosen.sort(key=lambda x: x[1].value)
        count = len(chosen)
        start_x = cx - (count*(GameConfig.CARD_WIDTH+10))//2
        for i, (p, c) in enumerate(chosen):
            face_up = p.is_human or self.reveal_timer > GameConfig.REVEAL_DELAY
            c.draw(SCREEN, start_x+i*(GameConfig.CARD_WIDTH+10), cy - GameConfig.CARD_HEIGHT//2, face_up=face_up)

    def draw_rows(self):
        row_y = GameConfig.HEIGHT//2 - 2*(GameConfig.CARD_HEIGHT+10)
        for i, row in enumerate(self.rows):
            row_x = GameConfig.WIDTH//2 - 2*(GameConfig.CARD_WIDTH+20) + i*(GameConfig.CARD_WIDTH+100)
            pygame.draw.rect(SCREEN, GameConfig.GRAY, 
                           (row_x, row_y, GameConfig.CARD_WIDTH+40, GameConfig.CARD_HEIGHT+150), 
                           border_radius=5)
            cy = row_y+10
            for card in row.cards:
                card.draw(SCREEN, row_x+20, cy)
                cy += GameConfig.CARD_HEIGHT//2
            if self.state == "pick_row" and self.selected_player and self.selected_player.is_human:
                mx, my = pygame.mouse.get_pos()
                rect = pygame.Rect(row_x, row_y, GameConfig.CARD_WIDTH+40, GameConfig.CARD_HEIGHT+150)
                if rect.collidepoint(mx, my):
                    pygame.draw.rect(SCREEN, GameConfig.YELLOW, rect, 4, border_radius=5)

    def draw_player_info(self):
        info_y = 10
        for p in self.players:
            color = GameConfig.BLACK if p.alive else GameConfig.RED
            txt = GameConfig.FONT.render(f"{p.name}: {p.penalty_points} pts {'(OUT)' if not p.alive else ''}", True, color)
            SCREEN.blit(txt, (10, info_y))
            info_y += 30

    def draw_hand(self):
        human = self.players[0]
        x_start = 50
        y_start = GameConfig.HEIGHT - GameConfig.CARD_HEIGHT - 50
        if self.state == "round" and human.alive and human not in self.player_cards_placed:
            for i, c in enumerate(human.hand):
                mx, my = pygame.mouse.get_pos()
                highlight = pygame.Rect(x_start+i*(GameConfig.CARD_WIDTH+5), y_start, 
                                     GameConfig.CARD_WIDTH, GameConfig.CARD_HEIGHT).collidepoint(mx, my)
                c.draw(SCREEN, x_start+i*(GameConfig.CARD_WIDTH+5), y_start, highlight=highlight, face_up=True)
        else:
            for i, c in enumerate(human.hand):
                c.draw(SCREEN, x_start+i*(GameConfig.CARD_WIDTH+5), y_start, face_up=True)

    def draw_animation(self):
        self.draw_rows()
        self.draw_player_info()
        self.draw_hand()
        self.animation_manager.draw(SCREEN)

    def draw(self):
        SCREEN.blit(background_img, (0, 0))

        if self.state == "menu":
            title = GameConfig.BIG_FONT.render("Select number of bot samurai frogs (1-9):", True, GameConfig.WHITE)
            SCREEN.blit(title, (GameConfig.WIDTH//2 - title.get_width()//2, GameConfig.HEIGHT//2 - 50))
            info = GameConfig.FONT.render("Press a key from 1 to 9 to select how many bots", True, GameConfig.WHITE)
            SCREEN.blit(info, (GameConfig.WIDTH//2 - info.get_width()//2, GameConfig.HEIGHT//2 + 10))

        elif self.state in ["round", "pick_row"]:
            self.draw_hand()
            self.draw_rows()
            self.draw_player_info()
            if self.state == "pick_row":
                msg = "Select a row to take."
                txt = GameConfig.BIG_FONT.render(msg, True, GameConfig.BLACK)
                SCREEN.blit(txt, (GameConfig.WIDTH//2 - txt.get_width()//2, 50))

        elif self.state == "reveal":
            self.draw_rows()
            self.draw_player_info()
            self.draw_hand()
            self.draw_reveal_cards()

        elif self.state == "animate":
            self.draw_animation()

        elif self.state == "leaderboard":
            SCREEN.fill(GameConfig.BLUE)
            leaderboard_text = GameConfig.BIG_FONT.render("Leaderboard", True, GameConfig.WHITE)
            SCREEN.blit(leaderboard_text, (GameConfig.WIDTH//2 - leaderboard_text.get_width()//2, 50))
            sorted_leaderboard = sorted(self.leaderboard, key=lambda x: x[1])
            start_y = 200
            for i, (name, points) in enumerate(sorted_leaderboard):
                line = f"{i+1}. {name}: {points} pts"
                line_surf = GameConfig.FONT.render(line, True, GameConfig.WHITE)
                SCREEN.blit(line_surf, (GameConfig.WIDTH//2 - line_surf.get_width()//2, start_y))
                start_y += 40

    def update(self, events):
        if self.state == "round":
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
            if self.reveal_timer > GameConfig.REVEAL_DELAY:
                self.handle_card_placement_final()

        elif self.state == "animate":
            self.animate_step()

def main():
    clock = pygame.time.Clock()
    game = Game()
    
    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == QUIT:
                running = False
            elif event.type == MOUSEBUTTONDOWN and event.button == 1:
                if game.state == "round":
                    human = game.players[0]
                    if human.alive and human not in game.player_cards_placed:
                        mx, my = event.pos
                        x_start = 50
                        y_start = GameConfig.HEIGHT - GameConfig.CARD_HEIGHT - 50
                        for i, c in enumerate(human.hand):
                            rect = pygame.Rect(x_start+i*(GameConfig.CARD_WIDTH+5), y_start, 
                                            GameConfig.CARD_WIDTH, GameConfig.CARD_HEIGHT)
                            if rect.collidepoint(mx, my):
                                game.player_cards_placed[human] = c
                                if game.all_players_placed():
                                    game.handle_card_placement_prep()
                                break
                elif game.state == "pick_row":
                    mx, my = event.pos
                    row_y = GameConfig.HEIGHT//2 - 2*(GameConfig.CARD_HEIGHT+10)
                    for i, row in enumerate(game.rows):
                        row_x = GameConfig.WIDTH//2 - 2*(GameConfig.CARD_WIDTH+20) + i*(GameConfig.CARD_WIDTH+100)
                        rect = pygame.Rect(row_x, row_y, GameConfig.CARD_WIDTH+40, GameConfig.CARD_HEIGHT+150)
                        if rect.collidepoint(mx, my):
                            game.pick_row_for_player(row)
                            break
            elif event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                if game.state == "menu":
                    if event.unicode.isdigit():
                        num = int(event.unicode)
                        if 1 <= num <= 9:
                            game.num_bots = num
                            game.state = "setup"
                            game.generate_deck()
                            game.shuffle_deck()
                            game.setup_players()
                            game.start_new_play()
            
        game.update(events)
        game.draw()
        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()
