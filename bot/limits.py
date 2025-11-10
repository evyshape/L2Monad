import asyncio

click_semaphore = asyncio.Semaphore(75)
swipe_semaphore = asyncio.Semaphore(1)
pixel_semaphore = asyncio.Semaphore(430)
move_semaphore = asyncio.Semaphore(35)
max_swipes = 1
thread = 750

curve = True # если поставить True, то мышь не будет телепортироваться, а будет двигаться человекоподобно