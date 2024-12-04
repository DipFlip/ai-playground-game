from location import Location
from character import Character

class NPC(Character):
    def __init__(self, x: int, y: int, emoji: str='', dialogues: list[str] = None):
        super().__init__(x, y, emoji)
        self.dialogues = dialogues if dialogues else ["..."]
        self.current_dialogue = 0
    
    def get_next_dialogue(self) -> str:
        dialogue = self.dialogues[self.current_dialogue]
        self.current_dialogue = (self.current_dialogue + 1) % len(self.dialogues)
        return dialogue

    def interact(self, character: Character) -> None:
        self.talk(self.get_next_dialogue())
        character.add_item('Milk')