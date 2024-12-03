from character import Character

class NPC(Character):
    def __init__(self, x: int, y: int):
        super().__init__(x, y)
    
    def interact(self) -> None:
        print("Hey there, how do you do?") 