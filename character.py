class Character:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.inventory = {}

    def move(self, dx: int, dy: int):
        self.x += dx
        self.y += dy

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