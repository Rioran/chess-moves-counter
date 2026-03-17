from constants import START


class State:
    """Holds all mutable application state for the chess board editor."""

    def __init__(self):
        self.board = [r[:] for r in START]
        self.white_persp = True
        self.start_active = True
        self.drag_src = {}
        self.drop_handled = False
        self.stats_shown = False
        self.stats = None  # (total, mate, targets, in_check) or None
        self.ep_pawn = None  # (row, col) of pawn eligible for en passant capture
        self.castle_w = True  # White king retains castling rights
        self.castle_b = True  # Black king retains castling rights


state = State()
