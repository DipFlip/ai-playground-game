"""
Sequence class for handling NPC conversations
"""
from dataclasses import dataclass
from typing import Dict, List, Union, Optional, Protocol
from character_generator import create_sequence
import yaml
from character import Character
import logging
from abc import ABC, abstractmethod

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

class StateHandler(ABC):
    @abstractmethod
    def handle(self, state: State, npc: Character, character: Character, sequence: 'Sequence') -> str:
        """Handle the state and return the next state ID"""
        pass

class TalkStateHandler(StateHandler):
    def handle(self, state: State, npc: Character, character: Character, sequence: 'Sequence') -> str:
        formatted_text = sequence.format_text(state.text)
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        npc.is_talking = True  # Set NPC to talking when showing message
        
        if not state.next_state:
            return "end"  # Don't set is_talking to False here, let the interaction system handle it
        return state.next_state

class GiveStateHandler(StateHandler):
    def handle(self, state: State, npc: Character, character: Character, sequence: 'Sequence') -> str:
        # Always show text if it exists, even if there's no item
        if state.text:
            formatted_text = sequence.format_text(state.text)
            message = f"{npc.name}: {formatted_text}"
            npc.talk(message)
            sequence.history.append({"role": "npc", "text": formatted_text})
            npc.is_talking = True  # Set NPC to talking when showing message

        # Handle item giving
        if state.item:
            quantity = state.item.get('quantity', 1)
            for _ in range(quantity):
                character.add_item(state.item['name'])

        # Handle state transition exactly like talk state
        if not state.next_state:
            return "end"  # Don't set is_talking to False here, let the interaction system handle it
        return state.next_state

class AskStateHandler(StateHandler):
    def handle(self, state: State, npc: Character, character: Character, sequence: 'Sequence') -> str:
        formatted_text = sequence.format_text(state.text)
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        sequence.waiting_for_response = True
        return None  # Wait for response

class ChoiceStateHandler(StateHandler):
    def handle(self, state: State, npc: Character, character: Character, sequence: 'Sequence') -> str:
        formatted_text = sequence.format_text(state.text)
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        npc.is_talking = True  # Keep NPC talking while waiting for choice
        sequence.waiting_for_response = True
        return None  # Wait for response

class GenerateStateHandler(StateHandler):
    def handle(self, state: State, npc: Character, character: Character, sequence: 'Sequence') -> str:
        """Handle generate state by creating a new sequence based on context"""
        # Get the user's choice from the last interaction
        last_response = sequence.history[-1]['text'] if sequence.history and sequence.history[-1]['role'] == 'player' else None
        
        # Build context with the user's choice
        context = sequence.format_text(state.context) if state.context else "Continue the conversation naturally based on the history"
        if last_response:
            context = f"{context}\nUser chose: {last_response}"
        
        # Only include the initial greeting in history, skip the choice/ask question
        relevant_history = []
        if sequence.history:
            # Include only the first greeting message and user's choice
            first_message = next((h for h in sequence.history if h['role'] == 'npc'), None)
            if first_message:
                relevant_history.append(first_message)
            if last_response:
                relevant_history.append({"role": "player", "text": last_response})
        
        history_text = "\n".join([f"{'NPC' if h['role'] == 'npc' else 'Player'}: {h['text']}" for h in relevant_history])
        context_with_history = f"{context}\nConversation history:\n{history_text}"
        
        new_sequence = create_sequence(context_with_history)
        if new_sequence:
            # Clear the history to prevent message repetition
            sequence.history = relevant_history
            # Process the new sequence and get its start state
            sequence_start, _ = sequence._process_sequence(new_sequence, len(sequence.states))
            return sequence_start
        return "end"

class TradeStateHandler(StateHandler):
    def handle(self, state: State, npc: Character, character: Character, sequence: 'Sequence') -> str:
        if not state.trade:
            if not state.next_state:
                return "end"
            return state.next_state

        # Show initial text if it exists
        if state.text:
            formatted_text = sequence.format_text(state.text)
            message = f"{npc.name}: {formatted_text}"
            npc.talk(message)
            sequence.history.append({"role": "npc", "text": formatted_text})
            npc.is_talking = True

        want = state.trade['want']
        offer = state.trade['offer']
        want_quantity = want.get('quantity', 1)
        
        has_items = character.has_item(want['name'], want_quantity)
        
        if has_items:
            self._process_successful_trade(want, offer, character)
            formatted_text = sequence.format_text(state.trade['success_text'])
        else:
            formatted_text = sequence.format_text(state.trade['failure_text'])
        
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        npc.is_talking = True  # Keep NPC talking to show the trade result
        
        if not state.next_state:
            return "end"  # Don't set is_talking to False here, let the interaction system handle it
        return state.next_state

    def _process_successful_trade(self, want: dict, offer: dict, character: Character) -> None:
        want_quantity = want.get('quantity', 1)
        for _ in range(want_quantity):
            character.remove_item(want['name'])
        
        offer_quantity = offer.get('quantity', 1)
        for _ in range(offer_quantity):
            character.add_item(offer['name'])

class Sequence:
    def __init__(self, sequence_data: List[dict]):
        self.states = {}
        self.initial_state = None
        self.current_state_id = None
        self.responses = {}  # Store player responses
        self.waiting_for_response = False
        self.history = []  # List to store conversation history
        self._state_handlers = {
            'talk': TalkStateHandler(),
            'give': GiveStateHandler(),
            'ask': AskStateHandler(),
            'choice': ChoiceStateHandler(),
            'trade': TradeStateHandler(),
            'generate': GenerateStateHandler(),
        }
        self._build_state_machine(sequence_data)
    
    def interact(self, npc: Character, character: Character) -> None:
        """Handle interaction between an NPC and a character"""
        current_state = self.get_current_state()
        if not current_state:
            npc.is_talking = False
            return

        handler = self._state_handlers.get(current_state.type)
        if handler:
            next_state = handler.handle(current_state, npc, character, self)
            if next_state == "end":
                self.current_state_id = None
            elif next_state is not None:  # None means waiting for response
                self.current_state_id = next_state

    def _process_sequence(self, sequence_data: List[dict], state_counter: int = 0) -> tuple[str, int]:
        """Process a sequence and return the start state ID and the next state counter"""
        if not sequence_data:
            return None, state_counter

        sequence_start = f"state_{state_counter}"
        state_counter += 1

        for i, action in enumerate(sequence_data):
            state_id = sequence_start if i == 0 else f"state_{state_counter}"
            next_state_id = f"state_{state_counter + 1}" if i < len(sequence_data) - 1 else None
            
            state = self._create_state(action, next_state_id)
            self.states[state_id] = state

            if action['type'] == 'choice':
                state_counter = self._process_choices(action, state, state_counter, next_state_id)
            
            state_counter += 1

        return sequence_start, state_counter

    def _create_state(self, action: dict, next_state_id: Optional[str]) -> State:
        """Create a state from action data"""
        state_data = {
            'type': action['type'],
            'text': action.get('text'),
            'user_input': action.get('user_input'),
            'item': action.get('item'),
            'trade': action.get('trade'),
            'choices': action.get('choices'),
            'context': action.get('context'),
            'next_state': next_state_id,
            'transitions': {} if action['type'] != 'choice' else None
        }
        return State(**state_data)

    def _process_choices(self, action: dict, state: State, state_counter: int, next_state_id: Optional[str]) -> int:
        """Process choices for a choice state"""
        transitions = {}
        for choice in action['choices']:
            if 'sequence' in choice:
                choice_start, new_counter = self._process_sequence(choice['sequence'], state_counter + 1)
                transitions[choice['choice_text']] = choice_start
                state_counter = new_counter
            else:
                # Create a state for this choice if it has a type
                if 'type' in choice:
                    choice_state = f"state_{state_counter + 1}"
                    state_counter += 1
                    # Create action data from the choice
                    action_data = {
                        'type': choice['type'],
                        'text': choice.get('text'),
                        'context': choice.get('context', f"Continue the conversation about {choice['choice_text'].lower()}")
                    }
                    self.states[choice_state] = self._create_state(action_data, None)
                    transitions[choice['choice_text']] = choice_state
                else:
                    # If choice has no sequence and no specific action, transition to next state
                    transitions[choice['choice_text']] = next_state_id
        state.transitions = transitions
        return state_counter

    def _build_state_machine(self, sequence: List[dict]) -> None:
        """Convert sequence data into a state machine"""
        sequence_start, _ = self._process_sequence(sequence)
        self.initial_state = sequence_start
        self.current_state_id = self.initial_state

    def get_current_state(self) -> Optional[State]:
        """Get the current state or None if ended"""
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

    def provide_response(self, response: str) -> None:
        """Handle a response from the player"""
        if not self.waiting_for_response:
            return

        current_state = self.get_current_state()
        if not current_state:
            return

        self.history.append({"role": "player", "text": response})
        self.waiting_for_response = False

        next_state = None
        if current_state.type == "ask":
            if current_state.user_input:
                self.responses[current_state.user_input] = response
            next_state = current_state.next_state
            # Handle generate state after ask the same way as after choice
            if next_state:
                next_state_obj = self.states.get(next_state)
                if next_state_obj and next_state_obj.type == "generate":
                    handler = self._state_handlers.get('generate')
                    if handler:
                        next_state = handler.handle(next_state_obj, None, None, self)
                        if next_state == "end":
                            self.current_state_id = None
                        else:
                            self.current_state_id = next_state
                        return
                self.current_state_id = next_state
                return  # Let the next interaction handle other state types
        elif current_state.type == "choice":
            next_state = current_state.transitions.get(response)
            if next_state:
                # Get the next state object
                next_state_obj = self.states.get(next_state)
                if next_state_obj and next_state_obj.type == "generate":
                    # For generate states, we want to process them immediately
                    handler = self._state_handlers.get('generate')
                    if handler:
                        next_state = handler.handle(next_state_obj, None, None, self)
                        if next_state == "end":
                            self.current_state_id = None
                        else:
                            self.current_state_id = next_state
                        return
                self.current_state_id = next_state
                return  # Let the next interaction handle other state types

        # Only end the conversation if there's no next state
        if not next_state:
            self.current_state_id = None
        else:
            self.current_state_id = next_state

    def reset(self) -> None:
        """Reset the sequence to its initial state"""
        self.current_state_id = self.initial_state
        self.responses = {}
        self.waiting_for_response = False
        self.history = []

    @classmethod
    def from_yaml(cls, sequence_data: List[dict]) -> 'Sequence':
        """Create a sequence from YAML data"""
        return cls(sequence_data) 