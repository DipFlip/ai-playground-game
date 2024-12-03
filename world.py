from character import Character
from lake import Lake
from shop import Shop
from npc import NPC
from typing import List

class World:
    def __init__(self):
        self.character = Character(0, 0)
        self.locations = [
            Lake(2, 2),
            Shop(5, 5),
            NPC(1, 1),
            NPC(4, 4)
        ]

    def get_location_at(self, x: int, y: int):
        for location in self.locations:
            if location.x == x and location.y == y:
                return location
        return None

    def try_interact(self):
        location = self.get_location_at(self.character.x, self.character.y)
        if location:
            if isinstance(location, NPC):
                location.interact()
            else:
                location.interact(self.character)
            return True
        return False 