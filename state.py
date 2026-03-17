from constants import START


class State:
    """Holds all mutable application state for the chess board editor."""

    def __init__(self):
        self.board = [r[:] for r in START]
        self.white_persp = True
        self.start_active = True
        self.drag_src = {}
        self.drop_handled = False
        # Move counting
        self.stats_shown = False
        self.turn_stats = []     # list of {color, total, mate_count, mates, truncated}
        self.targets_combined = {}  # (row, col) -> count across all plies
        self.computing = False
        # Mate preview
        self.mate_view = None    # {ply_idx, mate_idx} or None
        self.board_saved = None  # board copy before entering mate preview
        # Board meta-state
        self.ep_pawn = None      # (row, col) of pawn eligible for en passant
        self.castle_w = True     # White king retains castling rights
        self.castle_b = True     # Black king retains castling rights


state = State()
