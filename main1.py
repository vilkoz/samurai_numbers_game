import pygame
import random

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
CARD_WIDTH, CARD_HEIGHT = 50, 70
NUM_CARDS = 110
CARDS_PER_PLAYER = 10
POINTS_TO_LOSE = 60

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)

# Screen setup
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Samurai Numbers Game")

# Card class
class Card:
    def __init__(self, number):
        self.number = number
        self.points = random.choices([1, 2, 3, 4, 5, 6], weights=[6, 5, 4, 3, 2, 1])[0]

    def draw(self, x, y):
        pygame.draw.rect(screen, WHITE, (x, y, CARD_WIDTH, CARD_HEIGHT))
        font = pygame.font.Font(None, 36)
        text = font.render(str(self.number), True, BLACK)
        screen.blit(text, (x + 10, y + 10))
        points_text = font.render(str(self.points), True, RED)
        screen.blit(points_text, (x + 10, y + 40))

    def draw_back(self, x, y):
        pygame.draw.rect(screen, BLUE, (x, y, CARD_WIDTH, CARD_HEIGHT))

# Player class
class Player:
    def __init__(self, name):
        self.name = name
        self.cards = []
        self.point_stack = 0

    def draw_cards(self, x, y):
        for i, card in enumerate(self.cards):
            card.draw(x + i * (CARD_WIDTH + 10), y)

    def select_card(self, pos):
        x, y = pos
        for i, card in enumerate(self.cards):
            card_x = 50 + i * (CARD_WIDTH + 10)
            card_y = 50
            if card_x <= x <= card_x + CARD_WIDTH and card_y <= y <= card_y + CARD_HEIGHT:
                return self.cards.pop(i)
        return None

# Bot class
class Bot(Player):
    def __init__(self, name):
        super().__init__(name)

    def make_move(self, rows):
        # AI logic for bot moves (random for now)
        return self.cards.pop(random.randint(0, len(self.cards) - 1))

    def draw_back_of_cards(self, x, y):
        for i in range(len(self.cards)):
            self.cards[i].draw_back(x + i * (CARD_WIDTH + 10), y)

# Game states
class GameState:
    PLAYER_TURN = 1
    BOT_TURN = 2
    FLIP_CARDS = 3
    SHOW_RESULTS = 4

# Game class
class Game:
    def __init__(self):
        self.num_players = self.select_num_players()
        self.players, self.rows = self.setup_game(self.num_players)
        self.selected_card = None
        self.play_zone_cards = []
        self.game_state = GameState.PLAYER_TURN
        self.flip_start_time = None

    def setup_game(self, num_players):
        numbers = list(range(1, NUM_CARDS + 1))
        random.shuffle(numbers)
        players = [Player("Human Player")]
        for i in range(num_players - 1):
            players.append(Bot(f"Bot {i+1}"))
        for player in players:
            for _ in range(CARDS_PER_PLAYER):
                number = numbers.pop()
                player.cards.append(Card(number))
        rows = [[Card(numbers.pop())] for _ in range(4)]
        return players, rows

    def select_num_players(self):
        num_players = 1
        selecting = True
        while selecting:
            screen.fill(BLACK)
            font = pygame.font.Font(None, 36)
            text = font.render(f"Select number of bot players (1-9): {num_players}", True, WHITE)
            screen.blit(text, (50, 50))
            pygame.display.flip()
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP and num_players < 9:
                        num_players += 1
                    elif event.key == pygame.K_DOWN and num_players > 1:
                        num_players -= 1
                    elif event.key == pygame.K_RETURN:
                        selecting = False
        return num_players + 1  # Including the human player

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            elif event.type == pygame.MOUSEBUTTONDOWN and self.game_state == GameState.PLAYER_TURN:
                if event.button == 1:  # Left mouse button
                    self.selected_card = self.players[0].select_card(event.pos)
                    if self.selected_card:
                        self.play_zone_cards.append(self.selected_card)
                        for bot in self.players[1:]:
                            self.play_zone_cards.append(bot.make_move(self.rows))
                        self.game_state = GameState.FLIP_CARDS
                        self.flip_start_time = pygame.time.get_ticks()
        return True

    def update(self):
        if self.game_state == GameState.FLIP_CARDS:
            current_time = pygame.time.get_ticks()
            if current_time - self.flip_start_time > 1000:  # 1 second delay before flipping
                self.game_state = GameState.SHOW_RESULTS

        if self.game_state == GameState.SHOW_RESULTS:
            self.game_state = GameState.PLAYER_TURN

    def render(self):
        screen.fill(BLACK)
        self.players[0].draw_cards(50, 50)  # Draw only the human player's cards

        # Draw bot cards (back side)
        for i, player in enumerate(self.players[1:]):
            player.draw_back_of_cards(50, 150 + i * (CARD_HEIGHT + 10))

        # Draw initial rows vertically
        for i, row in enumerate(self.rows):
            for j, card in enumerate(row):
                card.draw(200 + i * (CARD_WIDTH + 10), 300 + j * (CARD_HEIGHT + 10))

        # Draw selected cards face down in the play zone
        for i, card in enumerate(self.play_zone_cards):
            card.draw_back(400 + i * (CARD_WIDTH + 10), 500)

        # Handle game states
        if self.game_state == GameState.FLIP_CARDS:
            current_time = pygame.time.get_ticks()
            if current_time - self.flip_start_time > 1000:  # 1 second delay before flipping
                self.game_state = GameState.SHOW_RESULTS

        if self.game_state == GameState.SHOW_RESULTS:
            for i, card in enumerate(self.play_zone_cards):
                card.draw(400 + i * (CARD_WIDTH + 10), 500)
            pygame.display.flip()
            pygame.time.wait(2000)  # Show the cards for 2 seconds
            self.play_zone_cards.clear()
            self.game_state = GameState.PLAYER_TURN

        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.render()
        pygame.quit()

if __name__ == "__main__":
    game = Game()
    game.run()