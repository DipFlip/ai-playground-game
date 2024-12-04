from location import Location
from character import Character

class NPC(Location):
    @property
    def emoji(self) -> str:
        return "🐮"  # Speech bubble emoji to represent an NPC you can talk to
        
    def interact(self, character: Character) -> None:
        print("Hey there, how do you do?") 