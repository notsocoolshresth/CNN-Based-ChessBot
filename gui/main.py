from cnn_minimax_chess import CNNMinimaxEngine
import os
import argparse
import pygame # type: ignore
import chess    # type: ignore
# Set up paths relative to the script location
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
GUI_DIR = SCRIPT_DIR  # Since the script is already in the gui directory
MODEL_DIRS = {
    "700": os.path.join(GUI_DIR, "models", "700-elo"),
    "1100": os.path.join(GUI_DIR, "models", "1100-elo"),
    "1200": os.path.join(GUI_DIR, "models", "1200-elo")
}

class ChessGame:
    def __init__(self, elo="1200", depth=3, square_size=75):
        pygame.init()
        self.square_size = square_size
        self.board_size = 8 * square_size
        self.info_width = 300
        self.screen_width = self.board_size + self.info_width
        self.screen_height = self.board_size
        
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption('Chess AI with CNN-Minimax')
        
        self.board = chess.Board()
        self.engine = CNNMinimaxEngine(elo=elo, depth=depth)
        
        # Load piece images
        self.images = {}
        self.load_images()
        
        # Game state
        self.player_white = True
        self.ai_thinking = False
        self.selected_square = None
        self.game_over = False
        self.last_move = None
        self.move_history = []
        
        # Colors
        self.WHITE = (255, 255, 255)
        self.BLACK = (0, 0, 0)
        self.LIGHT_SQUARE = (240, 217, 181)
        self.DARK_SQUARE = (181, 136, 99)
        self.HIGHLIGHT = (124, 252, 0, 128)  # Light green with some transparency
        self.SELECTED = (255, 255, 0, 150)   # Yellow with some transparency
        self.LAST_MOVE = (186, 202, 43, 150) # Light olive
        
        # Fonts
        self.font = pygame.font.SysFont('Arial', 24)
        self.small_font = pygame.font.SysFont('Arial', 18)
        
        # Buttons
        self.buttons = [
            {'text': 'New Game', 'rect': pygame.Rect(self.board_size + 20, 50, 120, 40)},
            {'text': 'Switch Sides', 'rect': pygame.Rect(self.board_size + 150, 50, 120, 40)},
            {'text': 'CNN Only', 'rect': pygame.Rect(self.board_size + 20, 100, 120, 40)},
            {'text': 'Minimax Only', 'rect': pygame.Rect(self.board_size + 150, 100, 120, 40)},
            {'text': 'CNN+Minimax', 'rect': pygame.Rect(self.board_size + 85, 150, 120, 40)},
        ]
        self.use_cnn = True
        self.current_mode = "CNN+Minimax"
    
    def load_images(self):
        """Load chess piece images."""
        # Map chess piece symbols to the correct image filenames
        piece_filenames = {
            'P': 'pawn',
            'R': 'rook',
            'N': 'knight',
            'B': 'bishop',
            'Q': 'queen',
            'K': 'king'
        }
        
        for piece, filename in piece_filenames.items():
            # Load white pieces
            self.images[piece] = pygame.image.load(os.path.join(GUI_DIR, "images", f"white_{filename}.gif"))
            self.images[piece] = pygame.transform.scale(self.images[piece], (self.square_size, self.square_size))
            
            # Load black pieces
            self.images[piece.lower()] = pygame.image.load(os.path.join(GUI_DIR, "images", f"black_{filename}.gif"))
            self.images[piece.lower()] = pygame.transform.scale(self.images[piece.lower()], (self.square_size, self.square_size))
    
    def draw_board(self):
        """Draw the chess board and pieces."""
        # Draw squares
        for row in range(8):
            for col in range(8):
                color = self.LIGHT_SQUARE if (row + col) % 2 == 0 else self.DARK_SQUARE
                pygame.draw.rect(self.screen, color, 
                                (col * self.square_size, row * self.square_size, 
                                self.square_size, self.square_size))
                
                # Draw rank and file labels
                if col == 0:  # Ranks on the left
                    rank_label = self.small_font.render(str(8 - row), True, self.BLACK if color == self.LIGHT_SQUARE else self.WHITE)
                    self.screen.blit(rank_label, (5, row * self.square_size + 5))
                
                if row == 7:  # Files on the bottom
                    file_label = self.small_font.render(chr(97 + col), True, self.BLACK if color == self.LIGHT_SQUARE else self.WHITE)
                    self.screen.blit(file_label, (col * self.square_size + self.square_size - 15, self.board_size - 20))
        
        # Highlight last move
        if self.last_move:
            from_square = chess.parse_square(self.last_move[:2])
            to_square = chess.parse_square(self.last_move[2:4])
            
            # Create a transparent surface for the highlight
            highlight_surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
            pygame.draw.rect(highlight_surface, self.LAST_MOVE, (0, 0, self.square_size, self.square_size))
            
            # Highlight from square
            from_col = chess.square_file(from_square)
            from_row = 7 - chess.square_rank(from_square)
            self.screen.blit(highlight_surface, (from_col * self.square_size, from_row * self.square_size))
            
            # Highlight to square
            to_col = chess.square_file(to_square)
            to_row = 7 - chess.square_rank(to_square)
            self.screen.blit(highlight_surface, (to_col * self.square_size, to_row * self.square_size))
        
        # Highlight selected square
        if self.selected_square:
            square = chess.parse_square(self.selected_square)
            col = chess.square_file(square)
            row = 7 - chess.square_rank(square)
            
            # Create a transparent surface for the highlight
            highlight_surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
            pygame.draw.rect(highlight_surface, self.SELECTED, (0, 0, self.square_size, self.square_size))
            
            self.screen.blit(highlight_surface, (col * self.square_size, row * self.square_size))
            
            # Highlight legal moves from selected square
            for move in self.board.legal_moves:
                if move.from_square == square:
                    to_col = chess.square_file(move.to_square)
                    to_row = 7 - chess.square_rank(move.to_square)
                    
                    # Create a transparent surface for the highlight
                    move_surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
                    pygame.draw.rect(move_surface, self.HIGHLIGHT, (0, 0, self.square_size, self.square_size))
                    
                    self.screen.blit(move_surface, (to_col * self.square_size, to_row * self.square_size))
        
        # Draw pieces
        for square in chess.SQUARES:
            piece = self.board.piece_at(square)
            if piece:
                # Convert chess.Square to row, col
                col = chess.square_file(square)
                row = 7 - chess.square_rank(square)  # Invert row since chess uses 1-8 from bottom
                
                piece_symbol = piece.symbol()
                self.screen.blit(self.images[piece_symbol], 
                                (col * self.square_size, row * self.square_size))
    
    def draw_info_panel(self):
        """Draw information panel on the right side."""
        # Draw background
        pygame.draw.rect(self.screen, self.WHITE, 
                        (self.board_size, 0, self.info_width, self.screen_height))
        
        # Draw border
        pygame.draw.line(self.screen, self.BLACK, 
                        (self.board_size, 0), (self.board_size, self.screen_height), 2)
        
        # Draw game status
        status_text = "White's turn" if self.board.turn else "Black's turn"
        if self.board.is_checkmate():
            status_text = "Checkmate! " + ("Black" if self.board.turn else "White") + " wins!"
        elif self.board.is_stalemate():
            status_text = "Stalemate!"
        elif self.board.is_insufficient_material():
            status_text = "Draw by insufficient material!"
        
        status_surface = self.font.render(status_text, True, self.BLACK)
        self.screen.blit(status_surface, (self.board_size + 20, 10))
        
        # Draw current mode
        mode_surface = self.font.render(f"Mode: {self.current_mode}", True, self.BLACK)
        self.screen.blit(mode_surface, (self.board_size + 20, 200))
        
        # Draw buttons
        for button in self.buttons:
            pygame.draw.rect(self.screen, (200, 200, 200), button['rect'])
            pygame.draw.rect(self.screen, self.BLACK, button['rect'], 2)
            
            button_text = self.small_font.render(button['text'], True, self.BLACK)
            text_rect = button_text.get_rect(center=button['rect'].center)
            self.screen.blit(button_text, text_rect)
        
        # Display move history
        history_title = self.font.render("Move History", True, self.BLACK)
        self.screen.blit(history_title, (self.board_size + 20, 250))
        
        # Display last 10 moves
        for i, move in enumerate(self.move_history[-10:], start=0):
            if (len(self.move_history)>= 10):
                move_num = len(self.move_history) - 10 + i + 1
            else:
                move_num = i + 1
            move_text = f"{move_num}. {move}"
            move_surface = self.small_font.render(move_text, True, self.BLACK)
            self.screen.blit(move_surface, (self.board_size + 20, 280 + i * 20))
    
    def handle_mouse_click(self, pos):
        
        """Handle mouse click events."""
        # Check if clicked on a button
        for button in self.buttons:
            if button['rect'].collidepoint(pos):
                if button['text'] == 'New Game':
                    self.board = chess.Board()
                    self.selected_square = None
                    self.game_over = False
                    self.last_move = None
                    self.move_history = []
                elif button['text'] == 'Switch Sides':
                    self.player_white = not self.player_white
                    if self.board.turn != self.player_white:
                        self.ai_thinking = True  # Trigger AI move if it's AI's turn after switch
                elif button['text'] == 'CNN Only':
                    self.use_cnn = True
                    self.current_mode = "CNN Only"
                elif button['text'] == 'Minimax Only':
                    self.use_cnn = False
                    self.current_mode = "Minimax Only"
                elif button['text'] == 'CNN+Minimax':
                    self.use_cnn = True
                    self.current_mode = "CNN+Minimax"
                return
        
        # If game over or AI's turn, ignore board clicks
        if self.game_over or (self.board.turn and not self.player_white) or (not self.board.turn and self.player_white):
            return
        
        # Handle click on board
        if pos[0] < self.board_size and pos[1] < self.board_size:
            col = pos[0] // self.square_size
            row = pos[1] // self.square_size
            
            # Convert to chess square notation
            file_letter = chr(97 + col)  # 'a' through 'h'
            rank_number = 8 - row       # 1 through 8
            square_name = file_letter + str(rank_number)
            
            if self.selected_square is None:
                # Check if there's a piece on the square and it's the player's turn
                square = chess.parse_square(square_name)
                piece = self.board.piece_at(square)
                if piece and ((piece.color and self.player_white) or (not piece.color and not self.player_white)):
                    self.selected_square = square_name
            else:
                # Attempt to make a move
                move_uci = self.selected_square + square_name
                try:
                    move = chess.Move.from_uci(move_uci)
                    if move in self.board.legal_moves:
                        # Check for promotion
                        piece = self.board.piece_at(chess.parse_square(self.selected_square))
                        if piece and piece.piece_type == chess.PAWN:
                            # Check if moving to the last rank
                            to_square = chess.parse_square(square_name)
                            print(piece.color)
                            print(chess.square_rank(to_square))
                            if (piece.color and chess.square_rank(to_square) == 7) or (not piece.color and chess.square_rank(to_square) == 0):
                                # Create a new move with promotion to queen
                                move = chess.Move.from_uci(move_uci + "q")
                        
                        # Make the move
                        self.board.push(move)
                        self.last_move = move.uci()
                        self.move_history.append(move.uci())
                        self.ai_thinking = True  # Now it's AI's turn
                    else:
                        # If move is not legal, try selecting a new piece
                        square = chess.parse_square(square_name)
                        piece = self.board.piece_at(square)
                        if piece and ((piece.color and self.player_white) or (not piece.color and not self.player_white)):
                            self.selected_square = square_name
                        else:
                            self.selected_square = None
                except ValueError:
                    # Invalid move format, reset selection
                    self.selected_square = None
    
    def make_ai_move(self):
        """Make a move for the AI."""
        if self.board.is_game_over():
            self.game_over = True
            return
        
        # Determine AI's color
        ai_color = 'black' if self.player_white else 'white'
        
        # Find best move
        best_move, elapsed = self.engine.find_best_move(self.board, ai_color, self.use_cnn)
        
        if best_move:
            # Apply the move
            move_uci = best_move.uci()
            self.board.push(best_move)
            self.last_move = move_uci
            self.move_history.append(move_uci)
            print(f"AI Move: {move_uci} (calculated in {elapsed:.2f} seconds)")
        
        # Check if game is over
        if self.board.is_game_over():
            self.game_over = True
    
    def run(self):
        """Main game loop."""
        clock = pygame.time.Clock()
        running = True
        
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_mouse_click(event.pos)
            
            # Make AI move if it's AI's turn
            if self.ai_thinking and not self.game_over:
                self.ai_thinking = False  # Reset flag
                self.make_ai_move()
            
            # If player is not the current turn, AI should move
            if ((self.board.turn and not self.player_white) or (not self.board.turn and self.player_white)) and not self.game_over and not self.ai_thinking:
                self.ai_thinking = True
            
            # Draw everything
            self.screen.fill(self.WHITE)
            self.draw_board()
            self.draw_info_panel()
            
            pygame.display.flip()
            clock.tick(30)
        
        pygame.quit()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Chess AI with CNN and Minimax')
    parser.add_argument('--elo', choices=['700', '1100', '1200'], default='1200', help='ELO rating of the CNN model to use')
    parser.add_argument('--depth', type=int, default=3, help='Minimax search depth')
    
    args = parser.parse_args()
    
    game = ChessGame(elo=args.elo, depth=args.depth)
    game.run()

if __name__ == "__main__":
    main()