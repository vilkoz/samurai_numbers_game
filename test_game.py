import pytest
from main2 import Game
from player import Player, Row
from card import Card

def test_row_with_five_cards():
    # Створюємо гру
    game = Game()
    
    # Створюємо тестових гравців
    human = Player("Test Human", is_human=True)
    bot = Player("Test Bot", is_human=False)
    game.players = [human, bot]
    
    # Створюємо тестовий ряд з 5 картами
    test_row = Row()
    for value in [10, 20, 30, 40, 50]:  # 5 карт зі зростаючими значеннями
        test_row.add_card(Card(value, 1))
    
    # Встановлюємо тестовий ряд
    game.rows = [test_row]
    
    # Симулюємо спробу бота додати карту
    bot_card = Card(60, 1)  # Карта з більшим значенням
    bot.hand = [bot_card]
    game.player_cards_placed = {bot: bot_card}
    
    # Викликаємо метод розміщення карт
    game.handle_card_placement_final()
    
    # Перевіряємо, що бот взяв карти з ряду
    assert len(game.pending_placements) == 1
    player, card, row, take_row = game.pending_placements[0]
    assert player == bot
    assert card == bot_card
    assert row == test_row
    assert take_row == True  # Повинен взяти ряд

def print_game_state(game):
    print("\nGame State:")
    for i, row in enumerate(game.rows):
        print(f"Row {i}: {[card.value for card in row.cards]}")
    print("Pending placements:", [(p.name, c.value, r.cards[-1].value if r.cards else None, t) 
                                for p, c, r, t in game.pending_placements])

def test_multiple_players_with_full_row():
    game = Game()
    
    # Створюємо гравців
    players = [
        Player("Human", is_human=True),
        Player("Bot 1", is_human=False),
        Player("Bot 2", is_human=False)
    ]
    game.players = players
    
    # Створюємо ряд з 5 картами
    full_row = Row()
    for value in [10, 20, 30, 40, 50]:
        full_row.add_card(Card(value, 1))
    
    # Створюємо інші ряди
    other_row = Row()
    other_row.add_card(Card(5, 1))
    
    game.rows = [full_row, other_row]
    
    # Симулюємо хід, де всі гравці кладуть карти
    game.player_cards_placed = {
        players[0]: Card(60, 1),
        players[1]: Card(70, 1),
        players[2]: Card(80, 1)
    }
    
    print_game_state(game)
    game.handle_card_placement_final()
    print_game_state(game)
    
    # Перевірки
    assert len(game.pending_placements) > 0
    # Перший гравець з найменшим значенням карти повинен взяти повний ряд
    first_placement = game.pending_placements[0]
    assert first_placement[3] == True  # take_row має бути True
    assert first_placement[2] == full_row  # має бути повний ряд

if __name__ == "__main__":
    test_multiple_players_with_full_row() 