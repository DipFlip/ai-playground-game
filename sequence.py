"""
Sequence class for handling NPC conversations
"""
from dataclasses import dataclass
from typing import Dict, List, Union, Optional
from character_generator import create_sequence
import yaml
from character import Character
import logging

logger = logging.getLogger(__name__)

@dataclass
class State:
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
    context: str = None  # For generate type - template for new sequence

class Sequence:
    def __init__(self, sequence_data: List[dict]):
        self.states = {}
        self.initial_state = None
        self.current_state_id = None
        self.responses = {}  # Store player responses
        self.waiting_for_response = False
        self.history = []  # List to store conversation history
        self._build_state_machine(sequence_data)
        
    def interact(self, npc: 'Character', character: Character) -> None:
        """Handle interaction between an NPC and a character"""
        current_state = self.get_current_state()
        if not current_state:
            npc.is_talking = False
            return

        if current_state.type == "talk":
            formatted_text = self.format_text(current_state.text)
            message = f"{npc.name}: {formatted_text}"
            npc.talk(message)
            self.history.append({"role": "npc", "text": formatted_text})
            # Auto-transition to next state
            self.current_state_id = current_state.next_state
        
        elif current_state.type == "give":
            if current_state.item:
                quantity = current_state.item.get('quantity', 1)
                for _ in range(quantity):
                    character.add_item(current_state.item['name'])
                if current_state.text:
                    formatted_text = self.format_text(current_state.text)
                    message = f"{npc.name}: {formatted_text}"
                    npc.talk(message)
                    self.history.append({"role": "npc", "text": formatted_text})
            # Auto-transition to next state
            self.current_state_id = current_state.next_state
        
        elif current_state.type == "ask":
            formatted_text = self.format_text(current_state.text)
            message = f"{npc.name}: {formatted_text}"
            npc.talk(message)
            self.history.append({"role": "npc", "text": formatted_text})
            self.waiting_for_response = True
        
        elif current_state.type == "choice":
            formatted_text = self.format_text(current_state.text)
            message = f"{npc.name}: {formatted_text}"
            npc.talk(message)
            self.history.append({"role": "npc", "text": formatted_text})
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
                    message = f"{npc.name}: {formatted_text}"
                    npc.talk(message)
                    self.history.append({"role": "npc", "text": formatted_text})
                else:
                    formatted_text = self.format_text(current_state.trade['failure_text'])
                    message = f"{npc.name}: {formatted_text}"
                    npc.talk(message)
                    self.history.append({"role": "npc", "text": formatted_text})
                
                if current_state.text:
                    formatted_text = self.format_text(current_state.text)
                    message = f"{npc.name}: {formatted_text}"
                    npc.talk(message)
                    self.history.append({"role": "npc", "text": formatted_text})
            # Auto-transition to next state
            self.current_state_id = current_state.next_state

    def _process_sequence(self, sequence_data: List[dict], state_counter: int = 0) -> tuple[str, int]:
        """Process a sequence and return the start state ID and the next state counter"""
        sequence_start = None
        last_state = None
        states_to_process = []

        # First pass: create all states
        for action in sequence_data:
            state_id = f"state_{state_counter}"
            state_counter += 1

            if sequence_start is None:
                sequence_start = state_id
            
            # Create state transitions based on action type
            transitions = {}
            next_state = None

            if action['type'] == "choice":
                # For each choice, process its sequence and link to it
                choice_transitions = {}
                for choice in action['choices']:
                    if 'sequence' in choice:
                        # Process the choice's sequence and get its start state
                        choice_start, state_counter = self._process_sequence(choice['sequence'], state_counter)
                        choice_transitions[choice['choice_text']] = choice_start
                    elif len(choice) == 1 and 'choice_text' in choice:
                        # If choice only has choice_text, mark it for later linking
                        choice_transitions[choice['choice_text']] = "NEXT_STATE"
                    else:
                        # Create a single state for this choice's action
                        choice_state = f"state_{state_counter}"
                        state_counter += 1
                        # Remove choice-specific keys and keep action data
                        action_data = {k: v for k, v in choice.items() if k not in ['choice_text', 'sequence']}
                        self.states[choice_state] = State(**action_data, next_state="NEXT_STATE")
                        choice_transitions[choice['choice_text']] = choice_state
                transitions = choice_transitions
            elif action['type'] == "ask":
                next_state = f"state_{state_counter}"  # Next state will be the next one we create
                transitions["*"] = next_state
            
            # Create the state with all fields from the action
            state_data = {
                'type': action['type'],
                'text': action.get('text'),
                'user_input': action.get('user_input'),
                'item': action.get('item'),
                'trade': action.get('trade'),
                'choices': action.get('choices'),
                'context': action.get('context'),
                'next_state': next_state,
                'transitions': transitions
            }
            self.states[state_id] = State(**state_data)
            states_to_process.append((state_id, action))

            if last_state and self.states[last_state].next_state is None:
                self.states[last_state].next_state = state_id

            last_state = state_id

        # Second pass: link states to their next states
        for i, (state_id, action) in enumerate(states_to_process):
            next_state_id = states_to_process[i + 1][0] if i + 1 < len(states_to_process) else None
            state = self.states[state_id]

            # Link simple choices to next state
            if action['type'] == "choice" and state.transitions:
                for choice_text, transition in state.transitions.items():
                    if transition == "NEXT_STATE":
                        state.transitions[choice_text] = next_state_id
            
            # Link choice action states to next state
            for choice_state_id in state.transitions.values():
                if choice_state_id != "NEXT_STATE":
                    choice_state = self.states.get(choice_state_id)
                    if choice_state and choice_state.next_state == "NEXT_STATE":
                        choice_state.next_state = next_state_id

        return sequence_start, state_counter

    def _build_state_machine(self, sequence: List[dict]) -> None:
        """Convert sequence data into a state machine"""
        sequence_start, _ = self._process_sequence(sequence)
        self.initial_state = sequence_start
        self.current_state_id = self.initial_state

    def _process_generate_state(self, state: State) -> None:
        """Process a generate state and create a new sequence"""
        context = self.format_text(state.context) if state.context else "Continue the conversation naturally based on the history"
        history_text = "\n".join([f"{'NPC' if h['role'] == 'npc' else 'Player'}: {h['text']}" for h in self.history])
        context_with_history = f"{context}\nConversation history:\n{history_text}"
        new_sequence = create_sequence(context_with_history)
        if new_sequence:
            sequence_start, _ = self._process_sequence(new_sequence, len(self.states))
            self.current_state_id = sequence_start

    def get_current_state(self) -> Optional[State]:
        """Get the current state or None if ended"""
        if self.current_state_id == "end":
            return None
        state = self.states.get(self.current_state_id)
        if state:
            # Set waiting_for_response based on state type - only for states that need input
            self.waiting_for_response = state.type in ["ask", "choice"]
        return state

    def format_text(self, text: str) -> str:
        """Format text with stored responses"""
        if not text:
            return text
        try:
            return text.format(**self.responses)
        except KeyError:
            return text

    def provide_response(self, response: str) -> None:
        """Handle a response from the player"""
        if not self.waiting_for_response:
            return

        current_state = self.get_current_state()
        if not current_state:
            return

        # Add player's response to history
        self.history.append({"role": "player", "text": response})

        # Handle the response based on state type
        if current_state.type == "ask":
            if current_state.user_input:
                self.responses[current_state.user_input] = response
            # Move to next state
            next_state = None
            if current_state.transitions and "*" in current_state.transitions:
                next_state = current_state.transitions["*"]
            else:
                next_state = current_state.next_state
            
            # If next state is generate, process it
            next_state_obj = self.states.get(next_state)
            if next_state_obj and next_state_obj.type == "generate":
                self.current_state_id = next_state
                self._process_generate_state(next_state_obj)
            else:
                # Normal transition for non-generate states
                self.current_state_id = next_state

        elif current_state.type == "choice":
            # Check if response matches any of the choices
            if current_state.transitions and response in current_state.transitions:
                next_state = current_state.transitions[response]
                # Check if next state is generate
                next_state_obj = self.states.get(next_state)
                if next_state_obj and next_state_obj.type == "generate":
                    self.current_state_id = next_state
                    self._process_generate_state(next_state_obj)
                else:
                    # Normal transition for non-generate states
                    self.current_state_id = next_state
            else:
                # If invalid choice, stay in current state
                return

        # Update waiting_for_response based on new state
        self.get_current_state()

    def reset(self) -> None:
        """Reset sequence to initial state"""
        self.current_state_id = self.initial_state
        self.waiting_for_response = False
        self.responses = {}
        self.history = []  # Clear conversation history

    @classmethod
    def from_yaml(cls, sequence_data: List[dict]) -> 'Sequence':
        """Create a Sequence from YAML data"""
        return cls(sequence_data) 