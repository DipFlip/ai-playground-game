from abc import ABC, abstractmethod
from character import Character

class Location(ABC):
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y

    @abstractmethod
    def interact(self, character: Character) -> None:
        pass 