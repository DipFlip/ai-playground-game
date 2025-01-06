import json
import yaml
from openai import OpenAI
import dotenv
from npc_schema import NPC_FUNCTIONS
from sequence_schema import SEQUENCE_FUNCTIONS

dotenv.load_dotenv()

# Initialize OpenAI client
client = OpenAI()  # Make sure you have OPENAI_API_KEY in your environment variables

def create_character(prompt):
    """
    Creates a character based on the given prompt using OpenAI's API.
    Generates both NPC attributes and conversation sequence.
    """
    try:
        # First, create the NPC character
        npc_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": f"Create an NPC character based on this description: {prompt}"}
            ],
            functions=NPC_FUNCTIONS,
            function_call={"name": "create_npc"}
        )

        # Extract the NPC data
        npc_data = json.loads(npc_response.choices[0].message.function_call.arguments)

        # Then, create the sequence based on the NPC's personality
        sequence_prompt = f"Create a conversation sequence for an NPC named {npc_data['name']} who is {npc_data['personality']}. {prompt}"
        sequence_response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "user", "content": sequence_prompt}
            ],
            functions=SEQUENCE_FUNCTIONS,
            function_call={"name": "create_sequence"}
        )

        # Extract the sequence data
        sequence_data = json.loads(sequence_response.choices[0].message.function_call.arguments)
        
        # Combine NPC and sequence data
        combined_data = {
            "npc": npc_data,
            "sequence": sequence_data["sequence"]
        }
        
        # Convert to YAML
        yaml_output = yaml.dump(combined_data, sort_keys=False, allow_unicode=True)
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