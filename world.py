from character import Character
from npc import NPC
from typing import List
from PIL import Image
import os
import glob
import random
import time

# Global in-memory storage for dynamically created NPCs
DYNAMIC_NPCS = []

class World:
    def __init__(self):
        self.character = Character(0, 0)
        self.current_interaction = None
        
        # Load obstruction and map images first
        base_path = os.path.dirname(os.path.abspath(__file__))
        obstruction_path = os.path.join(base_path, 'graphics', 'obstructions.png')
        map_path = os.path.join(base_path, 'graphics', 'map.png')
        
        self.obstruction_map = Image.open(obstruction_path).convert('L')
        self.background_map = Image.open(map_path)
        
        # Set up image dimensions and center point
        self.map_width, self.map_height = self.obstruction_map.size
        self.center_x = int(self.map_width // 2)
        self.center_y = int(self.map_height // 2)
        
        # Load NPCs from files and memory
        self.locations = []
        
        # Load static NPCs from files
        npc_path = os.path.join(base_path, 'npcs', '*.yaml')
        for npc_file in glob.glob(npc_path):
            npc = NPC.from_yaml(npc_file)
            if npc.needs_position:
                # Find a suitable position for the NPC
                x, y = self.find_random_position()
                npc.x = x
                npc.y = y
            self.locations.append(npc)
        
        # Load dynamic NPCs from memory
        for npc_data in DYNAMIC_NPCS:
            npc = NPC.from_yaml_data(npc_data)
            if npc.needs_position:
                x, y = self.find_random_position()
                npc.x = x
                npc.y = y
            self.locations.append(npc)
        
        # Initialize last update time
        self.last_update_time = time.time()

    def update(self):
        """Update the world state, including NPC movements."""
        current_time = time.time()
        
        # Update NPCs
        for location in self.locations:
            if isinstance(location, NPC):
                location.try_wander(self, current_time)
        
        self.last_update_time = current_time

    def get_location_at(self, x: int, y: int):
        for location in self.locations:
            if location.x == x and location.y == y:
                return location
        return None

    def try_interact(self):
        location = self.get_location_at(self.character.x, self.character.y)
        if location:
            if isinstance(location, NPC):
                if not location.is_talking:
                    self.current_interaction = location
                location.interact(self.character)
                if not location.is_talking:
                    self.current_interaction = None
            return True
        return False

    def is_interaction_active(self):
        return self.current_interaction is not None
    
    def can_move_to(self, x: int, y: int) -> bool:
        # Convert world coordinates to image coordinates
        img_x = self.center_x + x
        img_y = self.center_y + y
        
        # Check if position is within map bounds
        if (0 <= img_x < self.map_width and 
            0 <= img_y < self.map_height):
            # Get pixel value at position (0 is black, 255 is white)
            pixel_value = self.obstruction_map.getpixel((img_x, img_y))
            # Return True if pixel is closer to white (walkable)
            return pixel_value > 127
        return False

    def find_random_position(self) -> List[int]:
        """Find a random walkable position that's not occupied by any character."""
        # Define search bounds (adjust these based on your map size)
        min_x, max_x = -10, 10
        min_y, max_y = -10, 10
        max_attempts = 100
        
        for _ in range(max_attempts):
            x = random.randint(min_x, max_x)
            y = random.randint(min_y, max_y)
            
            # Check if position is walkable and not occupied
            if self.can_move_to(x, y) and not self.get_location_at(x, y):
                return [x, y]
        
        # If no position found, return a default position
        return [0, 0]