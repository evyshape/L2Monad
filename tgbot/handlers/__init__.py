from .start import router as start_router
from .menu import router as menu_router
from .manage import router as manage_router
from .screenshot import router as screenshot_router
from .notifications import router as notifications_router
from .windows import router as windows_router
from .ignore import router as ignore_router
from .global_menu import router as global_menu_router
from .prank import router as prank_router

all_routers = [
    start_router,
    menu_router,
    manage_router,
    screenshot_router,
    notifications_router,
    windows_router,
    ignore_router,
    global_menu_router,
    prank_router,
]
