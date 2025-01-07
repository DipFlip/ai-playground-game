from character import Character
from typing import List, Dict, Union, Optional
import yaml
import os
from dataclasses import dataclass
import random
import time
from sequence import Sequence, State

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

    def get_current_state(self) -> Optional[State]:
        """Proxy to sequence's get_current_state"""
        return self.sequence.get_current_state()

    def provide_response(self, response: str, character: Character = None) -> None:
        """Handle a response from the player"""
        if not self.sequence.waiting_for_response:
            return
        
        self.sequence.provide_response(response)

    def interact(self, character: Character) -> None:
        if not self.is_talking:
            self.is_talking = True
            self.sequence.reset()  # Reset sequence to initial state
        
        current_state = self.sequence.get_current_state()
        if not current_state:
            self.is_talking = False
            return

        if current_state.type == "talk":
            formatted_text = self.sequence.format_text(current_state.text)
            self.talk(f"{self.name}: {formatted_text}")
            # Auto-transition to next state
            self.sequence.current_state_id = current_state.next_state
        
        elif current_state.type == "give":
            if current_state.item:
                quantity = current_state.item.get('quantity', 1)
                for _ in range(quantity):
                    character.add_item(current_state.item['name'])
                if current_state.text:
                    formatted_text = self.sequence.format_text(current_state.text)
                    self.talk(f"{self.name}: {formatted_text}")
            # Auto-transition to next state
            self.sequence.current_state_id = current_state.next_state
        
        elif current_state.type == "ask":
            formatted_text = self.sequence.format_text(current_state.text)
            self.talk(f"{self.name}: {formatted_text}")
            self.sequence.waiting_for_response = True
        
        elif current_state.type == "Choice":
            formatted_text = self.sequence.format_text(current_state.text)
            self.talk(f"{self.name}: {formatted_text}")
            self.sequence.waiting_for_response = True
        
        elif current_state.type == "trade":
            if current_state.trade:
                want = current_state.trade['want']
                offer = current_state.trade['offer']
                want_quantity = want.get('quantity', 1)
                
                has_items = character.has_item(want['name'], want_quantity)
                
                if has_items:
                    for _ in range(want_quantity):
                        character.remove_item(want['name'])
                    
                    offer_quantity = offer.get('quantity', 1)
                    for _ in range(offer_quantity):
                        character.add_item(offer['name'])
                    
                    formatted_text = self.sequence.format_text(current_state.trade['success_text'])
                    self.talk(f"{self.name}: {formatted_text}")
                else:
                    formatted_text = self.sequence.format_text(current_state.trade['failure_text'])
                    self.talk(f"{self.name}: {formatted_text}")
                
                if current_state.text:
                    formatted_text = self.sequence.format_text(current_state.text)
                    self.talk(f"{self.name}: {formatted_text}")
            # Auto-transition to next state
            self.sequence.current_state_id = current_state.next_state

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