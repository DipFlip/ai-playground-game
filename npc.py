from location import Location
from character import Character

class NPC(Character):
    @property
    def emoji(self) -> str:
        return "🐮"
    
    def interact(self, character: Character) -> None:
        self.talk("Hey there, how do you do?") 
        character.add_item('Milk')