# Chess Moves Counter

A browser-based chess board editor that counts legal moves from any custom position. Built with pure Python in the browser via [Brython](https://brython.info/) — no backend required.

Hosted on https://rioran.github.io/chess-moves-counter/

![Move count demo](count_demo.jpg)

## Features

**Board setup**
- Drag pieces from the side panels onto the board to set up any position
- Drag pieces between squares or off the board to remove them
- Toggle between the standard starting position and an empty board (🗑 / ↺)
- Flip the board to view from White's or Black's perspective (⇅)
- Select whose turn it is with the Go button (White / Black)
- Fully playable on mobile with touch drag-and-drop

**Move counting**
- Count legal moves for the active side, including castling and en passant
- Each square shows how many pieces can land on it next move
- A shield icon (⛨) on the king marks retained castling rights
- Double arrow on a pawn marks it as capturable en passant; arrows flip with board perspective
- Castling squares for both king and rook are highlighted in the move count

**Multi-ply tree walk**
- Depth selector (1–6 plies) next to the Count button
- Per-ply stats show total moves and newly discovered checkmates
- Duplicate mate positions are deduplicated — stats show unique mates and total occurrences
- Click a mate count to cycle through unique mate positions; occurrence count shown while cycling
- A red ✕ marks the mated king during preview; the board is locked until exited

## Local development

```bash
python3 -m http.server 8000
```

Then open http://localhost:8000 in your browser.

## Author

[rioran](https://www.linkedin.com/in/rioran/) — [source code](https://github.com/Rioran/chess-moves-counter)

