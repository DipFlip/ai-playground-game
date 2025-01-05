from location import Location
from character import Character
from typing import List, Dict, Union, Optional
import yaml
import os
from dataclasses import dataclass

@dataclass
class NPCState:
    type: str
    text: str = None
    user_input: str = None
    item: Dict[str, Union[str, int]] = None
    trade: Dict[str, Union[Dict[str, Union[str, int]], str]] = None
    choices: List[Dict[str, Union[str, Dict[str, Union[str, int]]]]] = None
    next_state: str = None  # ID of the next state
    transitions: Dict[str, str] = None  # Maps responses/choices to next state IDs

class NPC(Character):
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'NPC':
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)['npc']
        
        x, y = data['position']
        
        # Convert YAML sequence to state machine
        states = {}
        initial_state = None
        
        for i, action in enumerate(data['sequence']):
            state_id = f"state_{i}"
            next_state = f"state_{i + 1}" if i < len(data['sequence']) - 1 else "end"
            
            # Create state transitions based on action type
            transitions = {}
            if action['type'] == "Choice":
                for choice in action['choices']:
                    transitions[choice['choice_text']] = next_state
            elif action['type'] == "ask":
                transitions["*"] = next_state  # Any response transitions to next state
            else:
                transitions = None  # Auto-transition to next state
            
            states[state_id] = NPCState(
                **action,
                next_state=next_state,
                transitions=transitions
            )
            
            if i == 0:
                initial_state = state_id
        
        return cls(x, y, data['emoji'], states, initial_state, data['name'])

    def __init__(self, x: int, y: int, emoji: str='', states: Dict[str, NPCState] = None, 
                 initial_state: str = None, name: str = "Unknown"):
        super().__init__(x, y, emoji)
        self.states = states if states else {"start": NPCState(type="talk", text="...")}
        self.current_state_id = initial_state if initial_state else "start"
        self.is_talking = False
        self.name = name
        self.responses = {}  # Store player responses
        self.waiting_for_response = False

    def get_current_state(self) -> Optional[NPCState]:
        if self.current_state_id == "end":
            return None
        return self.states.get(self.current_state_id)

    def format_text(self, text: str) -> str:
        """Format text with stored responses"""
        try:
            return text.format(**self.responses)
        except KeyError:
            return text

    def provide_response(self, response: str, character: Character = None) -> None:
        """Handle a response from the player"""
        if not self.waiting_for_response:
            return

        current_state = self.get_current_state()
        if not current_state:
            return

        # Handle the response based on state type
        if current_state.type == "ask":
            self.responses[current_state.user_input] = response
            # Transition to next state using wildcard
            if current_state.transitions and "*" in current_state.transitions:
                self.current_state_id = current_state.transitions["*"]
        elif current_state.type == "Choice":
            # Check if response matches any of the choices
            if current_state.transitions and response in current_state.transitions:
                # Find the choice configuration
                choice = next(c for c in current_state.choices if c['choice_text'] == response)
                
                # Process the choice action
                if choice.get('type') == 'give' and choice.get('item') and character:
                    quantity = choice['item'].get('quantity', 1)
                    for _ in range(quantity):
                        character.add_item(choice['item']['name'])
                elif choice.get('action') == 'talk' and choice.get('text'):
                    self.talk(f"{self.name}: {choice['text']}")
                
                # Transition to next state
                self.current_state_id = current_state.transitions[response]

        self.waiting_for_response = False

    def interact(self, character: Character) -> None:
        if not self.is_talking:
            self.is_talking = True
            self.current_state_id = next(iter(self.states))  # Reset to initial state
        
        current_state = self.get_current_state()
        if not current_state:
            self.is_talking = False
            return

        if current_state.type == "talk":
            formatted_text = self.format_text(current_state.text)
            self.talk(f"{self.name}: {formatted_text}")
            # Auto-transition to next state
            self.current_state_id = current_state.next_state
        
        elif current_state.type == "give":
            if current_state.item:
                quantity = current_state.item.get('quantity', 1)
                for _ in range(quantity):
                    character.add_item(current_state.item['name'])
                if current_state.text:
                    self.talk(f"{self.name}: {current_state.text}")
            # Auto-transition to next state
            self.current_state_id = current_state.next_state
        
        elif current_state.type == "ask":
            self.talk(f"{self.name}: {current_state.text}")
            self.waiting_for_response = True
        
        elif current_state.type == "Choice":
            self.talk(f"{self.name}: {current_state.text}")
            self.waiting_for_response = True
        
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
                    
                    self.talk(f"{self.name}: {current_state.trade['success_text']}")
                else:
                    self.talk(f"{self.name}: {current_state.trade['failure_text']}")
                
                if current_state.text:
                    self.talk(f"{self.name}: {current_state.text}")
            # Auto-transition to next state
            self.current_state_id = current_state.next_state