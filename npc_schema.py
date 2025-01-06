"""
NPC schema for character generation
"""

NPC_FUNCTIONS = [
    {
        "name": "create_npc",
        "description": "Creates an NPC character with basic attributes and personality.",
        "parameters": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "The name of the NPC"
                },
                "emoji": {
                    "type": "string",
                    "description": "A single emoji that represents the character"
                },
                "personality": {
                    "type": "string",
                    "description": "A short description of the character's personality, traits, and role in the game"
                },
                "position": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "The [x, y] position of the NPC. If not provided, a random walkable position will be chosen."
                },
                "wander": {
                    "type": "object",
                    "description": "Settings for NPC wandering behavior",
                    "properties": {
                        "enabled": {
                            "type": "boolean",
                            "description": "Whether the NPC should wander around",
                            "default": True
                        },
                        "interval": {
                            "type": "integer",
                            "description": "Time in seconds between wandering attempts",
                            "default": 5
                        }
                    }
                }
            },
            "required": ["name", "emoji", "personality"]
        }
    }
] 