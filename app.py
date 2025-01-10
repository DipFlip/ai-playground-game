from flask import Flask, render_template, jsonify, request, send_file
from world import World, DYNAMIC_NPCS, NPC_POSITIONS, PLAYER_STATE
from npc import NPC
import os
from character_generator import create_character
import yaml
import uuid
import json
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Union

# Configure logging
logging.basicConfig(level=logging.INFO)
# Reduce Werkzeug logger verbosity
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)

@dataclass
class GameState:
    """Class to manage game state"""
    player: Dict[str, Any]
    npc_positions: Dict[str, Dict[str, int]]
    dynamic_npcs: List[Dict[str, Any]]
    interaction: Optional[Dict[str, Any]] = None

    @classmethod
    def from_request(cls, request_data: Dict[str, Any]) -> Optional['GameState']:
        """Create GameState from request data"""
        if not request_data.get('savedState'):
            return None
        
        saved_state = request_data['savedState']
        return cls(
            player=saved_state.get('player', {}),
            npc_positions=saved_state.get('npcPositions', {}),
            dynamic_npcs=saved_state.get('dynamicNpcs', []),
            interaction=saved_state.get('interaction')
        )

    def apply_to_world(self, world: World) -> None:
        """Apply state to game world"""
        if self.player:
            PLAYER_STATE.update(self.player)
            world.character.x = self.player['x']
            world.character.y = self.player['y']
        
        if self.npc_positions:
            NPC_POSITIONS.update(self.npc_positions)
            self._sync_npc_positions(world)
        
        if self.dynamic_npcs:
            DYNAMIC_NPCS.clear()
            DYNAMIC_NPCS.extend(self.dynamic_npcs)

    def _sync_npc_positions(self, world: World) -> None:
        """Sync NPC positions with saved state"""
        for location in world.locations:
            if not isinstance(location, NPC):
                continue
            
            npc_id = self._find_npc_id(location)
            if npc_id and npc_id in self.npc_positions:
                location.x = self.npc_positions[npc_id]['x']
                location.y = self.npc_positions[npc_id]['y']

    def _find_npc_id(self, npc: NPC) -> Optional[str]:
        """Find NPC ID in positions"""
        return next((
            id for id in self.npc_positions.keys()
            if (isinstance(id, str) and id.startswith('dynamic_') and npc.name == f'dynamic_{id.split("_")[1]}')
            or (npc.name == id.replace('.yaml', ''))
        ), None)

class GameStateBuilder:
    """Builder for game state responses"""
    def __init__(self, world: World):
        self.world = world

    def build_state(self) -> Dict[str, Any]:
        """Build current game state"""
        state = {
            'player': self._build_player_state(),
            'npcPositions': NPC_POSITIONS,
            'dynamicNpcs': DYNAMIC_NPCS,
        }

        if self.world.current_interaction:
            state['interaction'] = self._build_interaction_state()

        return state

    def _build_player_state(self) -> Dict[str, Any]:
        """Build player state"""
        return {
            'x': self.world.character.x,
            'y': self.world.character.y,
            'inventory': self.world.character.inventory
        }

    def _build_interaction_state(self) -> Dict[str, Any]:
        """Build interaction state"""
        interaction = self.world.current_interaction
        return {
            'name': interaction.name,
            'is_talking': interaction.is_talking,
            'waiting_for_response': interaction.waiting_for_response,
            'sequence_state': {
                'current_state_id': interaction.sequence.current_state_id,
                'responses': interaction.sequence.responses
            }
        }

def create_state_response(world: World, response_data: Dict[str, Any]) -> Any:
    """Create response with current game state"""
    state_builder = GameStateBuilder(world)
    response_data['gameState'] = state_builder.build_state()
    return jsonify(response_data)

# Create a global world instance
game_world = World()
game_messages = []

@app.route('/')
def home():
    return render_template('game.html', 
                         character=game_world.character,
                         locations=game_world.locations,
                         messages=game_messages)

@app.route('/move', methods=['POST'])
def move():
    # Load and apply saved state
    if state := GameState.from_request(request.json):
        state.apply_to_world(game_world)
    
    # Don't allow movement during interaction
    if game_world.is_interaction_active():
        return create_state_response(game_world, {
            'x': game_world.character.x,
            'y': game_world.character.y,
            'inventory': game_world.character.inventory,
            'emoji': game_world.character.emoji,
            'canMove': False
        })

    # Process movement
    direction = request.json['direction']
    dx, dy = {
        'north': (0, -1),
        'south': (0, 1),
        'east': (1, 0),
        'west': (-1, 0)
    }[direction]
    
    new_x = game_world.character.x + dx
    new_y = game_world.character.y + dy
    
    if game_world.can_move_to(new_x, new_y):
        game_world.character.move(dx, dy)
    
    return create_state_response(game_world, {
        'x': game_world.character.x,
        'y': game_world.character.y,
        'inventory': game_world.character.inventory,
        'emoji': game_world.character.emoji,
        'canMove': True
    })

@app.route('/game_state', methods=['GET', 'POST'])
def game_state():
    # Load and apply saved state
    if request.is_json:
        if state := GameState.from_request(request.json):
            state.apply_to_world(game_world)
    
    # Update NPCs
    game_world.update_npcs()
    
    return create_state_response(game_world, {
        'character': {
            'x': game_world.character.x,
            'y': game_world.character.y,
            'emoji': game_world.character.emoji
        },
        'locations': [{
            'x': loc.x,
            'y': loc.y,
            'emoji': loc.emoji,
            'type': loc.__class__.__name__,
            'name': getattr(loc, 'name', None)
        } for loc in game_world.locations]
    })

@app.route('/graphics/<path:filename>')
def serve_graphic(filename):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return send_file(os.path.join(base_path, 'graphics', filename))

@app.route('/sounds/<path:filename>')
def serve_sound(filename):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return send_file(os.path.join(base_path, 'sounds', filename))

@app.route('/static/<path:filename>')
def serve_static(filename):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return send_file(os.path.join(base_path, 'static', filename))

class InteractionHandler:
    """Handler for NPC interactions"""
    def __init__(self, world: World, messages: List[str]):
        self.world = world
        self.messages = messages

    def handle_interaction(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle an interaction request"""
        # Capture print output
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = output = io.StringIO()

        if 'answer' in request_data:
            self._process_answer(request_data['answer'])

        result = self.world.try_interact()
        
        # Get the printed message
        sys.stdout = old_stdout
        message = output.getvalue().strip()
        
        current_npc = self.world.current_interaction
        self._update_messages(message, current_npc)
        
        return self._create_response(result, message, current_npc)

    def _process_answer(self, answer: Union[str, Dict[str, str]]) -> None:
        """Process player's answer"""
        npc = self.world.current_interaction
        if not npc:
            return

        # Extract text from answer if it's a dict
        if isinstance(answer, dict) and 'text' in answer:
            answer = answer['text']
        npc.provide_response(answer, self.world.character)

    def _update_messages(self, message: str, current_npc: Optional[NPC]) -> None:
        """Update game messages"""
        if message:
            self.messages.append(message)
            if len(self.messages) > 5:
                self.messages.pop(0)
        
        # Clear messages if interaction is over
        if not current_npc or not current_npc.is_talking:
            self.messages.clear()

    def _create_response(self, result: bool, message: str, current_npc: Optional[NPC]) -> Dict[str, Any]:
        """Create interaction response"""
        waiting_for_input = False
        choices = []
        
        if current_npc and current_npc.waiting_for_response:
            waiting_for_input = True
            current_state = current_npc.get_current_state()
            if current_state and current_state.type == "choice" and current_state.choices:
                choices = [choice['choice_text'] for choice in current_state.choices]
        
        return {
            'success': result,
            'message': message,
            'inventory': self.world.character.inventory,
            'messages': self.messages,
            'waitingForInput': waiting_for_input,
            'choices': choices,
            'is_talking': current_npc.is_talking if current_npc else False
        }

@app.route('/interact', methods=['POST'])
def interact():
    # Load and apply saved state
    if state := GameState.from_request(request.json):
        state.apply_to_world(game_world)
    
    # Handle interaction
    handler = InteractionHandler(game_world, game_messages)
    response = handler.handle_interaction(request.json)
    
    return create_state_response(game_world, response)

@app.route('/create_npc', methods=['POST'])
def create_npc():
    try:
        description = request.json['description']
        npc_data = create_character(description)
        
        # Generate unique ID for the NPC
        npc_id = str(uuid.uuid4())
        npc_filename = f'dynamic_{npc_id}.yaml'
        
        # Save NPC data
        npc_path = os.path.join('npcs', npc_filename)
        with open(npc_path, 'w') as f:
            yaml.dump(npc_data, f)
        
        # Add to dynamic NPCs list
        DYNAMIC_NPCS.append({
            'id': npc_id,
            'x': request.json.get('x', 0),
            'y': request.json.get('y', 0)
        })
        
        return jsonify({'success': True, 'message': 'NPC created successfully'})
    except Exception as e:
        logging.error(f"Error creating NPC: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/reset_game', methods=['POST'])
def reset_game():
    game_world.reset()
    game_messages.clear()
    return jsonify({'success': True})

if __name__ == '__main__':
    app.run(debug=True) 