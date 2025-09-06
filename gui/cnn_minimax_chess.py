import numpy as np
import chess # type: ignore
import time
import argparse
from tensorflow.keras.models import load_model # type: ignore
import pygame # type: ignore
import os
# Set up paths relative to the script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GUI_DIR = SCRIPT_DIR

# Default location of models inside gui/models/
DEFAULT_MODELS_DIR = os.path.join(GUI_DIR, "models")

# Allow overriding via environment variable (for Flask/Docker)
MODELS_BASE = os.environ.get("CHESS_MODELS_DIR", DEFAULT_MODELS_DIR)

MODEL_DIRS = {
    "700": os.path.join(MODELS_BASE, "700-elo"),
    "1100": os.path.join(MODELS_BASE, "1100-elo"),
    "1200": os.path.join(MODELS_BASE, "1200-elo"),
}

# Piece values for heuristic evaluation (in centipawns)
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 320,
    chess.BISHOP: 330,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Piece-square tables for positional evaluation
PAWN_TABLE = np.array([
    [0, 0, 0, 0, 0, 0, 0, 0],
    [50, 50, 50, 50, 50, 50, 50, 50],
    [10, 10, 20, 30, 30, 20, 10, 10],
    [5, 5, 10, 25, 25, 10, 5, 5],
    [0, 0, 0, 20, 20, 0, 0, 0],
    [5, -5, -10, 0, 0, -10, -5, 5],
    [5, 10, 10, -20, -20, 10, 10, 5],
    [0, 0, 0, 0, 0, 0, 0, 0]
])

KNIGHT_TABLE = np.array([
    [-50, -40, -30, -30, -30, -30, -40, -50],
    [-40, -20, 0, 0, 0, 0, -20, -40],
    [-30, 0, 10, 15, 15, 10, 0, -30],
    [-30, 5, 15, 20, 20, 15, 5, -30],
    [-30, 0, 15, 20, 20, 15, 0, -30],
    [-30, 5, 10, 15, 15, 10, 5, -30],
    [-40, -20, 0, 5, 5, 0, -20, -40],
    [-50, -40, -30, -30, -30, -30, -40, -50]
])

BISHOP_TABLE = np.array([
    [-20, -10, -10, -10, -10, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 10, 10, 10, 10, 0, -10],
    [-10, 5, 5, 10, 10, 5, 5, -10],
    [-10, 0, 5, 10, 10, 5, 0, -10],
    [-10, 10, 10, 10, 10, 10, 10, -10],
    [-10, 5, 0, 0, 0, 0, 5, -10],
    [-20, -10, -10, -10, -10, -10, -10, -20]
])

ROOK_TABLE = np.array([
    [0, 0, 0, 0, 0, 0, 0, 0],
    [5, 10, 10, 10, 10, 10, 10, 5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [-5, 0, 0, 0, 0, 0, 0, -5],
    [0, 0, 0, 5, 5, 0, 0, 0]
])

QUEEN_TABLE = np.array([
    [-20, -10, -10, -5, -5, -10, -10, -20],
    [-10, 0, 0, 0, 0, 0, 0, -10],
    [-10, 0, 5, 5, 5, 5, 0, -10],
    [-5, 0, 5, 5, 5, 5, 0, -5],
    [0, 0, 5, 5, 5, 5, 0, -5],
    [-10, 5, 5, 5, 5, 5, 0, -10],
    [-10, 0, 5, 0, 0, 0, 0, -10],
    [-20, -10, -10, -5, -5, -10, -10, -20]
])

KING_MIDDLE_GAME_TABLE = np.array([
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-30, -40, -40, -50, -50, -40, -40, -30],
    [-20, -30, -30, -40, -40, -30, -30, -20],
    [-10, -20, -20, -20, -20, -20, -20, -10],
    [20, 20, 0, 0, 0, 0, 20, 20],
    [20, 30, 10, 0, 0, 10, 30, 20]
])

KING_END_GAME_TABLE = np.array([
    [-50, -40, -30, -20, -20, -30, -40, -50],
    [-30, -20, -10, 0, 0, -10, -20, -30],
    [-30, -10, 20, 30, 30, 20, -10, -30],
    [-30, -10, 30, 40, 40, 30, -10, -30],
    [-30, -10, 30, 40, 40, 30, -10, -30],
    [-30, -10, 20, 30, 30, 20, -10, -30],
    [-30, -30, 0, 0, 0, 0, -30, -30],
    [-50, -30, -30, -30, -30, -30, -30, -50]
])

class ChessUtilities:
    @staticmethod
    def is_endgame(board):
        """Determine if the current position is an endgame."""
        queens = len(board.pieces(chess.QUEEN, chess.WHITE)) + len(board.pieces(chess.QUEEN, chess.BLACK))
        total_pieces = len(list(board.pieces(chess.KNIGHT, chess.WHITE))) + len(list(board.pieces(chess.KNIGHT, chess.BLACK))) + \
                    len(list(board.pieces(chess.BISHOP, chess.WHITE))) + len(list(board.pieces(chess.BISHOP, chess.BLACK))) + \
                    len(list(board.pieces(chess.ROOK, chess.WHITE))) + len(list(board.pieces(chess.ROOK, chess.BLACK)))
        
        return queens == 0 or total_pieces <= 6

    @staticmethod
    def get_piece_square_table_value(piece_type, square, is_white, endgame=False):
        """Get the position value for a piece from its appropriate piece-square table."""
        row = 7 - chess.square_rank(square) if is_white else chess.square_rank(square)
        col = chess.square_file(square)
        
        if piece_type == chess.PAWN:
            return PAWN_TABLE[row][col]
        elif piece_type == chess.KNIGHT:
            return KNIGHT_TABLE[row][col]
        elif piece_type == chess.BISHOP:
            return BISHOP_TABLE[row][col]
        elif piece_type == chess.ROOK:
            return ROOK_TABLE[row][col]
        elif piece_type == chess.QUEEN:
            return QUEEN_TABLE[row][col]
        elif piece_type == chess.KING:
            if endgame:
                return KING_END_GAME_TABLE[row][col]
            else:
                return KING_MIDDLE_GAME_TABLE[row][col]
        return 0

    @staticmethod
    def evaluate_board(board):
        """
        Heuristic evaluation function that considers:
        1. Material balance
        2. Piece positioning using piece-square tables
        3. Game state (checkmate, stalemate)
        4. Mobility
        """
        if board.is_checkmate():
            # If current player is checkmated
            return -10000 if board.turn else 10000
        
        if board.is_stalemate() or board.is_insufficient_material() or board.is_fifty_moves() or board.is_repetition(3):
            return 0  # Draw
        
        endgame = ChessUtilities.is_endgame(board)
        
        # Material and position evaluation
        eval_score = 0
        for square in chess.SQUARES:
            piece = board.piece_at(square)
            if piece is not None:
                # Material value
                value = PIECE_VALUES[piece.piece_type]
                
                # Add piece-square table value
                position_value = ChessUtilities.get_piece_square_table_value(
                    piece.piece_type, square, piece.color, endgame
                )
                
                # White is positive, black is negative
                modifier = 1 if piece.color else -1
                eval_score += modifier * (value + position_value)
        
        # Additional positional bonuses/penalties
        # Mobility (number of legal moves)
        mobility_bonus = 5  # Points per legal move
        current_legal_moves = len(list(board.legal_moves))
        
        # Store original turn
        original_turn = board.turn
        
        # Switch sides to count opponent's moves
        board.turn = not board.turn
        opponent_legal_moves = len(list(board.legal_moves))
        
        # Restore original turn
        board.turn = original_turn
        
        mobility_score = mobility_bonus * (current_legal_moves - opponent_legal_moves)
        
        # Apply the mobility score
        eval_score += mobility_score if board.turn else -mobility_score
        
        return eval_score

    @staticmethod
    def fen_to_matrix(fen):
        """Convert a FEN string to a matrix representation for CNN input."""
        fen = fen.split()[0]
        
        piece_dict = {
            'p' : [1,0,0,0,0,0,0,0,0,0,0,0],
            'P' : [0,0,0,0,0,0,1,0,0,0,0,0],
            'n' : [0,1,0,0,0,0,0,0,0,0,0,0],
            'N' : [0,0,0,0,0,0,0,1,0,0,0,0],
            'b' : [0,0,1,0,0,0,0,0,0,0,0,0],
            'B' : [0,0,0,0,0,0,0,0,1,0,0,0],
            'r' : [0,0,0,1,0,0,0,0,0,0,0,0],
            'R' : [0,0,0,0,0,0,0,0,0,1,0,0],
            'q' : [0,0,0,0,1,0,0,0,0,0,0,0],
            'Q' : [0,0,0,0,0,0,0,0,0,0,1,0],
            'k' : [0,0,0,0,0,1,0,0,0,0,0,0],
            'K' : [0,0,0,0,0,0,0,0,0,0,0,1],
            '.' : [0,0,0,0,0,0,0,0,0,0,0,0],
        }

        row_arr = []
        rows = fen.split('/')
        for row in rows:
            arr = []
            for ch in str(row):
                if ch.isdigit():
                    for _ in range(int(ch)):
                        arr.append(piece_dict['.'])
                else:
                    arr.append(piece_dict[ch])
            row_arr.append(arr)

        mat = np.array(row_arr)
        return mat

    @staticmethod
    def invert_fen(fen):
        """Invert the FEN representation for black's perspective."""
        fen = fen.split()[0]
        rows = fen.split('/')
        rows.reverse()
        for i in range(8):
            rows[i] = rows[i].swapcase()
        return '/'.join(rows)

    @staticmethod
    def uci_to_row_col(uci):
        """Convert UCI move notation to row-column coordinates."""
        sq_from = uci[: 2]
        sq_to = uci[2 :]

        def parse_square(sq):
            col = ord(sq[0]) - ord('a')
            row = 7 - (int(sq[1]) - 1)
            return row, col

        return parse_square(sq_from) + parse_square(sq_to)

class CNNMinimaxEngine:
    def __init__(self, elo="1200", depth=3):
        self.depth = depth
        self.from_model = load_model(os.path.join(MODEL_DIRS[elo], "from.h5"), compile=True)
        self.to_model = load_model(os.path.join(MODEL_DIRS[elo], "to.h5"), compile=True)
        
    def get_cnn_move_predictions(self, board, colour, top_n=5):
        """
        Get the top N move predictions from the CNN models.
        Returns a list of (move, score) tuples.
        """
        fen = board.fen()
        
        if colour == 'black':
            fen = ChessUtilities.invert_fen(fen=fen)
        
        arr = ChessUtilities.fen_to_matrix(fen=fen)
        arr = arr.reshape((1,) + arr.shape)
        
        from_matrix = self.from_model.predict(arr, verbose=0).reshape((8, 8))
        to_matrix = self.to_model.predict(arr, verbose=0).reshape((8, 8))
        
        if colour == 'black':
            from_matrix = np.flip(from_matrix, axis=0)
            to_matrix = np.flip(to_matrix, axis=0)
        
        moves = []
        for move in list(board.legal_moves):
            from_row, from_col, to_row, to_col = ChessUtilities.uci_to_row_col(move.uci())
            score = from_matrix[from_row][from_col] * to_matrix[to_row][to_col]
            moves.append((move, score))
        
        # Sort by CNN score and take top N
        moves.sort(key=lambda x: x[1], reverse=True)
        return moves[:top_n]

    def minimax(self, board, depth, alpha, beta, maximizing_player, colour, use_cnn=True):
        """
        Minimax algorithm with alpha-beta pruning.
        Returns the best value and move.
        """
        if depth == 0 or board.is_game_over():
            return ChessUtilities.evaluate_board(board), None
        
        # For the maximizing player (white)
        if maximizing_player:
            max_eval = float('-inf')
            best_move = None
            
            # Get top moves from CNN or all legal moves
            if use_cnn and depth == self.depth:  # Only use CNN at the root for efficiency
                moves = self.get_cnn_move_predictions(board, colour)
            else:
                # Use all legal moves for deeper levels
                moves = [(move, 0) for move in board.legal_moves]
            
            for move, _ in moves:
                board.push(move)
                eval_score, _ = self.minimax(board, depth - 1, alpha, beta, False, colour, False)
                board.pop()
                
                if eval_score > max_eval:
                    max_eval = eval_score
                    best_move = move
                    
                alpha = max(alpha, eval_score)
                if beta <= alpha:
                    break  # Beta cutoff
                    
            return max_eval, best_move
        
        # For the minimizing player (black)
        else:
            min_eval = float('inf')
            best_move = None
            
            # Get top moves from CNN or all legal moves
            if use_cnn and depth == self.depth:  # Only use CNN at the root for efficiency
                moves = self.get_cnn_move_predictions(board, colour)
            else:
                # Use all legal moves for deeper levels
                moves = [(move, 0) for move in board.legal_moves]
                
            for move, _ in moves:
                board.push(move)
                eval_score, _ = self.minimax(board, depth - 1, alpha, beta, True, colour, False)
                board.pop()
                
                if eval_score < min_eval:
                    min_eval = eval_score
                    best_move = move
                    
                beta = min(beta, eval_score)
                if beta <= alpha:
                    break  # Alpha cutoff
                    
            return min_eval, best_move

    def find_best_move(self, board, colour, use_cnn=True):
        """Find the best move for the given board position."""
        start_time = time.time()
        
        is_maximizing = colour == 'white'
        
        # Get the best move using minimax
        _, best_move = self.minimax(
            board, 
            self.depth, 
            float('-inf'), 
            float('inf'), 
            is_maximizing,
            colour,
            use_cnn
        )
        
        end_time = time.time()
        elapsed = end_time - start_time
        
        # If no best move found (shouldn't happen unless game over), return first legal move
        if best_move is None and not board.is_game_over():
            best_move = list(board.legal_moves)[0]
            
        return best_move, elapsed
