import os
from config import PREVIEW_COLORS, PREVIEW_INDICATOR_SHAPE, PREVIEW_INDICATOR_SIZE
from utils.icons import create_colored_icon

ICON_NAMES = ["valid", "unchanged", "invalid", "duplicate"]

ICON_PATHS = {}

def prepare_status_icons(base_dir: str = "resources/icons") -> dict[str, str]:
    os.makedirs(base_dir, exist_ok=True)

    for name in ICON_NAMES:
        path = os.path.join(base_dir, f"{name}.png")
        ICON_PATHS[name] = path

        if not os.path.exists(path):
            pixmap = create_colored_icon(
                fill_color=PREVIEW_COLORS[name],
                shape=PREVIEW_INDICATOR_SHAPE,
                size_x=PREVIEW_INDICATOR_SIZE[0],
                size_y=PREVIEW_INDICATOR_SIZE[1],
                border_color="#222222",
                border_thickness=1
            )
            pixmap.save(path)

    return ICON_PATHS
