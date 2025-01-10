import pytest
from app import app
import json

@pytest.fixture
def client():
    """Create a test client for our Flask app"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

def test_home_route(client):
    """Test that the home route returns 200 and renders correctly"""
    response = client.get('/')
    assert response.status_code == 200
    assert b'<!DOCTYPE html>' in response.data

def test_game_state_get(client):
    """Test that the game state route works"""
    response = client.get('/game_state')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'character' in data
    assert 'gameState' in data
    assert 'npcPositions' in data['gameState']

def test_move_endpoint(client):
    """Test the move endpoint"""
    initial_x = 1
    initial_y = 1
    test_data = {
        'direction': 'east',
        'savedState': {
            'player': {'x': initial_x, 'y': initial_y},
            'npcPositions': {},
            'dynamicNpcs': []
        }
    }
    response = client.post('/move', 
                          data=json.dumps(test_data),
                          content_type='application/json')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert 'canMove' in data
    assert 'emoji' in data
    assert 'gameState' in data
    
    # Check position based on canMove response
    if data['canMove']:
        # If movement was allowed, player should have moved east (x increased)
        assert data['gameState']['player']['x'] > initial_x
        assert data['gameState']['player']['y'] == initial_y
    else:
        # If movement was not allowed, position should not have changed
        assert data['gameState']['player']['x'] == initial_x
        assert data['gameState']['player']['y'] == initial_y 