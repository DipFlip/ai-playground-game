from flask import Flask, render_template, jsonify, request, send_file
from world import World
import os
from character_generator import create_character
import yaml
import uuid

app = Flask(__name__)

# Create a global world instance
game_world = World()
game_messages = []

@app.route('/')
def home():
    return render_template('game.html', 
                         character=game_world.character,
                         locations=game_world.locations,
                         messages=game_messages)

@app.route('/graphics/<path:filename>')
def serve_graphic(filename):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return send_file(os.path.join(base_path, 'graphics', filename))

@app.route('/static/<path:filename>')
def serve_static(filename):
    base_path = os.path.dirname(os.path.abspath(__file__))
    return send_file(os.path.join(base_path, 'static', filename))

@app.route('/move', methods=['POST'])
def move():
    # Don't allow movement during interaction
    if game_world.is_interaction_active():
        return jsonify({
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
    
    return jsonify({
        'x': game_world.character.x,
        'y': game_world.character.y,
        'inventory': game_world.character.inventory,
        'emoji': game_world.character.emoji,
        'canMove': True
    })

@app.route('/interact', methods=['POST'])
def interact():
    # Capture print output
    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = output = io.StringIO()
    
    # Check if we're providing an answer
    if 'answer' in request.json:
        npc = game_world.current_interaction
        if npc:
            npc.provide_response(request.json['answer'])
    
    result = game_world.try_interact()
    
    # Get the printed message
    sys.stdout = old_stdout
    message = output.getvalue().strip()
    
    if message:
        game_messages.append(message)
        # Keep only last 5 messages
        if len(game_messages) > 5:
            game_messages.pop(0)
    
    # Check if NPC is waiting for input
    waiting_for_input = False
    current_npc = game_world.current_interaction
    if current_npc and current_npc.waiting_for_response:
        waiting_for_input = True
    
    return jsonify({
        'success': result,
        'message': message,
        'inventory': game_world.character.inventory,
        'messages': game_messages,
        'waitingForInput': waiting_for_input
    })

@app.route('/create_npc', methods=['POST'])
def create_npc():
    try:
        description = request.json['description']
        
        # Generate NPC YAML using character_generator
        yaml_content = create_character(description)
        
        if not yaml_content:
            return jsonify({'success': False, 'error': 'Failed to generate NPC'})
        
        # Create a unique filename for the NPC
        npc_filename = f"npc_{uuid.uuid4().hex[:8]}.yaml"
        base_path = os.path.dirname(os.path.abspath(__file__))
        npc_dir = os.path.join(base_path, 'npcs')
        
        # Create npcs directory if it doesn't exist
        os.makedirs(npc_dir, exist_ok=True)
        
        # Save the YAML file
        npc_path = os.path.join(npc_dir, npc_filename)
        with open(npc_path, 'w', encoding='utf-8') as f:
            f.write(yaml_content)
        
        # Reload the world to include the new NPC
        global game_world
        game_world = World()
        
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True) 