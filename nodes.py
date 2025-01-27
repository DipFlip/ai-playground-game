"""
Node classes for handling different types of NPC conversation nodes
"""
from typing import Dict, List, Union, Optional
from character import Character
import logging
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class Node(ABC):
    def __init__(self, text: str = None):
        self.text = text
        self.next: Optional[Node] = None
    
    @abstractmethod
    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional['Node']:
        """Handle the node's action and return the next node"""
        pass

    @classmethod
    @abstractmethod
    def from_action(cls, action: dict) -> 'Node':
        """Create a node from action data"""
        pass

class EndNode(Node):
    """Special node that handles the end of a conversation"""
    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        logger.debug("Handling EndNode - closing conversation")
        npc.is_talking = False
        sequence.current_node = None
        return None

    @classmethod
    def from_action(cls, action: dict) -> 'Node':
        return cls()

class TalkNode(Node):
    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        logger.debug(f"Handling TalkNode with text: {self.text}")
        formatted_text = sequence.format_text(self.text)
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        npc.is_talking = True
        return self.next

    @classmethod
    def from_action(cls, action: dict) -> 'Node':
        return cls(action['text'])

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

    @classmethod
    def from_action(cls, action: dict) -> 'Node':
        return cls(action.get('text'), action.get('item'))

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

    @classmethod
    def from_action(cls, action: dict) -> 'Node':
        return cls(action['text'], action.get('user_input'))

class ChoiceNode(Node):
    def __init__(self, text: str):
        super().__init__(text)
        self.choices: Dict[str, Node] = {}  # Maps choice text to its node sequence

    def add_choice(self, choice_text: str, node: Node) -> None:
        """Add a choice and its corresponding node sequence"""
        self.choices[choice_text] = node

    def handle(self, npc: Character, character: Character, sequence: 'Sequence') -> Optional[Node]:
        formatted_text = sequence.format_text(self.text)
        message = f"{npc.name}: {formatted_text}"
        npc.talk(message)
        sequence.history.append({"role": "npc", "text": formatted_text})
        npc.is_talking = True
        sequence.waiting_for_response = True
        sequence.current_node = self
        return None

    @classmethod
    def from_action(cls, action: dict) -> 'Node':
        node = cls(action['text'])
        # Create nodes for each choice
        for choice in action['choices']:
            if 'type' in choice:
                # Create the node sequence for this choice
                choice_node = NodeFactory.create_node(choice)
                node.add_choice(choice['choice_text'], choice_node)
        return node

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

    @classmethod
    def from_action(cls, action: dict) -> 'Node':
        return cls(action.get('text'), action.get('context'))

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

    @classmethod
    def from_action(cls, action: dict) -> 'Node':
        return cls(action.get('text'), action.get('trade'))

class NodeFactory:
    """Factory class for creating nodes from action data"""
    _node_types = {
        'talk': TalkNode,
        'give': GiveNode,
        'ask': AskNode,
        'choice': ChoiceNode,
        'trade': TradeNode,
        'generate': GenerateNode,
        'end': EndNode
    }

    @classmethod
    def create_node(cls, action: dict) -> Node:
        """Create a node from action data"""
        node_type = action['type']
        if node_type not in cls._node_types:
            raise ValueError(f"Unknown node type: {node_type}")
        return cls._node_types[node_type].from_action(action) 