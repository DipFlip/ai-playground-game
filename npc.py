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
    item: str = None
    quantity: int = 1

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
    
    def get_next_action(self) -> NPCAction:
        action = self.actions[self.current_action]
        self.current_action = (self.current_action + 1) % len(self.actions)
        self.is_talking = self.current_action != 0
        return action

    def interact(self, character: Character) -> None:
        if not self.is_talking:
            self.is_talking = True
        
        action = self.get_next_action()
        
        if action.type == "talk":
            self.talk(f"{self.name}: {action.text}")
        elif action.type == "give":
            for _ in range(action.quantity):
                character.add_item(action.item)