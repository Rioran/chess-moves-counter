def opponent(color):
    """Return the opposing color: 'b' for 'w' and vice versa."""
    return "b" if color == "w" else "w"


def in_bounds(r, c):
    """Return True if (r, c) is a valid board coordinate."""
    return 0 <= r < 8 and 0 <= c < 8


def find_king(board, color):
    """Return (row, col) of color's king, or None if absent from the board."""
    for r in range(8):
        for c in range(8):
            if board[r][c] == color + "K":
                return (r, c)
    return None


def is_attacked(board, r, c, by_color):
    """Return True if square (r, c) is attacked by any piece of by_color."""
    # Pawns
    if by_color == "w":
        for dc in [-1, 1]:
            if in_bounds(r + 1, c + dc) and board[r + 1][c + dc] == "wP":
                return True
    else:
        for dc in [-1, 1]:
            if in_bounds(r - 1, c + dc) and board[r - 1][c + dc] == "bP":
                return True
    # Knights
    for dr, dc in [
        (-2, -1),
        (-2, 1),
        (-1, -2),
        (-1, 2),
        (1, -2),
        (1, 2),
        (2, -1),
        (2, 1),
    ]:
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc) and board[nr][nc] == by_color + "N":
            return True
    # Rooks / Queens (orthogonal)
    for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
        for d in range(1, 8):
            nr, nc = r + dr * d, c + dc * d
            if not in_bounds(nr, nc):
                break
            p = board[nr][nc]
            if p:
                if p[0] == by_color and p[1] in ("R", "Q"):
                    return True
                break
    # Bishops / Queens (diagonal)
    for dr, dc in [(1, 1), (1, -1), (-1, 1), (-1, -1)]:
        for d in range(1, 8):
            nr, nc = r + dr * d, c + dc * d
            if not in_bounds(nr, nc):
                break
            p = board[nr][nc]
            if p:
                if p[0] == by_color and p[1] in ("B", "Q"):
                    return True
                break
    # King
    for dr, dc in [
        (-1, -1),
        (-1, 0),
        (-1, 1),
        (0, -1),
        (0, 1),
        (1, -1),
        (1, 0),
        (1, 1),
    ]:
        nr, nc = r + dr, c + dc
        if in_bounds(nr, nc) and board[nr][nc] == by_color + "K":
            return True
    return False


def is_in_check(board, color):
    """Return True if color's king is currently under attack."""
    king = find_king(board, color)
    if not king:
        return False
    return is_attacked(board, king[0], king[1], opponent(color))


def apply_move(board, move):
    """
    Return a new board with move applied without mutating the original.

    Handles normal moves, en passant ('ep'), castling ('castle_k' /
    'castle_q'), and pawn promotion ('promo', always promotes to queen).
    """
    fr, fc, tr, tc, special = move
    b = [row[:] for row in board]
    piece = b[fr][fc]
    b[tr][tc] = piece
    b[fr][fc] = None
    if special == "ep":
        b[fr][tc] = None  # remove captured pawn
    elif special == "castle_k":
        b[fr][7] = None
        b[fr][5] = piece[0] + "R"
    elif special == "castle_q":
        b[fr][0] = None
        b[fr][3] = piece[0] + "R"
    elif special == "promo":
        b[tr][tc] = piece[0] + "Q"
    return b


def pseudo_legal(board, color, castling, ep_file):
    """
    Return all pseudo-legal moves for color without filtering for check.

    Each move is a 5-tuple (from_row, from_col, to_row, to_col, special)
    where special is one of: None, 'ep', 'castle_k', 'castle_q', 'promo'.
    castling is a set of strings e.g. {'wK', 'wQ', 'bK', 'bQ'}.
    ep_file is the column index of an en-passant target square, or None.
    """
    moves = []
    opp = opponent(color)
    pd = -1 if color == "w" else 1  # pawn direction
    psr = 6 if color == "w" else 1  # pawn start row
    ppr = 0 if color == "w" else 7  # pawn promotion row
    ep_r = 3 if color == "w" else 4  # row where en-passant capture is possible

    for r in range(8):
        for c in range(8):
            p = board[r][c]
            if not p or p[0] != color:
                continue
            pt = p[1]

            if pt == "P":
                nr = r + pd
                # Forward one
                if in_bounds(nr, c) and board[nr][c] is None:
                    moves.append((r, c, nr, c, "promo" if nr == ppr else None))
                    # Forward two from start
                    if r == psr:
                        nr2 = r + 2 * pd
                        if in_bounds(nr2, c) and board[nr2][c] is None:
                            moves.append((r, c, nr2, c, None))
                # Diagonal captures
                for dc in [-1, 1]:
                    nc, nr = c + dc, r + pd
                    if in_bounds(nr, nc):
                        t = board[nr][nc]
                        if t and t[0] == opp:
                            moves.append((r, c, nr, nc, "promo" if nr == ppr else None))
                        if ep_file is not None and nc == ep_file and r == ep_r:
                            moves.append((r, c, nr, nc, "ep"))

            elif pt == "N":
                for dr, dc in [
                    (-2, -1),
                    (-2, 1),
                    (-1, -2),
                    (-1, 2),
                    (1, -2),
                    (1, 2),
                    (2, -1),
                    (2, 1),
                ]:
                    nr, nc = r + dr, c + dc
                    if in_bounds(nr, nc) and (
                        board[nr][nc] is None or board[nr][nc][0] == opp
                    ):
                        moves.append((r, c, nr, nc, None))

            elif pt in ("B", "R", "Q"):
                dirs = []
                if pt in ("R", "Q"):
                    dirs += [(0, 1), (0, -1), (1, 0), (-1, 0)]
                if pt in ("B", "Q"):
                    dirs += [(1, 1), (1, -1), (-1, 1), (-1, -1)]
                for dr, dc in dirs:
                    for d in range(1, 8):
                        nr, nc = r + dr * d, c + dc * d
                        if not in_bounds(nr, nc):
                            break
                        t = board[nr][nc]
                        if t is None:
                            moves.append((r, c, nr, nc, None))
                        elif t[0] == opp:
                            moves.append((r, c, nr, nc, None))
                            break
                        else:
                            break

            elif pt == "K":
                for dr, dc in [
                    (-1, -1),
                    (-1, 0),
                    (-1, 1),
                    (0, -1),
                    (0, 1),
                    (1, -1),
                    (1, 0),
                    (1, 1),
                ]:
                    nr, nc = r + dr, c + dc
                    if in_bounds(nr, nc) and (
                        board[nr][nc] is None or board[nr][nc][0] == opp
                    ):
                        moves.append((r, c, nr, nc, None))
                # Castling
                back = 7 if color == "w" else 0
                if r == back and c == 4:
                    if color + "K" in castling:
                        if (
                            board[back][5] is None
                            and board[back][6] is None
                            and board[back][7] == color + "R"
                        ):
                            moves.append((r, c, back, 6, "castle_k"))
                    if color + "Q" in castling:
                        if (
                            board[back][1] is None
                            and board[back][2] is None
                            and board[back][3] is None
                            and board[back][0] == color + "R"
                        ):
                            moves.append((r, c, back, 2, "castle_q"))
    return moves


def legal_moves(board, color, castling, ep_file):
    """
    Return all legal moves for color, filtering out moves that leave the
    king in check. Also verifies that the king does not pass through an
    attacked square when castling.
    """
    result = []
    opp = opponent(color)
    for move in pseudo_legal(board, color, castling, ep_file):
        fr, fc, tr, tc, special = move
        if special in ("castle_k", "castle_q"):
            if is_in_check(board, color):
                continue
            back = 7 if color == "w" else 0
            pass_c = 5 if special == "castle_k" else 3
            if is_attacked(board, back, pass_c, opp):
                continue
        nb = apply_move(board, move)
        if not is_in_check(nb, color):
            result.append(move)
    return result


def detect_castling(board):
    """Infer castling rights from piece positions."""
    c = set()
    if board[7][4] == "wK":
        if board[7][7] == "wR":
            c.add("wK")
        if board[7][0] == "wR":
            c.add("wQ")
    if board[0][4] == "bK":
        if board[0][7] == "bR":
            c.add("bK")
        if board[0][0] == "bR":
            c.add("bQ")
    return c


def count_moves(board, color):
    """
    Return move statistics for color as (total, mate_count, targets, in_check).

    total      -- number of legal moves available.
    mate_count -- subset of moves that deliver immediate checkmate.
    targets    -- dict mapping (row, col) to the number of moves landing there.
    in_check   -- whether color's king is currently in check.
    """
    castling = detect_castling(board)
    moves = legal_moves(board, color, castling, None)
    in_chk = is_in_check(board, color)
    opp = opponent(color)

    targets = {}
    mate_count = 0

    for move in moves:
        tr, tc = move[2], move[3]
        targets[(tr, tc)] = targets.get((tr, tc), 0) + 1

        nb = apply_move(board, move)
        if is_in_check(nb, opp):
            opp_castling = detect_castling(nb)
            if not legal_moves(nb, opp, opp_castling, None):
                mate_count += 1

    return len(moves), mate_count, targets, in_chk
