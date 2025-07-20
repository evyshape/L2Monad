import asyncio

click_semaphore = asyncio.Semaphore(35)
swipe_semaphore = asyncio.Semaphore(1)
pixel_semaphore = asyncio.Semaphore(35)
move_semaphore = asyncio.Semaphore(35)
max_swipes = 1
