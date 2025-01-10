"""
Sequence class for handling NPC conversations using a linked list structure
"""
from dataclasses import dataclass
from typing import Dict, List, Union, Optional
from character_generator import create_sequence
import yaml
from character import Character
import logging
from nodes import Node, EndNode, TalkNode, GiveNode, AskNode, ChoiceNode, GenerateNode, TradeNode

logger = logging.getLogger(__name__)

class Sequence:
    def __init__(self, sequence_data: List[dict]):
        self.head: Optional[Node] = None
        self.current_node: Optional[Node] = None
        self.waiting_for_response = False
        self.responses = {}  # Store player responses
        self.history = []  # Store conversation history
        self._build_sequence(sequence_data)
    
    def _build_sequence(self, sequence_data: List[dict]) -> None:
        """Build the linked list sequence from sequence data"""
        if not sequence_data:
            return

        self.head = self._build_node_chain(sequence_data)
        self.current_node = self.head

    def _build_node_chain(self, sequence_data: List[dict]) -> Optional[Node]:
        """Build a chain of nodes from sequence data and return the head"""
        if not sequence_data:
            return None

        # Create the first node
        head = self._create_node(sequence_data[0])
        current = head

        # Create and link the rest of the nodes
        for action in sequence_data[1:]:
            next_node = self._create_node(action)
            current.next = next_node
            current = next_node

        # Always append an EndNode as the last node
        end_node = EndNode()
        current.next = end_node
        logger.debug("Added EndNode as the final node in sequence")

        return head

    def _create_node(self, action: dict) -> Node:
        """Create a node based on the action type"""
        node_type = action['type']
        if node_type == 'talk':
            return TalkNode(action['text'])
        elif node_type == 'give':
            return GiveNode(action.get('text'), action.get('item'))
        elif node_type == 'ask':
            return AskNode(action['text'], action.get('user_input'))
        elif node_type == 'choice':
            node = ChoiceNode(action['text'], action['choices'])
            # Create nodes for each choice
            for choice in action['choices']:
                if 'type' in choice:
                    choice_action = {
                        'type': choice['type'],
                        'text': choice.get('text'),
                        'item': choice.get('item')
                    }
                    choice_node = self._create_node(choice_action)
                    node.choice_nodes[choice['choice_text']] = choice_node
            return node
        elif node_type == 'trade':
            return TradeNode(action.get('text'), action.get('trade'))
        elif node_type == 'generate':
            return GenerateNode(action.get('text'), action.get('context'))
        else:
            raise ValueError(f"Unknown node type: {node_type}")

    def interact(self, npc: Character, character: Character) -> None:
        """Handle interaction between an NPC and a character"""
        if not self.current_node:
            logger.debug("No current node, ending conversation")
            npc.is_talking = False
            return

        logger.debug(f"Current node before handling: {self.current_node.__class__.__name__}")
        next_node = self.current_node.handle(npc, character, self)
        logger.debug(f"Next node after handling: {next_node.__class__.__name__ if next_node else None}")
        
        if next_node is not None:  # None means waiting for response
            logger.debug(f"Setting current node to: {next_node.__class__.__name__ if next_node else None}")
            self.current_node = next_node

    def provide_response(self, response: str) -> None:
        """Handle a response from the player"""
        if not self.waiting_for_response or not self.current_node:
            return

        self.history.append({"role": "player", "text": response})
        self.waiting_for_response = False

        if isinstance(self.current_node, AskNode):
            if self.current_node.user_input:
                self.responses[self.current_node.user_input] = response
            self.current_node = self.current_node.next
        elif isinstance(self.current_node, ChoiceNode):
            next_node = self.current_node.choice_nodes.get(response)
            if next_node:
                # Follow the choice node's chain until the end
                while next_node.next:
                    next_node = next_node.next
                # Link back to the main sequence
                next_node.next = self.current_node.next
                self.current_node = next_node
            else:
                # If choice not found, continue with next node
                self.current_node = self.current_node.next

    def format_text(self, text: str) -> str:
        """Format text with stored responses"""
        if not text:
            return text
        try:
            return text.format(**self.responses)
        except KeyError:
            return text

    def reset(self) -> None:
        """Reset the sequence to its initial state"""
        self.current_node = self.head
        self.responses = {}
        self.waiting_for_response = False
        self.history = []

    @classmethod
    def from_yaml(cls, sequence_data: List[dict]) -> 'Sequence':
        """Create a sequence from YAML data"""
        return cls(sequence_data) 