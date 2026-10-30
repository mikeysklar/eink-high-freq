# pr_isolate: which step of switching() leaves stale bytes in the 0x26 RAM (needs pr_raw, pr_fast)
ROWS = list(range(0, 40, 13)) + list(range(125, 176))


def iso(reentry=True, stock=False, steps=20, steps2=20):
    clear_panel()
    d, rect = make_display(True)
    timed_refresh(d)
    ms, dx = move(d, rect, steps)
    if reentry:
        d.update_refresh_mode(FAST_START, 0, refresh_sequence=FAST_REFRESH)
        ms, dx = move(d, rect, steps2, dx)
    if stock:
        d.update_refresh_mode(STOCK_START, 0, refresh_sequence=STOCK_REFRESH)
        ms, dx = move(d, rect, 2, dx)
        d.update_refresh_mode(FAST_START, 0, refresh_sequence=FAST_REFRESH)
        ms, dx = move(d, rect, steps2, dx)
    print("reentry=%s stock=%s steps=%d steps2=%d" % (reentry, stock, steps, steps2))
    try:
        check_ram(rect.x, ROWS)
    finally:
        finish_panel()


def iso_stock(steps=41, n=2, back=0):
    # fast, then n stock full refreshes, then `back` fast refreshes, then read RAM
    clear_panel()
    d, rect = make_display(True)
    timed_refresh(d)
    ms, dx = move(d, rect, steps)
    d.update_refresh_mode(STOCK_START, 0, refresh_sequence=STOCK_REFRESH)
    ms, dx = move(d, rect, n, dx)
    if back:
        d.update_refresh_mode(FAST_START, 0, refresh_sequence=FAST_REFRESH)
        ms, dx = move(d, rect, back, dx)
    print("iso_stock steps=%d n=%d back=%d" % (steps, n, back))
    try:
        check_ram(rect.x, ROWS)
    finally:
        finish_panel()


def one_move(reset_before, start=FAST_START, refresh_sequence=FAST_REFRESH, x0=200, x1=192):
    # one refresh after an optional update_refresh_mode (RST + start_sequence), then read RAM
    clear_panel()
    d, rect = make_display(True)
    timed_refresh(d)
    rect.x = x0
    timed_refresh(d)
    if reset_before:
        d.update_refresh_mode(start, 0, refresh_sequence=refresh_sequence)
    rect.x = x1
    print("one_move reset_before=%s x %d -> %d: %.1f ms" % (reset_before, x0, x1, timed_refresh(d)))
    try:
        check_ram(rect.x, ROWS)
    finally:
        finish_panel()
