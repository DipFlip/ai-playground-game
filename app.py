from flask import Flask, render_template, jsonify, request
from world import World

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

@app.route('/move', methods=['POST'])
def move():
    direction = request.json['direction']
    dx, dy = {
        'north': (0, -1),
        'south': (0, 1),
        'east': (1, 0),
        'west': (-1, 0)
    }[direction]
    
    game_world.character.move(dx, dy)
    
    return jsonify({
        'x': game_world.character.x,
        'y': game_world.character.y,
        'inventory': game_world.character.inventory
    })

@app.route('/interact', methods=['POST'])
def interact():
    # Capture print output
    import io
    import sys
    old_stdout = sys.stdout
    sys.stdout = output = io.StringIO()
    
    result = game_world.try_interact()
    
    # Get the printed message
    sys.stdout = old_stdout
    message = output.getvalue().strip()
    
    if message:
        game_messages.append(message)
        # Keep only last 5 messages
        if len(game_messages) > 5:
            game_messages.pop(0)
    
    return jsonify({
        'success': result,
        'message': message,
        'inventory': game_world.character.inventory,
        'messages': game_messages
    })

if __name__ == '__main__':
    app.run(debug=True) 