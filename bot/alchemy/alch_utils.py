import pygetwindow as gw
from screeninfo import get_monitors
from bot.alchemy.alch_cons import ALCH_REZ


def alch_rects(r1, r2):
    x1, y1, w1, h1 = r1
    x2, y2, w2, h2 = r2

    if (w2, h2) in [(400, 225), (400, 265)]:
        return False

    if w2 >= 960 and h2 >= 495:
        return not (x1 + w1 <= x2 or x2 + w2 <= x1 or
                    y1 + h1 <= y2 or y2 + h2 <= y1)

    return not (x1 + w1 <= x2 or x2 + w2 <= x1 or
                y1 + h1 <= y2 or y2 + h2 <= y1)


def get_monitorss():
    monitors = get_monitors()
    l2_w = [w for w in gw.getAllWindows() if "Lineage2M" in w.title]

    win_w, win_h = map(int, ALCH_REZ.split("x"))
    cell_w = win_w
    cell_h = win_h + 40  # залупа сверху окна

    result = {
        "count": len(monitors),
        "monitors": []
    }

    for idx, monitor in enumerate(monitors):
        cols = monitor.width // cell_w
        rows = monitor.height // cell_h
        capacity = cols * rows  # скок всего влезет сеточкой

        la2_windows = [
            {
                "title": w.title,
                "pos": (w.left, w.top),
                "size": (w.width, w.height)
            }
            for w in l2_w
            if (monitor.x <= w.left < monitor.x + monitor.width
                and monitor.y <= w.top < monitor.y + monitor.height)
        ]

        monitor_info = {
            "id": idx,
            "res": f"{monitor.width}x{monitor.height}",
            "pos": (monitor.x, monitor.y),
            "l2_count": len(la2_windows),
            "l2_windows": la2_windows,
            "grid_all": capacity,
            "grid_size": f"{cols}x{rows}"
        }
        result["monitors"].append(monitor_info)

    return result