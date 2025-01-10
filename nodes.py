"""
Node classes for handling different types of NPC conversation nodes
"""
from typing import Dict, List, Union, Optional
from character import Character
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

class Node(ABC):
    def __init__(self, text: str = None):
        self.text = text
        self.next: Optional[Node] = None
    
    @abstractmethod
    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional['Node']:
        """Handle the node's action and return the next node"""
        pass

class EndNode(Node):
    """Special node that handles the end of a conversation"""
    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        logger.debug("Handling EndNode - closing conversation")
        npc.is_talking = False
        sequence.current_node = None
        return None

class TalkNode(Node):
    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        logger.debug(f"Handling TalkNode with text: {self.text}")
        formatted_text = sequence.format_text(self.text)
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        npc.is_talking = True
        return self.next

class GiveNode(Node):
    def __init__(self, text: str, item: Dict[str, Union[str, int]]):
        super().__init__(text)
        self.item = item

    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        logger.debug(f"Handling GiveNode with item: {self.item}")
        if self.text:
            formatted_text = sequence.format_text(self.text)
            message = f"{npc.name}: {formatted_text}"
            npc.talk(message)
            sequence.history.append({"role": "npc", "text": formatted_text})
            npc.is_talking = True

        if self.item:
            quantity = self.item.get('quantity', 1)
            for _ in range(quantity):
                character.add_item(self.item['name'])

        return self.next

class AskNode(Node):
    def __init__(self, text: str, user_input: str):
        super().__init__(text)
        self.user_input = user_input

    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        formatted_text = sequence.format_text(self.text)
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        sequence.waiting_for_response = True
        sequence.current_node = self  # Store current node while waiting for response
        return None

class ChoiceNode(Node):
    def __init__(self, text: str, choices: List[Dict[str, Union[str, Dict[str, Union[str, int]]]]]):
        super().__init__(text)
        self.choices = choices
        self.choice_nodes: Dict[str, Node] = {}

    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        formatted_text = sequence.format_text(self.text)
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        npc.is_talking = True
        sequence.waiting_for_response = True
        sequence.current_node = self  # Store current node while waiting for choice
        return None

class GenerateNode(Node):
    def __init__(self, text: str = None, context: str = None):
        super().__init__(text)
        self.context = context

    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        # Get the user's choice from the last interaction
        last_response = sequence.history[-1]['text'] if sequence.history and sequence.history[-1]['role'] == 'player' else None
        
        # Build context with the user's choice
        context = sequence.format_text(self.context) if self.context else "Continue the conversation naturally based on the history"
        if last_response:
            context = f"{context}\nUser chose: {last_response}"
        
        # Only include the initial greeting in history
        relevant_history = []
        if sequence.history:
            first_message = next((h for h in sequence.history if h['role'] == 'npc'), None)
            if first_message:
                relevant_history.append(first_message)
            if last_response:
                relevant_history.append({"role": "player", "text": last_response})
        
        history_text = "\n".join([f"{'NPC' if h['role'] == 'npc' else 'Player'}: {h['text']}" for h in relevant_history])
        context_with_history = f"{context}\nConversation history:\n{history_text}"
        
        from character_generator import create_sequence
        new_sequence = create_sequence(context_with_history)
        if new_sequence:
            sequence.history = relevant_history
            new_head = sequence._build_node_chain(new_sequence)
            return new_head
        return None

class TradeNode(Node):
    def __init__(self, text: str, trade: Dict[str, Union[Dict[str, Union[str, int]], str]]):
        super().__init__(text)
        self.trade = trade

    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        if not self.trade:
            return self.next

        if self.text:
            formatted_text = sequence.format_text(self.text)
            message = f"{npc.name}: {formatted_text}"
            npc.talk(message)
            sequence.history.append({"role": "npc", "text": formatted_text})
            npc.is_talking = True

        want = self.trade['want']
        offer = self.trade['offer']
        want_quantity = want.get('quantity', 1)
        
        has_items = character.has_item(want['name'], want_quantity)
        
        if has_items:
            self._process_successful_trade(want, offer, character)
            formatted_text = sequence.format_text(self.trade['success_text'])
        else:
            formatted_text = sequence.format_text(self.trade['failure_text'])
        
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        npc.is_talking = True
        
        return self.next

    def _process_successful_trade(self, want: dict, offer: dict, character: Character) -> None:
        want_quantity = want.get('quantity', 1)
        for _ in range(want_quantity):
            character.remove_item(want['name'])
        
        offer_quantity = offer.get('quantity', 1)
        for _ in range(offer_quantity):
            character.add_item(offer['name']) 