import json
import yaml
from openai import OpenAI
import dotenv
dotenv.load_dotenv()

# Initialize OpenAI client
client = OpenAI()  # Make sure you have OPENAI_API_KEY in your environment variables

# Define the function schema
functions = [
    {
        "name": "create_npc",
        "description": "Creates an NPC character with a sequence of actions. The character can have multiple interactions before requiring user input.",
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
                "position": {
                    "type": "array",
                    "items": {
                        "type": "integer"
                    },
                    "description": "The [x, y] position of the NPC"
                },
                "sequence": {
                    "type": "array",
                    "description": "A sequence of character actions. Each action requires 'type' and 'text'. Other fields depend on the action type.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "type": {
                                "type": "string",
                                "enum": ["talk", "ask", "give", "trade", "Choice"],
                                "description": "The type of action: talk (just dialogue), ask (requests input), give (gives item), trade (exchanges items), Choice (presents multiple options)"
                            },
                            "text": {
                                "type": "string",
                                "description": "The dialogue text - can be a statement or question depending on the action type"
                            },
                            "user_input": {
                                "type": "string",
                                "description": "Optional: For 'ask' type only. Variable name to store the player's response. Use sparingly. Later conversations can use input as {variable_name}"
                            },
                            "item": {
                                "type": "object",
                                "description": "Required for 'give' type only. Specifies the item to give and its quantity",
                                "properties": {
                                    "name": {
                                        "type": "string",
                                        "description": "The name of the item to give"
                                    },
                                    "quantity": {
                                        "type": "integer",
                                        "description": "Amount of the item to give. Defaults to 1 if not specified",
                                        "default": 1
                                    }
                                },
                                "required": ["name"]
                            },
                            "trade": {
                                "type": "object",
                                "description": "Required for 'trade' type only. Specifies the items to trade",
                                "properties": {
                                    "want": {
                                        "type": "object",
                                        "description": "The item the NPC wants from the player",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "The name of the item wanted"
                                            },
                                            "quantity": {
                                                "type": "integer",
                                                "description": "Amount of the item wanted",
                                                "default": 1
                                            }
                                        },
                                        "required": ["name"]
                                    },
                                    "offer": {
                                        "type": "object",
                                        "description": "The item the NPC offers in return",
                                        "properties": {
                                            "name": {
                                                "type": "string",
                                                "description": "The name of the item offered"
                                            },
                                            "quantity": {
                                                "type": "integer",
                                                "description": "Amount of the item offered",
                                                "default": 1
                                            }
                                        },
                                        "required": ["name"]
                                    },
                                    "success_text": {
                                        "type": "string",
                                        "description": "Text to show when trade is successful"
                                    },
                                    "failure_text": {
                                        "type": "string",
                                        "description": "Text to show when player doesn't have enough items"
                                    }
                                },
                                "required": ["want", "offer", "success_text", "failure_text"]
                            },
                            "choices": {
                                "type": "array",
                                "description": "Required for 'Choice' type only. List of choices the player can select from",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "choice_text": {
                                            "type": "string",
                                            "description": "The text shown to the player for this choice"
                                        },
                                        "type": {
                                            "type": "string",
                                            "enum": ["give", "talk"],
                                            "description": "The type of action to take when this choice is selected"
                                        },
                                        "text": {
                                            "type": "string",
                                            "description": "For talk actions, the text to say when this choice is selected"
                                        },
                                        "item": {
                                            "type": "object",
                                            "description": "For give actions, the item to give when this choice is selected",
                                            "properties": {
                                                "name": {
                                                    "type": "string",
                                                    "description": "The name of the item to give"
                                                },
                                                "quantity": {
                                                    "type": "integer",
                                                    "description": "Amount of the item to give",
                                                    "default": 1
                                                }
                                            },
                                            "required": ["name"]
                                        }
                                    },
                                    "required": ["choice_text"]
                                }
                            }
                        },
                        "required": ["type", "text"]
                    }
                }
            },
            "required": ["name", "emoji", "position", "sequence"]
        }
    }
]

def create_character(prompt):
    """
    Creates a character based on the given prompt using OpenAI's API
    """
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": prompt}
            ],
            functions=functions,
            function_call={"name": "create_npc"}
        )

        # Extract the function call arguments
        function_response = response.choices[0].message.function_call.arguments
        npc_data = json.loads(function_response)
        
        # Convert to YAML
        yaml_output = yaml.dump({"npc": npc_data}, sort_keys=False, allow_unicode=True)
        return yaml_output

    except Exception as e:
        print(f"Error creating character: {str(e)}")
        return None

def main():
    # Example prompts
    prompts = [
        "Create a character that gives the player meat. It's located on 2,1",
        "Create a friendly merchant who sells potions at position 5,3",
        "Create a wise old wizard who teaches spells at position 1,4"
    ]

    # Test with one prompt
    result = create_character(prompts[0])
    if result:
        print("Generated Character YAML:")
        print(result)

if __name__ == "__main__":
    main()