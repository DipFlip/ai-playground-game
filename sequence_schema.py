"""
Sequence function schema for NPC conversation generation
"""

SEQUENCE_FUNCTIONS = [
    {
        "name": "create_sequence",
        "description": "Creates a sequence of actions for an NPC character. The sequence defines how the NPC interacts with players.",
        "parameters": {
            "type": "object",
            "properties": {
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
            "required": ["sequence"]
        }
    }
] 