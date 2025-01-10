from character import Character
from typing import List, Dict, Union, Optional
import yaml
import os
from dataclasses import dataclass
import random
import time
from sequence import Sequence, Node

class NPC(Character):
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'NPC':
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)
        return cls.from_yaml_data(data)
    
    @classmethod
    def from_yaml_data(cls, data: dict) -> 'NPC':
        npc_data = data['npc']
        sequence_data = data['sequence']
        
        # Get position from data or let the world decide later
        position = npc_data.get('position', None)
        x, y = position if position else (0, 0)
        
        # Get wandering behavior settings
        wander_settings = npc_data.get('wander', {})
        if isinstance(wander_settings, bool):
            # Handle case where wander is just a boolean
            should_wander = wander_settings
            wander_interval = 5
        else:
            # Default wandering behavior based on NPC type
            default_should_wander = not any(word in npc_data.get('name', '').lower() for word in ['shop', 'lake', 'store'])
            should_wander = wander_settings.get('enabled', default_should_wander)
            wander_interval = wander_settings.get('interval', 5)
        
        # Create sequence
        sequence = Sequence(sequence_data)
        
        npc = cls(x, y, npc_data['emoji'], sequence, npc_data['name'], 
                 should_wander=should_wander, wander_interval=wander_interval)
        npc.needs_position = position is None
        npc.personality = npc_data.get('personality', '')
        return npc

    def __init__(self, x: int, y: int, emoji: str='', sequence: Sequence = None, 
                 name: str = "Unknown", should_wander: bool = True, 
                 wander_interval: int = 5):
        super().__init__(x, y, emoji)
        self.sequence = sequence if sequence else Sequence([{"type": "talk", "text": "..."}])
        self.is_talking = False
        self.name = name
        self.personality = ""
        self.needs_position = False  # Flag to indicate if we need a position from the world
        self.last_wander_time = time.time() + random.uniform(0, 10)  # Longer random initial offset
        self.wander_interval = wander_interval  # Default wander interval in seconds
        self.wander_interval_offset = random.uniform(-0.5, 0.5)  # Smaller random offset
        self.should_wander = should_wander  # Whether this NPC should wander

    @property
    def waiting_for_response(self) -> bool:
        """Proxy to sequence's waiting_for_response"""
        return self.sequence.waiting_for_response

    def get_current_node(self) -> Optional[Node]:
        """Get the current node in the sequence"""
        return self.sequence.current_node

    def provide_response(self, response: str, character: Character = None) -> None:
        """Handle a response from the player"""
        if not self.sequence.waiting_for_response:
            return
        
        self.sequence.provide_response(response)

    def interact(self, character: Character) -> None:
        """Handle interaction with a character"""
        if not self.is_talking:
            self.is_talking = True
            self.sequence.reset()  # Reset sequence to initial state
        
        self.sequence.interact(self, character)

    def try_wander(self, world, current_time: float) -> bool:
        """Attempt to make the NPC wander if enough time has passed."""
        if not self.should_wander or self.is_talking:
            return False

        # Check if enough time has passed since last wander
        actual_interval = self.wander_interval + self.wander_interval_offset
        time_since_last = current_time - self.last_wander_time
        if time_since_last < actual_interval:
            return False

        # Choose a random direction
        directions = [(0, 1), (0, -1), (1, 0), (-1, 0)]
        dx, dy = random.choice(directions)
        new_x, new_y = self.x + dx, self.y + dy

        # Check if the new position is valid and unoccupied
        if world.can_move_to(new_x, new_y) and not world.get_location_at(new_x, new_y):
            self.x = new_x
            self.y = new_y
            self.last_wander_time = current_time
            # Add some randomness to next interval
            self.wander_interval_offset = random.uniform(-1, 1)  # Reduced randomness
            return True

        return False