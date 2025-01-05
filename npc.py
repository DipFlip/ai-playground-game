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
    success_text: str = None  # For trade success message
    failure_text: str = None  # For trade failure message

class NPC(Character):
    @classmethod
    def from_yaml(cls, yaml_path: str) -> 'NPC':
        with open(yaml_path, 'r') as f:
            data = yaml.safe_load(f)['npc']
        
        # Get position from data or let the world decide later
        position = data.get('position', None)
        x, y = position if position else (0, 0)
        
        # Convert YAML sequence to state machine
        states = {}
        initial_state = None
        state_counter = 0

        def process_sequence(sequence, parent_state=None):
            nonlocal state_counter, initial_state
            sequence_start = None
            last_state = None

            for action in sequence:
                state_id = f"state_{state_counter}"
                state_counter += 1

                if sequence_start is None:
                    sequence_start = state_id
                
                # Create state transitions based on action type
                transitions = {}
                next_state = None

                if action['type'] == "Choice":
                    # For each choice, process its sequence and link to it
                    choice_transitions = {}
                    for choice in action['choices']:
                        if 'sequence' in choice:
                            # Process the choice's sequence and get its start state
                            choice_start = process_sequence(choice['sequence'], state_id)
                            choice_transitions[choice['choice_text']] = choice_start
                    transitions = choice_transitions
                elif action['type'] == "ask":
                    next_state = f"state_{state_counter}"  # Next state will be the next one we create
                    transitions["*"] = next_state
                
                states[state_id] = NPCState(
                    **action,
                    next_state=next_state,
                    transitions=transitions
                )

                if last_state and states[last_state].next_state is None:
                    states[last_state].next_state = state_id

                if initial_state is None:
                    initial_state = state_id

                last_state = state_id

            return sequence_start

        process_sequence(data['sequence'])
        
        npc = cls(x, y, data['emoji'], states, initial_state, data['name'])
        npc.needs_position = position is None
        return npc

    def __init__(self, x: int, y: int, emoji: str='', states: Dict[str, NPCState] = None, 
                 initial_state: str = None, name: str = "Unknown"):
        super().__init__(x, y, emoji)
        self.states = states if states else {"start": NPCState(type="talk", text="...")}
        self.current_state_id = initial_state if initial_state else "start"
        self.is_talking = False
        self.name = name
        self.responses = {}  # Store player responses
        self.waiting_for_response = False
        self.needs_position = False  # Flag to indicate if we need a position from the world

    def get_current_state(self) -> Optional[NPCState]:
        if self.current_state_id == "end":
            return None
        return self.states.get(self.current_state_id)

    def format_text(self, text: str) -> str:
        """Format text with stored responses"""
        if not text:
            return text
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
            if current_state.user_input:
                self.responses[current_state.user_input] = response
            # Transition to next state using wildcard
            if current_state.transitions and "*" in current_state.transitions:
                self.current_state_id = current_state.transitions["*"]
            else:
                self.current_state_id = current_state.next_state
        elif current_state.type == "Choice":
            # Check if response matches any of the choices
            if current_state.transitions and response in current_state.transitions:
                # Transition to next state based on choice
                self.current_state_id = current_state.transitions[response]

        self.waiting_for_response = False

    def interact(self, character: Character) -> None:
        if not self.is_talking:
            self.is_talking = True
            self.current_state_id = next(iter(self.states))  # Reset to initial state
            self.responses = {}  # Clear stored responses when starting new conversation
        
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
                    formatted_text = self.format_text(current_state.text)
                    self.talk(f"{self.name}: {formatted_text}")
            # Auto-transition to next state
            self.current_state_id = current_state.next_state
        
        elif current_state.type == "ask":
            formatted_text = self.format_text(current_state.text)
            self.talk(f"{self.name}: {formatted_text}")
            self.waiting_for_response = True
        
        elif current_state.type == "Choice":
            formatted_text = self.format_text(current_state.text)
            self.talk(f"{self.name}: {formatted_text}")
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
                    
                    formatted_text = self.format_text(current_state.trade['success_text'])
                    self.talk(f"{self.name}: {formatted_text}")
                else:
                    formatted_text = self.format_text(current_state.trade['failure_text'])
                    self.talk(f"{self.name}: {formatted_text}")
                
                if current_state.text:
                    formatted_text = self.format_text(current_state.text)
                    self.talk(f"{self.name}: {formatted_text}")
            # Auto-transition to next state
            self.current_state_id = current_state.next_state