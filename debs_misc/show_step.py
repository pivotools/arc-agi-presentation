from pathlib import Path
import json
import numpy as np
from termcolor import colored
from copy import deepcopy
import numpy as np, random, math, itertools, collections
import sys

PALETTE_TERMINAL = {
    0: ("white", "on_grey"),  # black bg (grey in ANSI), white text
    1: ("white", "on_blue"),  # navy blue bg, white text
    2: ("white", "on_red"),  # red bg, white text
    3: ("black", "on_green"),  # green bg, black text
    4: ("black", "on_yellow"),  # yellow bg, black text
    5: ("black", "on_white"),  # gray bg (white in ANSI), black text
    6: ("white", "on_magenta"),  # pink bg (magenta), white text
    7: ("black", "on_yellow"),  # orange bg → closest is yellow, black text
    8: ("black", "on_cyan"),  # sky blue bg (cyan), black text
    9: ("white", "on_red"),  # maroon bg (closest = red), white text
}

def grid_to_colored_text(arr: np.ndarray, cell_width: int = 3, show_legend: bool = False) -> str:
    colored_text = ""
    if arr.ndim != 2:
        raise ValueError("arr must be a 2-D numpy array")

    # Validate values
    if not np.issubdtype(arr.dtype, np.integer):
        raise ValueError("arr must contain integers")
    bad = (arr < 0) | (arr > 9)
    if np.any(bad):
        bad_coords = np.argwhere(bad)
        raise ValueError(
            f"All values must be in 0..9. Bad cells at: {bad_coords.tolist()}"
        )

    for row in arr:
        line_parts = []
        for v in row:
            fg, bg = PALETTE_TERMINAL[int(v)]
            # Center the digit inside a fixed-width cell; bold for readability.
            text = f"{int(v):^{cell_width}}"
            line_parts.append(colored(text, fg, bg, attrs=["bold"]))
        colored_text += "".join(line_parts) + "\n"

    colored_text = colored_text.rstrip("\n")
    if show_legend:
        colored_text += "\n"
        for k in range(10):
            fg, bg = PALETTE_TERMINAL[k]
            swatch = colored(f" {k} ", fg, bg, attrs=["bold"])
            colored_text += swatch + " "
    return colored_text

def render_colored_grid(
    arr: np.ndarray, cell_width: int = 3, show_legend: bool = False
) -> None:
    """
    Render a 2-D numpy array (values 0..9) as a colored grid in the terminal.

    Args:
        arr: 2-D numpy array of ints in [0, 9]
        cell_width: width of each cell (use >=2; 3 works well)
        show_legend: print a color legend after the grid
    """
    print(grid_to_colored_text(arr, cell_width, show_legend))

def simulate(grid, max_steps=10000, order='bottom', dirs=('L','R'), water=1):
    H=len(grid); W=len(grid[0])
    arr=[row[:] for row in grid]
    def empty(r,c): return 0<=r<H and 0<=c<W and arr[r][c]==0
    for step in range(max_steps):

        moved=False
        coords=[(r,c) for r in range(H) for c in range(W) if arr[r][c]==water]
        if order=='bottom': coords.sort(reverse=True)
        elif order=='top': coords.sort()
        elif order=='random': random.shuffle(coords)
        for r,c in coords:
            if not (0<=r<H and 0<=c<W and arr[r][c]==water): continue
            # down
            if r+1<H and arr[r+1][c]==0:
                arr[r][c]=0; arr[r+1][c]=water; moved=True; continue
            # diagonal down if empty
            moved_this=False
            for d in dirs:
                dc=-1 if d=='L' else 1
                if r+1<H and 0<=c+dc<W and arr[r+1][c+dc]==0 and arr[r][c+dc]==0:
                    arr[r][c]=0; arr[r+1][c+dc]=water; moved=True; moved_this=True; break
            if moved_this: continue
            # horizontal to supported empty?
            for d in dirs:
                dc=-1 if d=='L' else 1
                if 0<=c+dc<W and arr[r][c+dc]==0 and (r+1==H or arr[r+1][c+dc]!=0):
                    arr[r][c]=0; arr[r][c+dc]=water; moved=True; moved_this=True; break
            if moved_this: continue
        if not moved:
            return arr, step
    return arr, max_steps


if __name__ == "__main__":
    n_step = int(sys.argv[1])
    puzzle_id = "28a6681f"
    puzzle_dir = Path(f"/data/ARC-AGI-2/data/evaluation")

    puzle_json = puzzle_dir / f"{puzzle_id}.json"

    puzzle = json.load(open(puzle_json))


    out, _ = simulate(puzzle["test"][0]["input"], dirs=('R','L'), max_steps=n_step)
    render_colored_grid(np.array(out))