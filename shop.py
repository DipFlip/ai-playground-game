from character import Character

class Shop(Character):
    def __init__(self, x: int, y: int, emoji: str = '👩‍🌾'):
        super().__init__(x, y, emoji)       
    def interact(self, character: Character) -> None:
        if character.remove_item("fish"):
            character.add_item("coins")
            self.talk("Nice fish, take a coin for it!")
        else:
            self.talk("Got anything to sell?") 