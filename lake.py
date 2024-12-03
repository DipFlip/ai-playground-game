from location import Location
from character import Character

class Lake(Location):
    def interact(self, character: Character) -> None:
        character.add_item("fish")
        print("You caught a fish!") 