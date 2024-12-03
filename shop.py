from location import Location
from character import Character

class Shop(Location):
    def interact(self, character: Character) -> None:
        if character.remove_fish():
            character.add_coins()
            print("You sold a fish for 1 coin!")
        else:
            print("You need a fish to trade!") 