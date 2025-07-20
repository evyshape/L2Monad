import asyncio
from clogger import log
from constans import SUPPORTED_REZ
from profiles.BuyerProfile.buyer import Buyer
from profiles.RewardsProfile.rewards import Rewards
from profiles.TestProfile.test import Test
from profiles.PvpProfile.pvp import PvPDodge
from bot.utils import findAllWindows
from bot.windows.base import BaseSettings, default_values
from bot.windows.settings_loader import load_settings, save_settings

async def main():
    tname = "-Zapuskator-"
    windows = findAllWindows()
    bots = []
    tasks = []

    for window_nick, window_info in windows.items():
        size = window_info["Size"]
        if size not in SUPPORTED_REZ:
            log(f"[{window_nick}] Почини разрешение...", tname, "ERROR")
            log(f"Поддерживаемые: {SUPPORTED_REZ} | Твое: {size}", tname, "ERROR")
            #todo меседж бокс сюда
            continue

        settings = load_settings(window_nick)
        if not settings:
            log(f"[{window_nick}] Нет настроек, создаём из базы...", tname)
            settings = BaseSettings(**default_values)
            save_settings(window_nick, settings)

        bot = PvPDodge({window_nick: window_info}, settings=settings)
        #bot = Rewards({window_nick: window_info}, settings=settings)
        #bot = Buyer({window_nick: window_info}, settings=settings)
        #bot = Test({window_nick: window_info}, settings=settings)
        bots.append(bot)
        task = await bot.on_start()
        tasks.append(task)

    await asyncio.gather(*tasks)
    log("Все таски завершены", tname)
    await asyncio.gather(*(bot.on_stop() for bot in bots))

asyncio.run(main())
