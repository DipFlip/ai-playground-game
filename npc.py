from location import Location
from character import Character

class NPC(Character):
    def __init__(self, x: int, y: int, emoji: str='', dialogues: list[str] = None):
        super().__init__(x, y, emoji)
        self.dialogues = dialogues if dialogues else ["..."]
        self.current_dialogue = 0
        self.is_talking = False
    
    def get_next_dialogue(self) -> str:
        dialogue = self.dialogues[self.current_dialogue]
        self.current_dialogue = (self.current_dialogue + 1) % len(self.dialogues)
        self.is_talking = self.current_dialogue != 0
        return dialogue

    def interact(self, character: Character) -> None:
        if not self.is_talking:
            self.is_talking = True
        self.talk(self.get_next_dialogue())
        if not self.is_talking:
            character.add_item('Milk')