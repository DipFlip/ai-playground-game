from location import Location
from character import Character
from typing import List, Dict, Union
import yaml
import os
from dataclasses import dataclass

@dataclass
class NPCAction:
    type: str
    text: str = None
    user_input: str = None  # Field to store response variable name
    item: Dict[str, Union[str, int]] = None  # Object containing name and quantity

class NPC(Character):
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'NPC':
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)['npc']
        
        x, y = data['position']
        
        # Convert YAML sequence to action objects
        actions = []
        for action in data['sequence']:
            actions.append(NPCAction(**action))
        
        return cls(x, y, data['emoji'], actions, data['name'])

    def __init__(self, x: int, y: int, emoji: str='', actions: List[NPCAction] = None, name: str = "Unknown"):
        super().__init__(x, y, emoji)
        self.actions = actions if actions else [NPCAction(type="talk", text="...")]
        self.current_action = 0
        self.is_talking = False
        self.name = name
        self.responses = {}  # Store player responses
        self.waiting_for_response = False
        self.current_question = None
    
    def get_next_action(self) -> NPCAction:
        action = self.actions[self.current_action]
        # Only advance if not waiting for a response
        if not self.waiting_for_response:
            self.current_action = (self.current_action + 1) % len(self.actions)
            self.is_talking = self.current_action != 0
        return action

    def format_text(self, text: str) -> str:
        """Format text with stored responses"""
        try:
            return text.format(**self.responses)
        except KeyError:
            # If we're missing a response, return the raw text
            return text

    def provide_response(self, response: str) -> None:
        """Handle a response from the player"""
        if self.waiting_for_response and self.current_question:
            self.responses[self.current_question.user_input] = response
            self.waiting_for_response = False
            self.current_question = None

    def interact(self, character: Character) -> None:
        if not self.is_talking:
            self.is_talking = True
        
        action = self.get_next_action()
        
        if action.type == "talk":
            # Format the text with any stored responses
            formatted_text = self.format_text(action.text)
            self.talk(f"{self.name}: {formatted_text}")
        elif action.type == "give":
            if action.item:
                quantity = action.item.get('quantity', 1)
                for _ in range(quantity):
                    character.add_item(action.item['name'])
        elif action.type == "ask":
            self.talk(f"{self.name}: {action.text}")
            self.waiting_for_response = True
            self.current_question = action