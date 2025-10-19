import asyncio

click_semaphore = asyncio.Semaphore(55)
swipe_semaphore = asyncio.Semaphore(1)
pixel_semaphore = asyncio.Semaphore(230)
move_semaphore = asyncio.Semaphore(35)
max_swipes = 1
thread = 450

curve = True # если поставить True, то мышь не будет телепортироваться, а будет двигаться человекоподобно