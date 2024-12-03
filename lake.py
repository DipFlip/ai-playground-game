from location import Location
from character import Character

class Lake(Location):
    @property
    def emoji(self) -> str:
        return "🎣"
        
    def interact(self, character: Character) -> None:
        character.add_item("fish")
        print("You caught a fish!") 