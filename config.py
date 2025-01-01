import pygame

class GameConfig:
    # Window dimensions
    WIDTH = 1200
    HEIGHT = 800
    
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
    
    # Game rules
    MAX_PENALTY_POINTS = 60
    CARDS_PER_PLAYER = 10
    NUM_ROWS = 4
    
    # Animation
    REVEAL_DELAY = 60
    ANIMATION_SPEED = 0.05
    
    # Fonts
    FONT = pygame.font.SysFont(None, 32)
    BIG_FONT = pygame.font.SysFont(None, 64)
    
    # Weighted penalty distribution
    PENALTY_WEIGHTS = [6, 5, 4, 3, 2, 1]
    PENALTY_VALUES = range(1, 7)
    
    @classmethod
    def get_penalty_distribution(cls):
        distribution = []
        for v, w in zip(cls.PENALTY_VALUES, cls.PENALTY_WEIGHTS):
            distribution.extend([v]*w)
        return distribution 