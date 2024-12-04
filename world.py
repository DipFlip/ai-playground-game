from character import Character
from lake import Lake
from shop import Shop
from npc import NPC
from typing import List
from PIL import Image
import os
import glob

class World:
    def __init__(self):
        self.character = Character(0, 0)
        
        # Load NPCs from YAML files
        base_path = os.path.dirname(os.path.abspath(__file__))
        npc_path = os.path.join(base_path, 'npcs', '*.yaml')
        npcs = []
        for npc_file in glob.glob(npc_path):
            npcs.append(NPC.from_yaml(npc_file))
        
        self.locations = [
            Lake(-6, -7),
            Shop(5, -1),
            *npcs  # Unpack NPCs into locations list
        ]
        
        # Load obstruction and map images
        base_path = os.path.dirname(os.path.abspath(__file__))
        obstruction_path = os.path.join(base_path, 'graphics', 'obstructions.png')
        map_path = os.path.join(base_path, 'graphics', 'map.png')
        
        self.obstruction_map = Image.open(obstruction_path).convert('L')
        self.background_map = Image.open(map_path)
        
        # Image dimensions and center point
        self.map_width, self.map_height = self.obstruction_map.size
        self.center_x = self.map_width // 2
        self.center_y = self.map_height // 2
        self.current_interaction = None

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
            else:
                location.interact(self.character)
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