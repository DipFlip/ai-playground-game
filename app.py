from flask import Flask, render_template, jsonify, request, send_file
from world import World, DYNAMIC_NPCS, NPC_POSITIONS, PLAYER_STATE
from npc import NPC
import os
from character_generator import create_character
import yaml
import uuid
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
# Reduce Werkzeug logger verbosity
logging.getLogger('werkzeug').setLevel(logging.WARNING)

app = Flask(__name__)

def load_state_from_request():
    """Load state from request data if it exists"""
    if request.is_json and request.json.get('savedState'):
        saved_state = request.json['savedState']
        if saved_state.get('player'):
            player_state = saved_state['player']
            PLAYER_STATE.update(player_state)
            # Sync game world character position with saved state
            game_world.character.x = player_state['x']
            game_world.character.y = player_state['y']
            
        if saved_state.get('npcPositions'):
            NPC_POSITIONS.update(saved_state['npcPositions'])
            # Sync NPC positions with saved state
            for location in game_world.locations:
                if isinstance(location, NPC):
                    npc_id = next((id for id, pos in saved_state['npcPositions'].items() 
                                 if (isinstance(id, str) and id.startswith('dynamic_') and location.name == f'dynamic_{id.split("_")[1]}') 
                                 or (location.name == id.replace('.yaml', ''))), None)
                    if npc_id and npc_id in saved_state['npcPositions']:
                        location.x = saved_state['npcPositions'][npc_id]['x']
                        location.y = saved_state['npcPositions'][npc_id]['y']
            
        if saved_state.get('dynamicNpcs'):
            DYNAMIC_NPCS.clear()
            DYNAMIC_NPCS.extend(saved_state['dynamicNpcs'])
        if saved_state.get('interaction'):
            return saved_state['interaction']
    return None

def create_state_response(response_data):
    """Add current state to response data"""
    game_state = {
        'player': {
            'x': game_world.character.x,
            'y': game_world.character.y,
            'inventory': game_world.character.inventory
        },
        'npcPositions': NPC_POSITIONS,
        'dynamicNpcs': DYNAMIC_NPCS,
    }

    # Add interaction state if there is one
    if game_world.current_interaction:
        game_state['interaction'] = {
            'name': game_world.current_interaction.name,
            'is_talking': game_world.current_interaction.is_talking,
            'waiting_for_response': game_world.current_interaction.waiting_for_response,
            'sequence_state': {
                'current_state_id': game_world.current_interaction.sequence.current_state_id,
                'responses': game_world.current_interaction.sequence.responses
            }
        }

    response_data['gameState'] = game_state
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
    # Load saved state if it exists
    load_state_from_request()
    
    # Don't allow movement during interaction
    if game_world.is_interaction_active():
        return create_state_response({
            'x': game_world.character.x,
            'y': game_world.character.y,
            'inventory': game_world.character.inventory,
            'emoji': game_world.character.emoji,
            'canMove': False
        })

    direction = request.json['direction']
    dx, dy = {
        'north': (0, -1),
        'south': (0, 1),
        'east': (1, 0),
        'west': (-1, 0)
    }[direction]
    
    # Calculate new position
    new_x = game_world.character.x + dx
    new_y = game_world.character.y + dy
    
    # Check if movement is allowed
    if game_world.can_move_to(new_x, new_y):
        game_world.character.move(dx, dy)
    
    return create_state_response({
        'x': game_world.character.x,
        'y': game_world.character.y,
        'inventory': game_world.character.inventory,
        'emoji': game_world.character.emoji,
        'canMove': True
    })

@app.route('/game_state', methods=['GET', 'POST'])
def game_state():
    # Load all state from the request
    if request.is_json and request.json.get('savedState'):
        saved_state = request.json['savedState']
        if saved_state.get('player'):
            player_state = saved_state['player']
            PLAYER_STATE.update(player_state)
            # Sync game world character position with saved state
            game_world.character.x = player_state['x']
            game_world.character.y = player_state['y']
            
        if saved_state.get('npcPositions'):
            NPC_POSITIONS.update(saved_state['npcPositions'])
            # Sync NPC positions with saved state
            for location in game_world.locations:
                if isinstance(location, NPC):
                    npc_id = next((id for id, pos in saved_state['npcPositions'].items() 
                                 if (isinstance(id, str) and id.startswith('dynamic_') and location.name == f'dynamic_{id.split("_")[1]}') 
                                 or (location.name == id.replace('.yaml', ''))), None)
                    if npc_id and npc_id in saved_state['npcPositions']:
                        location.x = saved_state['npcPositions'][npc_id]['x']
                        location.y = saved_state['npcPositions'][npc_id]['y']
                        
        if saved_state.get('dynamicNpcs'):
            DYNAMIC_NPCS.clear()
            DYNAMIC_NPCS.extend(saved_state['dynamicNpcs'])
    
    # Update NPCs
    game_world.update_npcs()  # Update world state including NPC movements
    
    return create_state_response({
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

@app.route('/interact', methods=['POST'])
def interact():
    # Load saved state if it exists
    load_state_from_request()
    
    # Capture print output
    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = output = io.StringIO()
    
    # Check if we're providing an answer
    if 'answer' in request.json:
        npc = game_world.current_interaction
        if npc:
            # Extract just the text value from the answer
            answer = request.json['answer']
            if isinstance(answer, dict) and 'text' in answer:
                answer = answer['text']
            npc.provide_response(answer, game_world.character)
    
    result = game_world.try_interact()
    
    # Get the printed message
    sys.stdout = old_stdout
    message = output.getvalue().strip()
    
    # Get current NPC before updating messages
    current_npc = game_world.current_interaction
    
    if message:
        game_messages.append(message)
        # Keep only last 5 messages
        if len(game_messages) > 5:
            game_messages.pop(0)
    
    # Clear messages if interaction is completely over
    if not current_npc or not current_npc.is_talking:
        game_messages.clear()
    
    # Check if NPC is waiting for input
    waiting_for_input = False
    choices = []
    if current_npc and current_npc.waiting_for_response:
        waiting_for_input = True
        current_state = current_npc.get_current_state()
        if current_state and current_state.type == "choice" and current_state.choices:
            choices = [choice['choice_text'] for choice in current_state.choices]
    
    return create_state_response({
        'success': result,
        'message': message,
        'inventory': game_world.character.inventory,
        'messages': game_messages,
        'waitingForInput': waiting_for_input,
        'choices': choices,
        'is_talking': current_npc.is_talking if current_npc else False
    })

@app.route('/create_npc', methods=['POST'])
def create_npc():
    try:
        description = request.json['description']
        
        # Generate NPC YAML using character_generator
        yaml_content = create_character(description)
        
        if not yaml_content:
            return jsonify({'success': False, 'error': 'Failed to generate NPC'})
        
        # Parse the YAML content
        npc_data = yaml.safe_load(yaml_content)
        
        # Add to in-memory storage
        DYNAMIC_NPCS.append(npc_data)
        
        # Reload the world to include the new NPC
        global game_world
        game_world = World()
        
        return create_state_response({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/reset_game', methods=['POST'])
def reset_game():
    """Reset all game state to initial values."""
    try:
        # Clear player state
        PLAYER_STATE.update({
            'x': 0,
            'y': 0,
            'inventory': {}
        })
        
        # Clear NPC positions
        NPC_POSITIONS.clear()
        
        # Clear dynamic NPCs
        DYNAMIC_NPCS.clear()
        
        # Reinitialize the game world
        global game_world
        game_world = World()
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True) 