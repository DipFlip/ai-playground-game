from world import World

def main():
    world = World()
    
    # Move to the lake
    world.character.move(2, 2)
    world.try_interact()  # Catches a fish
    
    # Move to the shop
    world.character.move(3, 3)  # Move to (5, 5)
    world.try_interact()  # Sells the fish for a coin
    
    # print(f"Character has {world.character.fish} fish and {world.character.coins} coins")

if __name__ == "__main__":
    main() 