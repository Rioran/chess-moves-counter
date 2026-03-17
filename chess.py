from browser import document, html, bind, timer

from constants import ORDER, W_CHR, B_CHR, START
from state import state
from moves import count_tree, apply_move, find_king, is_in_check


# ── Helpers ────────────────────────────────────────────────────────────────────
def glyph(p):
    """Return the Unicode chess glyph for piece code p (e.g. 'wK' → '♚')."""
    return (W_CHR if p[0] == "w" else B_CHR)[p[1]] if p else ""


def find_sq(el):
    """Traverse up the DOM to find the nearest sq-{row}-{col} element."""
    while el:
        try:
            if el.id and el.id.startswith("sq-"):
                return el
        except Exception:
            pass
        el = el.parentElement
    return None


def clear_hover():
    """Remove all drag-over and label-highlight CSS classes from the DOM."""
    for el in document.querySelectorAll(".drag-over"):
        el.classList.remove("drag-over")
    for el in document.querySelectorAll(".label-highlight"):
        el.classList.remove("label-highlight")


def drop_stats():
    """Clear all computed stats and mate-view state."""
    state.stats_shown = False
    state.turn_stats = []
    state.targets_combined = {}
    state.computing = False
    state.mate_view = None
    state.board_saved = None


def current_color():
    """Return 'w' or 'b' based on the current state of the whose-turn button."""
    return "w" if document["wtg-btn"].textContent == "Go, White!" else "b"


# ── Mate preview helpers ────────────────────────────────────────────────────────
def _apply_mate_path(base_board, path):
    """Apply a sequence of moves to base_board and store the result in state.board."""
    b = [r[:] for r in base_board]
    for move in path:
        b = apply_move(b, move)
    state.board = b


def on_mate_click(ev):
    """Cycle through stored mate positions for the clicked ply."""
    ply_idx = int(ev.target.attrs["data-ply"])
    stat = state.turn_stats[ply_idx]
    mates = stat["mates"]
    if not mates:
        return

    if state.mate_view and state.mate_view["ply_idx"] == ply_idx:
        next_idx = state.mate_view["mate_idx"] + 1
        if next_idx >= len(mates):
            # Restore board and exit mate view
            state.board = state.board_saved
            state.board_saved = None
            state.mate_view = None
        else:
            state.mate_view["mate_idx"] = next_idx
            _apply_mate_path(state.board_saved, mates[next_idx])
    else:
        # Enter mate view (possibly switching from a different ply)
        if state.mate_view:
            state.board = state.board_saved
        else:
            state.board_saved = [r[:] for r in state.board]
        state.mate_view = {"ply_idx": ply_idx, "mate_idx": 0}
        _apply_mate_path(state.board_saved, mates[0])

    render()


def update_move_state(src_type, piece, src_row, src_col, dst_row, dst_col):
    """Update en passant pawn and castling rights after a piece is placed or moved."""
    color, kind = piece[0], piece[1]
    # En passant: only a 2-square pawn advance from its starting row qualifies
    if src_type == "board" and kind == "P":
        if color == "w" and src_row == 6 and dst_row == 4:
            state.ep_pawn = (dst_row, dst_col)
        elif color == "b" and src_row == 1 and dst_row == 3:
            state.ep_pawn = (dst_row, dst_col)
        else:
            state.ep_pawn = None
    else:
        state.ep_pawn = None
    # Castling: only a panel placement on the king's home square grants rights
    if kind == "K":
        if color == "w":
            state.castle_w = src_type == "panel" and dst_row == 7 and dst_col == 4
        else:
            state.castle_b = src_type == "panel" and dst_row == 0 and dst_col == 4


# ── Drag handlers ──────────────────────────────────────────────────────────────
def panel_dragstart(ev):
    """Record a drag originating from a piece panel (copy semantics)."""
    piece = ev.target.attrs["data-piece"]
    ev.dataTransfer.setData("text", piece)
    ev.dataTransfer.effectAllowed = "copy"
    state.drag_src.update({"type": "panel", "piece": piece})


def board_dragstart(ev):
    """Record a drag originating from the board (move semantics)."""
    piece = ev.target.attrs["data-piece"]
    row = int(ev.target.attrs["data-row"])
    col = int(ev.target.attrs["data-col"])
    ev.dataTransfer.setData("text", piece)
    ev.dataTransfer.effectAllowed = "move"
    state.drag_src.update({"type": "board", "piece": piece, "row": row, "col": col})
    ev.stopPropagation()


def any_dragend(ev):
    """Clean up after any drag ends; remove the piece if it was dropped off-board."""
    clear_hover()
    if not state.drop_handled and state.drag_src.get("type") == "board":
        state.board[state.drag_src["row"]][state.drag_src["col"]] = None
        state.ep_pawn = None
        state.drag_src.clear()
        drop_stats()
        render()
    else:
        state.drag_src.clear()
    state.drop_handled = False


def sq_dragenter(ev):
    """Highlight the hovered square and its rank/file labels on drag enter."""
    ev.preventDefault()
    clear_hover()
    sq = find_sq(ev.target)
    if sq:
        sq.classList.add("drag-over")
        rank = str(8 - int(sq.attrs["data-row"]))
        file = chr(ord("a") + int(sq.attrs["data-col"]))
        for el in document.querySelectorAll(f'[data-rank="{rank}"]'):
            el.classList.add("label-highlight")
        for el in document.querySelectorAll(f'[data-file="{file}"]'):
            el.classList.add("label-highlight")


def sq_dragover(ev):
    """Allow a drop by preventing the default dragover behaviour."""
    ev.preventDefault()


def sq_dragleave(ev):
    """Remove the drag-over highlight when the cursor leaves a square."""
    sq = find_sq(ev.target)
    if not sq:
        return
    related = ev.relatedTarget
    if related:
        try:
            if sq.contains(related):
                return
        except Exception:
            pass
    sq.classList.remove("drag-over")


def sq_drop(ev):
    """Place the dragged piece on the target square and update the board state."""
    ev.preventDefault()
    clear_hover()
    sq = find_sq(ev.target)
    if not sq or not state.drag_src:
        return
    dr = int(sq.attrs["data-row"])
    dc = int(sq.attrs["data-col"])
    piece = state.drag_src.get("piece")
    if not piece:
        return
    src_type = state.drag_src.get("type")
    src_row = state.drag_src.get("row")
    src_col = state.drag_src.get("col")
    if src_type == "board":
        if src_row == dr and src_col == dc:
            state.drag_src.clear()
            return
        state.board[src_row][src_col] = None
    state.board[dr][dc] = piece
    update_move_state(src_type, piece, src_row, src_col, dr, dc)
    state.drop_handled = True
    state.drag_src.clear()
    drop_stats()
    render()


# ── Touch drag ─────────────────────────────────────────────────────────────────
_touch = {}


def _sq_from_point(x, y):
    """Return the board square element at viewport coordinates (x, y), or None."""
    ghost = _touch.get("ghost")
    if ghost:
        ghost.style.display = "none"
    el = document.elementFromPoint(x, y)
    if ghost:
        ghost.style.display = ""
    return find_sq(el)


def touch_start(ev):
    """Start a touch drag from a piece element (panel or board)."""
    if _touch:
        return  # another finger already dragging
    ev.preventDefault()
    if not ev.touches.length:
        return
    touch = ev.touches.item(0)
    target = ev.target
    piece = target.attrs.get("data-piece")
    if not piece:
        return
    if "data-row" in target.attrs:
        _touch.update(
            {
                "type": "board",
                "piece": piece,
                "row": int(target.attrs["data-row"]),
                "col": int(target.attrs["data-col"]),
            }
        )
    else:
        _touch.update({"type": "panel", "piece": piece})
    sq_el = document.querySelector(".square")
    size = int(sq_el.offsetWidth) if sq_el else 42
    _touch["size"] = size
    color_cls = "piece-w" if piece[0] == "w" else "piece-b"
    ghost = html.SPAN(glyph(piece))
    ghost.classList.add("touch-ghost")
    ghost.classList.add(color_cls)
    ghost.style.fontSize = f"{size}px"
    ghost.style.left = f"{touch.clientX - size // 2}px"
    ghost.style.top = f"{touch.clientY - size}px"
    document.body <= ghost
    _touch["ghost"] = ghost


def touch_move(ev):
    """Move the ghost element and highlight the square under the finger."""
    if not _touch:
        return
    ev.preventDefault()
    touch = ev.touches.item(0)
    ghost = _touch.get("ghost")
    size = _touch.get("size", 42)
    if ghost:
        ghost.style.left = f"{touch.clientX - size // 2}px"
        ghost.style.top = f"{touch.clientY - size}px"
    sq = _sq_from_point(touch.clientX, touch.clientY)
    clear_hover()
    if sq:
        sq.classList.add("drag-over")
        rank = str(8 - int(sq.attrs["data-row"]))
        file_chr = chr(ord("a") + int(sq.attrs["data-col"]))
        for label in document.querySelectorAll(f'[data-rank="{rank}"]'):
            label.classList.add("label-highlight")
        for label in document.querySelectorAll(f'[data-file="{file_chr}"]'):
            label.classList.add("label-highlight")


def touch_end(ev):
    """Drop the piece on the square under the finger, or remove it if off-board."""
    if not _touch:
        return
    try:
        ev.preventDefault()
        ghost = _touch.pop("ghost", None)
        if ghost:
            ghost.style.display = "none"
        clear_hover()
        touch = ev.changedTouches.item(0)
        sq = _sq_from_point(touch.clientX, touch.clientY)
        piece = _touch.get("piece")
        if piece:
            if sq:
                dr = int(sq.attrs["data-row"])
                dc = int(sq.attrs["data-col"])
                if _touch.get("type") == "board":
                    sr, sc = _touch["row"], _touch["col"]
                    if not (sr == dr and sc == dc):
                        state.board[sr][sc] = None
                state.board[dr][dc] = piece
                update_move_state(
                    _touch.get("type"),
                    piece,
                    _touch.get("row"),
                    _touch.get("col"),
                    dr,
                    dc,
                )
            elif _touch.get("type") == "board":
                state.board[_touch["row"]][_touch["col"]] = None
                state.ep_pawn = None
            drop_stats()
        timer.set_timeout(render, 0)
    finally:
        _touch.clear()


def build_panel(color):
    """Build and return the draggable piece panel for the given color ('w'/'b')."""
    in_mate_view = state.mate_view is not None
    panel = html.DIV(Class="piece-panel")
    cmap = W_CHR if color == "w" else B_CHR
    for p in ORDER:
        code = color + p
        item = html.DIV(cmap[p], Class=f"piece-item piece-{color}")
        item.attrs["data-piece"] = code
        if not in_mate_view:
            item.attrs["draggable"] = "true"
            item.bind("dragstart", panel_dragstart)
            item.bind("dragend", any_dragend)
            item.bind("touchstart", touch_start)
            item.bind("touchmove", touch_move)
            item.bind("touchend", touch_end)
        panel <= item
    return panel


def build_board():
    """Build and return the full board DOM element including rank/file labels."""
    rows = list(range(8)) if state.white_persp else list(range(7, -1, -1))
    cols = list(range(8)) if state.white_persp else list(range(7, -1, -1))
    targets = state.targets_combined if state.stats_shown else {}
    in_mate_view = state.mate_view is not None

    # Find the mated king when previewing a mate
    mated_pos = None
    if in_mate_view:
        for color in ("w", "b"):
            if is_in_check(state.board, color):
                mated_pos = find_king(state.board, color)
                break

    area = html.DIV(Class="board-area")
    br_wrap = html.DIV(Class="board-and-ranks")
    rank_col_l = html.DIV(Class="rank-col")
    rank_col_r = html.DIV(Class="rank-col")
    board_cls = "board board-preview" if in_mate_view else "board"
    board_el = html.DIV(Class=board_cls)

    # Top file row
    frow_top = html.DIV(Class="file-row file-row-top")
    for col in cols:
        fl = html.DIV(chr(ord("a") + col), Class="flabel")
        fl.attrs["data-file"] = chr(ord("a") + col)
        frow_top <= fl
    area <= frow_top

    for row in rows:
        rank_num = str(8 - row)
        rl = html.DIV(rank_num, Class="rlabel")
        rl.attrs["data-rank"] = rank_num
        rank_col_l <= rl
        rr = html.DIV(rank_num, Class="rlabel rlabel-r")
        rr.attrs["data-rank"] = rank_num
        rank_col_r <= rr
        row_div = html.DIV(Class="board-row")

        for col in cols:
            light = (row + col) % 2 == 0
            sq = html.DIV(Class="square " + ("sq-light" if light else "sq-dark"))
            sq.id = f"sq-{row}-{col}"
            sq.attrs["data-row"] = str(row)
            sq.attrs["data-col"] = str(col)

            piece = state.board[row][col]
            if piece:
                color_cls = "piece-w" if piece[0] == "w" else "piece-b"
                span = html.SPAN(glyph(piece), Class=f"piece-on-board {color_cls}")
                span.attrs["data-piece"] = piece
                span.attrs["data-row"] = str(row)
                span.attrs["data-col"] = str(col)
                if not in_mate_view:
                    span.attrs["draggable"] = "true"
                    span.bind("dragstart", board_dragstart)
                    span.bind("dragend", any_dragend)
                    span.bind("touchstart", touch_start)
                    span.bind("touchmove", touch_move)
                    span.bind("touchend", touch_end)
                sq <= span

                # En passant indicator: two arrows showing the pawn's travel direction
                if state.ep_pawn == (row, col):
                    arrow_up = (piece[0] == "w") == state.white_persp
                    arrow = "▲" if arrow_up else "▼"
                    ep_div = html.DIV(Class="ep-indicator")
                    ep_div <= html.SPAN(arrow, Class="ep-arrow")
                    ep_div <= html.SPAN(arrow, Class="ep-arrow")
                    sq <= ep_div

                # Castle indicator: tower icon when king retains castling rights
                if piece[1] == "K":
                    can_castle = (
                        piece[0] == "w" and row == 7 and col == 4 and state.castle_w
                    ) or (piece[0] == "b" and row == 0 and col == 4 and state.castle_b)
                    if can_castle:
                        sq <= html.SPAN("⛨", Class="castle-indicator")

            # Mated king cross (shown in mate preview)
            if mated_pos == (row, col):
                sq <= html.SPAN("✕", Class="king-cross")

            # Move-count badge
            count = targets.get((row, col), 0)
            if count > 0:
                sq <= html.SPAN(str(count), Class="sq-move-count")

            if not in_mate_view:
                sq.bind("dragenter", sq_dragenter)
                sq.bind("dragover", sq_dragover)
                sq.bind("dragleave", sq_dragleave)
                sq.bind("drop", sq_drop)
            row_div <= sq

        board_el <= row_div

    br_wrap <= rank_col_l
    br_wrap <= board_el
    br_wrap <= rank_col_r
    area <= br_wrap

    # Bottom file row
    frow_bot = html.DIV(Class="file-row")
    for col in cols:
        fl = html.DIV(chr(ord("a") + col), Class="flabel")
        fl.attrs["data-file"] = chr(ord("a") + col)
        frow_bot <= fl
    area <= frow_bot

    return area


def update_stats_bar():
    """Rebuild the stats bar from current state."""
    bar = document["stats-bar"]
    bar.clear()

    if state.computing:
        bar <= html.SPAN("Computing…")
        bar.classList.remove("hidden")
        return

    if not state.stats_shown or not state.turn_stats:
        bar.classList.add("hidden")
        return

    bar.classList.remove("hidden")
    for i, stat in enumerate(state.turn_stats):
        if stat["color"] is None:
            continue
        color_name = "White" if stat["color"] == "w" else "Black"
        total = stat["total"]
        mc = stat["mate_count"]
        mates = stat["mates"]
        line = html.DIV(Class="turn-line")
        prefix = f"Move {i + 1} - {color_name}: {total} moves"
        if mc > 0:
            s = "" if mc == 1 else "s"
            if i == 0:
                mate_label = f"{mc} mate{s}"
            else:
                mate_label = f"new {mc} mate{s}"
            if state.mate_view and state.mate_view["ply_idx"] == i:
                mid = state.mate_view["mate_idx"]
                btn_text = f"{mid + 1} / {len(mates)} mates"
            else:
                btn_text = mate_label
            line <= f"{prefix}, "
            btn = html.SPAN(btn_text, Class="mate-btn")
            btn.attrs["data-ply"] = str(i)
            btn.bind("click", on_mate_click)
            line <= btn
        else:
            line <= prefix
        if stat["truncated"]:
            line <= html.SPAN(" ⚠", Class="truncated-warn")
        bar <= line


def render():
    """Re-render the entire chess layout: panels, board, flip button, stats bar."""
    for g in document.querySelectorAll(".touch-ghost"):
        g.style.display = "none"
    layout = document["chess-layout"]
    layout.clear()
    layout <= build_panel("w")
    layout <= build_board()
    layout <= build_panel("b")
    flip_btn = document["flip-btn"]
    if state.white_persp:
        flip_btn.classList.replace("flip-black", "flip-white")
    else:
        flip_btn.classList.replace("flip-white", "flip-black")
    update_stats_bar()


# ── Button handlers ────────────────────────────────────────────────────────────
@bind(document["wtg-btn"], "click")
def on_wtg(ev):
    """Toggle the active side between White and Black, then re-render."""
    btn = ev.target
    if btn.textContent == "Go, White!":
        btn.textContent = "Go, Black!"
        btn.classList.replace("wtg-white", "wtg-black")
    else:
        btn.textContent = "Go, White!"
        btn.classList.replace("wtg-black", "wtg-white")
    drop_stats()
    render()


@bind(document["toggle-btn"], "click")
def on_toggle(ev):
    """Switch between the starting position and an empty board, then re-render."""
    # Exit mate view (board will be replaced anyway)
    state.mate_view = None
    state.board_saved = None
    state.start_active = not state.start_active
    if state.start_active:
        state.board = [r[:] for r in START]
        state.castle_w = True
        state.castle_b = True
        ev.target.textContent = "🗑"
    else:
        state.board = [[None] * 8 for _ in range(8)]
        state.castle_w = False
        state.castle_b = False
        ev.target.textContent = "↺"
    state.ep_pawn = None
    drop_stats()
    render()


@bind(document["flip-btn"], "click")
def on_flip(ev):
    """Flip the board perspective between White and Black, then re-render."""
    state.white_persp = not state.white_persp
    render()


@bind(document["depth-up"], "click")
def on_depth_up(ev):
    """Increment the depth input (max 6)."""
    el = document["depth-input"]
    try:
        val = int(el.value or "1")
    except Exception:
        val = 1
    if val < 6:
        el.value = str(val + 1)


@bind(document["depth-down"], "click")
def on_depth_down(ev):
    """Decrement the depth input (min 1)."""
    el = document["depth-input"]
    try:
        val = int(el.value or "1")
    except Exception:
        val = 1
    if val > 1:
        el.value = str(val - 1)


@bind(document["count-btn"], "click")
def on_count(ev):
    """Run the move-count tree walk for the selected depth and show results."""
    # Exit any active mate preview and restore the original board
    if state.mate_view:
        state.board = state.board_saved
        state.board_saved = None
    drop_stats()

    depth_el = document["depth-input"]
    try:
        depth = max(1, min(6, int(depth_el.value or "1")))
    except Exception:
        depth = 1

    state.computing = True
    render()

    def do_compute():
        ply_stats, targets = count_tree(
            state.board,
            current_color(),
            state.ep_pawn,
            state.castle_w,
            state.castle_b,
            depth,
        )
        state.turn_stats = ply_stats
        state.targets_combined = targets
        state.stats_shown = True
        state.computing = False
        render()

    timer.set_timeout(do_compute, 50)


render()
