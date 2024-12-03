from location import Location
from character import Character

class Shop(Location):
    @property
    def emoji(self) -> str:
        return "🏪"
        
    def interact(self, character: Character) -> None:
        if character.remove_item("fish"):
            character.add_item("coins")
            print("You sold a fish for 1 coin!")
        else:
            print("You need a fish to trade!") 