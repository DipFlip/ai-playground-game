from flask import Flask, render_template, jsonify, request, send_file, session
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
from sequence import ChoiceNode

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Reduce Werkzeug logger verbosity
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', os.urandom(24))  # Required for sessions

# Dictionary to store game worlds for each session
game_worlds = {}
game_messages = {}

def get_player_world():
    """Get or create a game world for the current session"""
    session_id = session.get('session_id')
    if not session_id:
        session_id = str(uuid.uuid4())
        session['session_id'] = session_id
    
    if session_id not in game_worlds:
        game_worlds[session_id] = World()
        game_messages[session_id] = []
    
    return game_worlds[session_id], game_messages[session_id]

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
        current_node = interaction.sequence.current_node
        return {
            'name': interaction.name,
            'is_talking': interaction.is_talking,
            'waiting_for_response': interaction.waiting_for_response,
            'sequence_state': {
                'node_type': current_node.__class__.__name__ if current_node else None,
                'responses': interaction.sequence.responses
            }
        }

def create_state_response(world: World, response_data: Dict[str, Any]) -> Any:
    """Create response with current game state"""
    state_builder = GameStateBuilder(world)
    response_data['gameState'] = state_builder.build_state()
    return jsonify(response_data)

@app.route('/')
def home():
    world, messages = get_player_world()
    return render_template('game.html', 
                         character=world.character,
                         locations=world.locations,
                         messages=messages)

@app.route('/move', methods=['POST'])
def move():
    world, _ = get_player_world()
    
    # Load and apply saved state
    if state := GameState.from_request(request.json):
        state.apply_to_world(world)
    
    # Don't allow movement during interaction
    if world.is_interaction_active():
        return create_state_response(world, {
            'x': world.character.x,
            'y': world.character.y,
            'inventory': world.character.inventory,
            'emoji': world.character.emoji,
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
    
    new_x = world.character.x + dx
    new_y = world.character.y + dy
    
    if world.can_move_to(new_x, new_y):
        world.character.move(dx, dy)
    
    return create_state_response(world, {
        'x': world.character.x,
        'y': world.character.y,
        'inventory': world.character.inventory,
        'emoji': world.character.emoji,
        'canMove': True
    })

@app.route('/game_state', methods=['GET', 'POST'])
def game_state():
    world, _ = get_player_world()
    
    # Load and apply saved state
    if request.is_json:
        if state := GameState.from_request(request.json):
            state.apply_to_world(world)
    
    # Update NPCs
    world.update_npcs()
    
    return create_state_response(world, {
        'character': {
            'x': world.character.x,
            'y': world.character.y,
            'emoji': world.character.emoji
        },
        'locations': [{
            'x': loc.x,
            'y': loc.y,
            'emoji': loc.emoji,
            'type': loc.__class__.__name__,
            'name': getattr(loc, 'name', None)
        } for loc in world.locations]
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
            current_node = current_npc.get_current_node()
            if current_node and isinstance(current_node, ChoiceNode):
                choices = list(current_node.choices.keys())  # Get the choice texts from the dictionary keys
        
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
    world, messages = get_player_world()
    
    # Load and apply saved state
    if state := GameState.from_request(request.json):
        state.apply_to_world(world)
    
    handler = InteractionHandler(world, messages)
    response = handler.handle_interaction(request.json)
    return create_state_response(world, response)

@app.route('/create_npc', methods=['POST'])
def create_npc():
    world, _ = get_player_world()
    try:
        description = request.json['description']
        # Create the NPC data
        npc_data = create_character(description)
        
        # If npc_data is a string (YAML), parse it
        if isinstance(npc_data, str):
            npc_data = yaml.safe_load(npc_data)
            
        if not npc_data or 'npc' not in npc_data:
            raise ValueError("Failed to generate valid NPC data")

        # Generate unique ID for the NPC
        npc_id = str(uuid.uuid4())
        npc_filename = f'dynamic_{npc_id}'  # Remove .yaml extension from the ID
        
        # Add to dynamic NPCs list with position
        dynamic_npc = {
            'id': npc_id,
            'x': request.json.get('x', 0),
            'y': request.json.get('y', 0),
            'data': npc_data  # Store the actual NPC data
        }
        DYNAMIC_NPCS.append(dynamic_npc)
        
        # Add initial position to NPC_POSITIONS
        NPC_POSITIONS[npc_filename] = {
            'x': request.json.get('x', 0),
            'y': request.json.get('y', 0)
        }
        
        # Log the data for debugging
        logger.debug(f"Created NPC with data: {dynamic_npc}")
        
        # Reload the world to include the new NPC
        world.reload_npcs()
        
        return jsonify({
            'success': True, 
            'message': 'NPC created successfully',
            'npc': {
                'id': npc_id,
                'x': dynamic_npc['x'],
                'y': dynamic_npc['y'],
                'name': npc_data['npc'].get('name', 'Unknown'),
                'emoji': npc_data['npc'].get('emoji', '👤')
            }
        })
    except Exception as e:
        logger.error(f"Error creating NPC: {str(e)}", exc_info=True)  # Add full traceback
        return jsonify({'success': False, 'message': str(e)})

@app.route('/reset_game', methods=['POST'])
def reset_game():
    session_id = session.get('session_id')
    if session_id:
        if session_id in game_worlds:
            del game_worlds[session_id]
        if session_id in game_messages:
            del game_messages[session_id]
    return jsonify({'status': 'success'})

# Cleanup function to remove inactive sessions periodically
def cleanup_inactive_sessions():
    """Remove game worlds for sessions that haven't been active for a while"""
    # This could be implemented with a timestamp-based cleanup mechanism
    pass

if __name__ == '__main__':
    app.run(debug=True) 