from abc import ABC, abstractmethod

class Character:
    def __init__(self, x: int, y: int, emoji: str='🐱'):
        self.x = x
        self.y = y
        self.inventory = {}
        self.emoji = emoji
    @abstractmethod
    def interact(self, character: "Character") -> None:
        pass 

    def talk(self, text):
        print(f"{self.emoji}: {text}")
    
    def move(self, dx: int, dy: int):
        self.x += dx
        self.y += dy

    def has_item(self, item: str, amount: int = 1) -> bool:
        """Check if character has at least the specified amount of an item"""
        return item in self.inventory and self.inventory[item] >= amount

    def add_item(self, item: str, amount: int = 1):
        if item not in self.inventory:
            self.inventory[item] = 0
        self.inventory[item] += amount

    def remove_item(self, item: str, amount: int = 1) -> bool:
        if item in self.inventory and self.inventory[item] >= amount:
            self.inventory[item] -= amount
            # if self.inventory[item] == 0:
            #     del self.inventory[item]
            return True
        return False 