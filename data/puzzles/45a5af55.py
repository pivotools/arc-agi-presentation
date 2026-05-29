def solution(grid):
    """
    Transform the input grid into a nested square of colored frames.

    The input consists of horizontal strips where each whole row has a single color.
    For each consecutive block of rows with the same color we create a rectangular
    frame whose thickness equals the height of that block.  Starting from the
    innermost block (the last one in the input) we build the output square
    outward by surrounding the current picture with a new frame of the next
    outer colour.

    The resulting picture is always a square.  Its side length is:
        innermost_height + 2 * sum(outer_heights)

    Parameters
    ----------
    grid : list[list[int]]
        Input grid (uniform‑row strips).

    Returns
    -------
    list[list[int]]
        Output grid according to the described rule.
    """
    # ---------------------------------------------------------------
    # 1. Determine the colour blocks (colour, height) from top to bottom.
    colours = []
    heights = []
    prev = None
    cnt = 0
    for row in grid:
        # each row is assumed uniform; take its first cell as the colour
        c = row[0]
        if prev is None:
            prev = c
            cnt = 1
        elif c == prev:
            cnt += 1
        else:
            colours.append(prev)
            heights.append(cnt)
            prev = c
            cnt = 1
    # add the final block
    if prev is not None:
        colours.append(prev)
        heights.append(cnt)

    # ---------------------------------------------------------------
    # 2. Build the nested frames from the innermost block outwards.
    #    The innermost block becomes a solid square.
    cur_side = heights[-1]
    cur_grid = [[colours[-1] for _ in range(cur_side)] for __ in range(cur_side)]

    #    For every outer block we create a new square, fill it with the block's
    #    colour, and paste the previous picture into its centre.
    for colour, thickness in zip(reversed(colours[:-1]), reversed(heights[:-1])):
        new_side = cur_side + 2 * thickness
        # new square filled with the outer colour
        new_grid = [[colour for _ in range(new_side)] for __ in range(new_side)]
        # copy the current picture into the centre
        for i in range(cur_side):
            new_grid[thickness + i][thickness:thickness + cur_side] = cur_grid[i][:]
        # prepare for next iteration
        cur_grid = new_grid
        cur_side = new_side

    # ---------------------------------------------------------------
    return cur_grid
