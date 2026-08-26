import asyncio

click_semaphore = asyncio.Semaphore(75)
swipe_semaphore = asyncio.Semaphore(30)
pixel_semaphore = asyncio.Semaphore(500)
move_semaphore = asyncio.Semaphore(35)
max_swipes = 1
thread = 850

curve = True # если поставить True, то мышь не будет телепортироваться, а будет двигаться человекоподобно