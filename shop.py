from character import Character

class Shop(Character):
    @property
    def emoji(self) -> str:
        return "👩‍🌾"
        
    def interact(self, character: Character) -> None:
        if character.remove_item("fish"):
            character.add_item("coins")
            self.talk("Nice fish, take a coin for it!")
        else:
            self.talk("Got anything to sell?") 