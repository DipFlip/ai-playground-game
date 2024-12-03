class Character:
    def __init__(self, x: int, y: int):
        self.x = x
        self.y = y
        self.fish = 0
        self.coins = 0

    def move(self, dx: int, dy: int):
        self.x += dx
        self.y += dy

    def add_fish(self, amount: int = 1):
        self.fish += amount

    def remove_fish(self, amount: int = 1):
        if self.fish >= amount:
            self.fish -= amount
            return True
        return False

    def add_coins(self, amount: int = 1):
        self.coins += amount 