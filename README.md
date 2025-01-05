# Simple Game World

A simple 2D game world built with Python and Flask where a character can move around, fish at a lake, and sell fish at a shop.

## Features

- Character movement in 4 directions
- Interactive locations:
  - Lake: Catch fish
  - Shop: Sell fish for coins
- Web-based UI with:
  - Visual representation of the world
  - Movement controls
  - Interaction button
  - Inventory display
  - Message log

## Prerequisites

- Python 3.6+
- Flask

## Installation

1. Clone the repository
2. Install the dependencies using `pip install -r requirements.txt`
3. Edit `template.env` with your OpenAI API key and save as `.env`
4. Run the server using `python app.py`
5. Open the game in your browser at `http://localhost:5000`
