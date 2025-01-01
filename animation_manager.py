from config import GameConfig
from card import CardAnimation

class AnimationManager:
    def __init__(self, game):
        self.animations = []
        self.pending_placements = []
        self.game = game
        
    def create_card_animations(self, placements):
        self.animations = []
        self.pending_placements = placements
        
        cx = GameConfig.WIDTH//2
        cy = GameConfig.HEIGHT//2
        reveal_count = len(placements)
        reveal_start_x = cx - (reveal_count*(GameConfig.CARD_WIDTH+10))//2

        for i, (player, card, row_obj, take_row) in enumerate(placements):
            row_index = self.game.rows.index(row_obj)
            row_x = GameConfig.WIDTH//2 - 2*(GameConfig.CARD_WIDTH+20) + row_index*(GameConfig.CARD_WIDTH+100) + 20
            
            final_y = GameConfig.HEIGHT//2 - 2*(GameConfig.CARD_HEIGHT+10) + 10
            if not take_row:
                final_y += len(row_obj.cards)*(GameConfig.CARD_HEIGHT//2)

            start_x = reveal_start_x + i*(GameConfig.CARD_WIDTH+10)
            start_y = cy - GameConfig.CARD_HEIGHT//2

            anim = CardAnimation(player, card, (start_x, start_y), 
                               (row_x, final_y), take_row, row_obj)
            self.animations.append(anim)
    
    def update(self):
        if not self.animations:
            return True
            
        done = True
        for anim in self.animations:
            if not anim.update():
                done = False
        return done
        
    def draw(self, surface):
        for anim in self.animations:
            anim.draw(surface)
            
    def get_results(self):
        return self.animations, self.pending_placements 