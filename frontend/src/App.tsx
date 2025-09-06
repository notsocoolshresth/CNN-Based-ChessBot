import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Chessboard } from 'react-chessboard';
import { Chess, Square } from 'chess.js';

interface ApiResponse {
  move: string;
  time_taken: number;
}

const App: React.FC = () => {
  const game = useRef(new Chess());
  const [currentFen, setCurrentFen] = useState(game.current.fen());
  const [humanColor, setHumanColor] = useState<'white' | 'black' | null>(null);
  const [status, setStatus] = useState<string>('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [isDarkMode, setIsDarkMode] = useState<boolean>(false);

  // Load dark mode preference
  useEffect(() => {
    const savedMode = localStorage.getItem('chess-dark-mode');
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;

    setIsDarkMode(savedMode ? JSON.parse(savedMode) : prefersDark);
  }, []);

  // Persist dark mode
  useEffect(() => {
    localStorage.setItem('chess-dark-mode', JSON.stringify(isDarkMode));
    document.body.style.transition = 'background-color 0.3s, color 0.3s';
    document.body.style.backgroundColor = isDarkMode ? '#1a1a1a' : '#fafafa';
    document.body.style.color = isDarkMode ? '#e6e6e6' : '#2d3748';
  }, [isDarkMode]);

  // Make a move (no sound)
  const makeMove = (move: { from: Square; to: Square; promotion?: string }) => {
    try {
      const result = game.current.move(move);
      if (result) {
        setCurrentFen(game.current.fen());
        return true;
      }
      return false;
    } catch (e) {
      return false;
    }
  };

  const onDrop = (sourceSquare: Square, targetSquare: Square) => {
    if (game.current.turn() !== humanColor?.[0] || loading || game.current.isGameOver()) return false;

    const move = { from: sourceSquare, to: targetSquare, promotion: 'q' };
    const isValid = makeMove(move);
    if (!isValid) return false;

    updateGameStatus();
    if (!game.current.isGameOver() && game.current.turn() === (humanColor === 'white' ? 'b' : 'w')) {
      setTimeout(getAiMove, 300);
    }
    return true;
  };

  const getAiMove = async () => {
    if (game.current.isGameOver() || loading) return;

    setLoading(true);
    setStatus('AI thinking...');
    setError(null);

    try {
      const fen = game.current.fen();
      const aiPlayer = humanColor === 'white' ? 'black' : 'white';
      const response = await fetch('http://localhost:5000/move', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ fen, player: aiPlayer, mode: 'cnn_minimax' }),
      });

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.error || 'API request failed');
      }

      const data: ApiResponse = await response.json();
      const aiMove = {
        from: data.move.slice(0, 2) as Square,
        to: data.move.slice(2, 4) as Square,
        promotion: data.move.slice(4) || 'q',
      };
      const isValid = makeMove(aiMove);
      if (!isValid) throw new Error('Invalid AI move received');

      updateGameStatus();
    } catch (err) {
      setError((err as Error).message);
      setStatus('Error occurred. Reset to continue.');
    } finally {
      setLoading(false);
    }
  };

  const undoMove = () => {
    if (loading || game.current.history().length === 0) return;

    game.current.undo();
    setCurrentFen(game.current.fen());
    updateGameStatus();
  };

  const updateGameStatus = useCallback(() => {
    const turnColor = game.current.turn() === 'w' ? 'White' : 'Black';
    const isHumanTurn = (humanColor === 'white' && game.current.turn() === 'w') || (humanColor === 'black' && game.current.turn() === 'b');

    if (game.current.isCheckmate()) {
      const winner = turnColor === 'White' ? 'Black' : 'White';
      setStatus(`Checkmate! ${winner} wins.`);
    } else if (game.current.isStalemate()) {
      setStatus('Stalemate! Draw.');
    } else if (game.current.isDraw()) {
      setStatus('Draw!');
    } else if (game.current.inCheck()) {
      setStatus(`${turnColor} is in check. ${isHumanTurn ? 'Your turn' : "AI's turn"} (${turnColor}).`);
    } else {
      setStatus(`${isHumanTurn ? 'Your turn' : "AI's turn"} (${turnColor}).`);
    }
  }, [humanColor]);

  const resetGame = () => {
    game.current.reset();
    setCurrentFen(game.current.fen());
    setHumanColor(null);
    setStatus('');
    setError(null);
    setLoading(false);
  };

  const chooseSide = (color: 'white' | 'black') => {
    setHumanColor(color);
    updateGameStatus();
    if (color === 'black') {
      setTimeout(getAiMove, 300);
    }
  };

  useEffect(() => {
    if (humanColor) {
      updateGameStatus();
    }
  }, [humanColor, updateGameStatus]);

  // Full move history in SAN
  const moveHistory = game.current.history({ verbose: true });
  const formattedMoves = [];
  for (let i = 0; i < moveHistory.length; i += 2) {
    const moveNum = Math.floor(i / 2) + 1;
    const whiteMove = moveHistory[i]?.san || '';
    const blackMove = moveHistory[i + 1]?.san || '...';
    formattedMoves.push(`${moveNum}. ${whiteMove} ${blackMove}`);
  }

  const isAiTurn = !game.current.isGameOver() && !loading && game.current.turn() === (humanColor === 'white' ? 'b' : 'w');

  // Theme colors
  const bg = isDarkMode ? '#1a1a1a' : '#fafafa';
  const cardBg = isDarkMode ? '#2d2d2d' : '#ffffff';
  const text = isDarkMode ? '#e6e6e6' : '#2d3748';
  const muted = isDarkMode ? '#a0a0a0' : '#718096';
  const border = isDarkMode ? '#444' : '#e2e8f0';

  return (
    <div
      style={{
        maxWidth: '720px',
        margin: '24px auto',
        padding: '20px 16px',
        fontFamily: '"Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif',
        backgroundColor: bg,
        color: text,
        minHeight: '100vh',
        transition: 'background-color 0.3s, color 0.3s',
      }}
    >
      {/* Dark Mode Toggle */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: '24px',
        }}
      >
        <h1
          style={{
            fontSize: '24px',
            fontWeight: '600',
            margin: '0',
            color: text,
          }}
        >
          Chess vs AI
        </h1>
        <label
          style={{
            fontSize: '13px',
            color: muted,
            display: 'flex',
            alignItems: 'center',
            cursor: 'pointer',
          }}
        >
          <input
            type="checkbox"
            checked={isDarkMode}
            onChange={() => setIsDarkMode(prev => !prev)}
            style={{ marginRight: '6px' }}
          />
          Dark Mode
        </label>
      </div>

      {!humanColor ? (
        <div
          style={{
            textAlign: 'center',
            padding: '36px 20px',
            backgroundColor: cardBg,
            borderRadius: '12px',
            boxShadow: `0 4px 12px ${isDarkMode ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.08)'}`,
            marginBottom: '24px',
            border: `1px solid ${border}`,
          }}
        >
          <h2
            style={{
              fontSize: '18px',
              fontWeight: '500',
              color: text,
              marginBottom: '24px',
            }}
          >
            Choose your color
          </h2>
          <div
            style={{
              display: 'flex',
              justifyContent: 'center',
              gap: '20px',
              flexWrap: 'wrap',
            }}
          >
            <button
              onClick={() => chooseSide('white')}
              style={{
                padding: '12px 28px',
                fontSize: '15px',
                fontWeight: '500',
                backgroundColor: '#2d3748',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                transition: 'background-color 0.15s ease',
              }}
              onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#1a202c')}
              onMouseOut={(e) => (e.currentTarget.style.backgroundColor = '#2d3748')}
            >
              Play as White
            </button>
            <button
              onClick={() => chooseSide('black')}
              style={{
                padding: '12px 28px',
                fontSize: '15px',
                fontWeight: '500',
                backgroundColor: '#4a5568',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                transition: 'background-color 0.15s ease',
              }}
              onMouseOver={(e) => (e.currentTarget.style.backgroundColor = '#2d3748')}
              onMouseOut={(e) => (e.currentTarget.style.backgroundColor = '#4a5568')}
            >
              Play as Black
            </button>
          </div>
        </div>
      ) : (
        <>
          <div
            style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '20px',
            }}
          >
            {/* Board & Controls */}
            <div
              style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
              }}
            >
              <div
                style={{
                  width: '100%',
                  maxWidth: '500px',
                  borderRadius: '8px',
                  overflow: 'hidden',
                  boxShadow: `0 4px 12px ${isDarkMode ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.1)'}`,
                  backgroundColor: cardBg,
                  padding: '10px',
                  border: `1px solid ${border}`,
                }}
              >
                <Chessboard
                  position={currentFen}
                  onPieceDrop={onDrop}
                  boardOrientation={humanColor}
                  arePiecesDraggable={!loading && !game.current.isGameOver() && game.current.turn() === humanColor[0]}
                  customBoardStyle={{
                    borderRadius: '6px',
                  }}
                />
              </div>

              <div
                style={{
                  padding: '12px 16px',
                  backgroundColor: game.current.isGameOver()
                    ? isDarkMode ? '#552222' : '#fff5f5'
                    : loading
                    ? isDarkMode ? '#443300' : '#fffbeb'
                    : isDarkMode ? '#0a3315' : '#f0fff4',
                  color: game.current.isGameOver()
                    ? '#fca5a5'
                    : loading
                    ? '#fcd34d'
                    : isDarkMode ? '#68d391' : '#276749',
                  fontSize: '14.5px',
                  textAlign: 'center',
                  borderRadius: '6px',
                  fontWeight: '500',
                  margin: '16px 0',
                  border: `1px solid ${
                    game.current.isGameOver()
                      ? isDarkMode ? '#772222' : '#fed7d7'
                      : loading
                      ? isDarkMode ? '#996600' : '#fbd38d'
                      : isDarkMode ? '#0d5522' : '#c6f6d5'
                  }`,
                }}
              >
                {status}
              </div>

              {error && (
                <div
                  style={{
                    padding: '12px 16px',
                    backgroundColor: isDarkMode ? '#552222' : '#fff5f5',
                    color: '#fca5a5',
                    fontSize: '14px',
                    textAlign: 'center',
                    borderRadius: '6px',
                    marginBottom: '16px',
                    border: `1px solid ${isDarkMode ? '#772222' : '#fed7d7'}`,
                  }}
                >
                  {error}
                </div>
              )}

              <div
                style={{
                  display: 'flex',
                  justifyContent: 'center',
                  gap: '10px',
                  flexWrap: 'wrap',
                  marginBottom: '20px',
                }}
              >
                <button
                  onClick={undoMove}
                  disabled={loading || game.current.history().length === 0 || game.current.isGameOver()}
                  style={{
                    padding: '8px 14px',
                    fontSize: '13.5px',
                    fontWeight: '500',
                    backgroundColor:
                      loading || game.current.history().length === 0 || game.current.isGameOver()
                        ? isDarkMode ? '#4a4a4a' : '#e2e8f0'
                        : isDarkMode ? '#4a5568' : '#4a5568',
                    color:
                      loading || game.current.history().length === 0 || game.current.isGameOver()
                        ? isDarkMode ? '#777' : '#a0aec0'
                        : 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor:
                      loading || game.current.history().length === 0 || game.current.isGameOver()
                        ? 'not-allowed'
                        : 'pointer',
                    transition: 'background-color 0.15s ease',
                  }}
                >
                  Undo Move
                </button>

                {isAiTurn && (
                  <button
                    onClick={getAiMove}
                    style={{
                      padding: '8px 14px',
                      fontSize: '13.5px',
                      fontWeight: '500',
                      backgroundColor: isDarkMode ? '#48bb78' : '#68d391',
                      color: '#1a202c',
                      border: 'none',
                      borderRadius: '6px',
                      cursor: 'pointer',
                      transition: 'background-color 0.15s ease',
                    }}
                  >
                    Let AI Move
                  </button>
                )}

                <button
                  onClick={resetGame}
                  style={{
                    padding: '8px 14px',
                    fontSize: '13.5px',
                    fontWeight: '500',
                    backgroundColor: isDarkMode ? '#e53e3e' : '#e53e3e',
                    color: 'white',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    transition: 'background-color 0.15s ease',
                  }}
                >
                  Reset Game
                </button>
              </div>
            </div>

            {/* Move History Panel */}
            <div
              style={{
                backgroundColor: cardBg,
                padding: '16px',
                borderRadius: '8px',
                boxShadow: `0 1px 6px ${isDarkMode ? 'rgba(0,0,0,0.3)' : 'rgba(0,0,0,0.06)'}`,
                border: `1px solid ${border}`,
              }}
            >
              <h3
                style={{
                  margin: '0 0 8px 0',
                  fontSize: '15px',
                  color: text,
                  fontWeight: '600',
                }}
              >
                Move History
              </h3>
              <div
                style={{
                  maxHeight: '200px',
                  overflowY: 'auto',
                  fontSize: '13.5px',
                  color: muted,
                  lineHeight: '1.6',
                  textAlign: 'left',
                  padding: '4px 0',
                  fontFamily: 'monospace',
                }}
              >
                {formattedMoves.length > 0 ? (
                  formattedMoves.map((move, i) => (
                    <div key={i} style={{ whiteSpace: 'nowrap' }}>
                      {move}
                    </div>
                  ))
                ) : (
                  <div style={{ fontStyle: 'italic' }}>No moves yet</div>
                )}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

export default App;