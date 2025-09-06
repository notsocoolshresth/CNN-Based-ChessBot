import os
import time
import sys
import chess
from flask import Flask, request, jsonify
from flask_cors import CORS


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from gui.cnn_minimax_chess import CNNMinimaxEngine

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Initialize the chess engine with default parameters
engine = CNNMinimaxEngine(elo="1200", depth=3)

@app.route('/move', methods=['POST'])
def make_move():
    """
    API endpoint to get the AI's next move based on the current board state.
    
    Expected JSON payload:
    {
        "fen": "current board position in FEN notation",
        "player": "white" or "black",
        "mode": "cnn_only", "minimax_only", or "cnn_minimax"
    }
    
    Returns:
    {
        "move": "move in UCI notation (e.g., 'e2e4')",
        "time_taken": elapsed time in seconds
    }
    """
    try:
        # Get the request data
        data = request.json
        print(data)
        
        if not data or 'fen' not in data or 'player' not in data or 'mode' not in data:
            return jsonify({"error": "Missing required fields: fen, player, or mode"}), 400
            
        fen = data['fen']
        player = data['player'].lower()
        mode = data['mode']
        
        # Validate inputs
        if player not in ['white', 'black']:
            return jsonify({"error": "Invalid player. Must be 'white' or 'black'"}), 400
        if mode not in ['cnn_only', 'minimax_only', 'cnn_minimax']:
            return jsonify({"error": "Invalid mode. Must be 'cnn_only', 'minimax_only', or 'cnn_minimax'"}), 400
            
        # Create a chess board from the FEN string
        board = chess.Board(fen)
        
        # Check if the game is over
        if board.is_game_over():
            return jsonify({"error": "Game is over", "result": board.result()}), 400
            
        start_time = time.time()
        
        # Select the appropriate move function based on the mode
        if mode == 'cnn_only':
            cnn_moves = engine.get_cnn_move_predictions(board, player, top_n=1)
            if not cnn_moves:
                return jsonify({"error": "No valid moves found"}), 400
            best_move, score = cnn_moves[0]
        elif mode == 'minimax_only':
            best_move, _ = engine.find_best_move(board, player, use_cnn=False)
        else:  # cnn_minimax
            best_move, _ = engine.find_best_move(board, player, use_cnn=True)
        
        time_taken = time.time() - start_time
        
        # Return the move in UCI notation
        print(best_move.uci())
        return jsonify({
            "move": best_move.uci(),
            "time_taken": time_taken
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Add a simple health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(debug=True, host='0.0.0.0', port=port)