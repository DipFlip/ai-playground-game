from character import Character
from npc import NPC
from typing import List, Dict
from PIL import Image
import os
import glob
import random
import time
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global in-memory storage for all dynamic state
DYNAMIC_NPCS = []
NPC_POSITIONS = {}  # Store current positions of all NPCs
PLAYER_STATE = {
    'x': 0,
    'y': 0,
    'inventory': {}
}

class World:
    def __init__(self):
        self.character = Character(PLAYER_STATE['x'], PLAYER_STATE['y'])
        self.character.inventory = PLAYER_STATE['inventory'].copy()
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
        
        # Initialize locations list
        self.locations = []
        
        # Load all NPCs
        self.reload_npcs()
        
        # Initialize last update time
        self.last_update_time = time.time()

    def reload_npcs(self):
        """Reload all NPCs, particularly after adding a new dynamic NPC"""
        # Keep track of non-NPC locations
        non_npc_locations = [loc for loc in self.locations if not isinstance(loc, NPC)]
        
        # Clear current NPCs
        self.locations = non_npc_locations
        
        # Load static NPCs from files
        base_path = os.path.dirname(os.path.abspath(__file__))
        npc_path = os.path.join(base_path, 'npcs', '*.yaml')
        for npc_file in glob.glob(npc_path):
            try:
                npc = NPC.from_yaml(npc_file)
                npc_id = os.path.basename(npc_file)
                
                # Use stored position if available
                if npc_id in NPC_POSITIONS:
                    npc.x, npc.y = NPC_POSITIONS[npc_id]['x'], NPC_POSITIONS[npc_id]['y']
                elif npc.needs_position:
                    x, y = self.find_random_position()
                    npc.x, npc.y = x, y
                    NPC_POSITIONS[npc_id] = {'x': x, 'y': y}
                else:
                    NPC_POSITIONS[npc_id] = {'x': npc.x, 'y': npc.y}
                    
                self.locations.append(npc)
            except Exception as e:
                logger.error(f"Error loading static NPC from {npc_file}: {str(e)}")
                continue
        
        # Load dynamic NPCs from memory
        for dynamic_npc in DYNAMIC_NPCS:
            try:
                if not isinstance(dynamic_npc, dict):
                    logger.error(f"Invalid dynamic NPC format: {dynamic_npc}")
                    continue
                    
                npc_id = dynamic_npc.get('id')
                if not npc_id:
                    logger.error(f"Dynamic NPC missing ID: {dynamic_npc}")
                    continue
                
                npc_id = f"dynamic_{npc_id}"
                
                # Validate NPC data
                if not dynamic_npc.get('data') or not isinstance(dynamic_npc['data'], dict):
                    logger.error(f"Invalid NPC data format: {dynamic_npc}")
                    continue
                
                # Create NPC from stored data
                npc = NPC.from_yaml_data(dynamic_npc['data'])
                
                # Set position from stored data
                npc.x = dynamic_npc.get('x', 0)
                npc.y = dynamic_npc.get('y', 0)
                
                # Update NPC_POSITIONS
                NPC_POSITIONS[npc_id] = {'x': npc.x, 'y': npc.y}
                
                self.locations.append(npc)
                logger.debug(f"Successfully loaded dynamic NPC: {npc_id}")
            except Exception as e:
                logger.error(f"Error loading dynamic NPC: {str(e)}", exc_info=True)
                continue

    def update_npcs(self):
        """Update only NPC states and positions, leaving player state unchanged."""
        current_time = time.time()
        
        # Update NPCs and their positions in memory
        for i, location in enumerate(self.locations):
            if isinstance(location, NPC):
                # Try to make the NPC wander
                if location.try_wander(self, current_time):
                    # If NPC moved, update its position in memory
                    npc_id = f"dynamic_{i}" if i >= len(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'npcs', '*.yaml'))) else os.path.basename(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'npcs', '*.yaml'))[i])
                    NPC_POSITIONS[npc_id] = {'x': location.x, 'y': location.y}
                    # Log debug info instead of printing
                    logger.debug(f"NPC {location.name} moved to {location.x}, {location.y}")
                # Always update position in memory even if NPC didn't move
                else:
                    npc_id = f"dynamic_{i}" if i >= len(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'npcs', '*.yaml'))) else os.path.basename(glob.glob(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'npcs', '*.yaml'))[i])
                    NPC_POSITIONS[npc_id] = {'x': location.x, 'y': location.y}
        
        self.last_update_time = current_time

    def update(self):
        """Update the world state, including NPC movements and player state."""
        self.update_npcs()
        
        # Update player state in memory
        PLAYER_STATE['x'] = self.character.x
        PLAYER_STATE['y'] = self.character.y
        PLAYER_STATE['inventory'] = self.character.inventory.copy()

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

    def reset(self):
        """Reset the world state to initial values."""
        # Reset player state
        PLAYER_STATE.update({
            'x': 0,
            'y': 0,
            'inventory': {}
        })
        
        # Reset character
        self.character.x = 0
        self.character.y = 0
        self.character.inventory = {}
        
        # Clear NPC positions
        NPC_POSITIONS.clear()
        
        # Clear dynamic NPCs
        DYNAMIC_NPCS.clear()
        
        # Clear current interaction
        self.current_interaction = None
        
        # Reload NPCs to reset their positions
        self.reload_npcs()
        
        logger.info("Game state reset successfully")