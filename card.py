import pygame
from config import GameConfig

class Card:
    def __init__(self, value, penalty):
        self.value = value
        self.penalty = penalty
        self.rect = pygame.Rect(0, 0, GameConfig.CARD_WIDTH, GameConfig.CARD_HEIGHT)
        
    def draw(self, surface, x, y, highlight=False, face_up=True):
        self.rect.topleft = (x, y)
        if not face_up:
            surface.blit(GameConfig.CARD_BACK_IMG, (x, y))
            if highlight:
                pygame.draw.rect(surface, GameConfig.YELLOW, self.rect, 2, border_radius=5)
            else:
                pygame.draw.rect(surface, GameConfig.BLACK, self.rect, 2, border_radius=5)
            return
        
        color = GameConfig.YELLOW if highlight else GameConfig.WHITE
        pygame.draw.rect(surface, color, self.rect, border_radius=5)
        pygame.draw.rect(surface, GameConfig.BLACK, self.rect, 2, border_radius=5)

        frog_img = GameConfig.FROG_IMAGES.get(self.penalty)
        if frog_img:
            fw, fh = frog_img.get_width(), frog_img.get_height()
            fx = x + (GameConfig.CARD_WIDTH - fw)//2
            fy = y + (GameConfig.CARD_HEIGHT - fh)//2
            surface.blit(frog_img, (fx, fy))

        val_text = GameConfig.FONT.render(str(self.value), True, GameConfig.BLACK)
        penalty_text = GameConfig.FONT.render(str(self.penalty), True, GameConfig.RED)
        surface.blit(val_text, (x+GameConfig.CARD_WIDTH//2 - val_text.get_width()//2, y+5))
        surface.blit(penalty_text, (x+GameConfig.CARD_WIDTH//2 - penalty_text.get_width()//2, y+GameConfig.CARD_HEIGHT-30))

class CardAnimation:
    def __init__(self, player, card, start_pos, end_pos, take_row, row_obj):
        self.player = player
        self.card = card
        self.start_pos = start_pos
        self.end_pos = end_pos
        self.take_row = take_row
        self.row_obj = row_obj
        self.progress = 0.0
        self.speed = GameConfig.ANIMATION_SPEED

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