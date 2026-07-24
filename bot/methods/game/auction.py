import asyncio

from bot.clogger import log
from bot.delays import DELAY_WAIT_AUCTION
from bot.methods.base import parseCBT
from bot.methods.game._base import GameAction


class Auction(GameAction):

    async def reregister(self) -> bool:
        if not await self.wait_and_click("main_menu_gui", timeout=7):
            log("Не удалось открыть главное меню В АУКЕ", self.window_id)
            return False

        if not await self.wait_and_click("auction_menu", timeout=4):
            log("Не удалось ткнуть по auction_menu", self.window_id)
            await self.wait_and_click("main_menu_gui", timeout=3)
            return False

        await asyncio.sleep(0.3)
        xy, rgb = parseCBT("auction_nalog", profile=self.profile)
        if not await self.profile.check_pixel(xy, rgb, timeout=DELAY_WAIT_AUCTION, thr=4):
            log("Чет пошло не так, не прогрузился аук =( Пробую выйти в меню", self.window_id)
            await self.wait_and_click("main_menu_gui", timeout=1)
            return False

        try_success = True

        if not await self.wait_and_click("auction_sell_page", timeout=10):
            log("Не удалось ткнуть по auction_sell_page", self.window_id)
            try_success = False
        else:
            await asyncio.sleep(3)

        await asyncio.sleep(DELAY_WAIT_AUCTION)
        if try_success and not await self.wait_and_click("auction_sell_select_all_active", timeout=5):
            log("Не удалось ткнуть по auction_sell_select_all_active", self.window_id)
            try_success = False

        if try_success and not await self.wait_and_click("auction_sell_reregister_active", timeout=5):
            log("Не удалось ткнуть по auction_sell_reregister_active", self.window_id)
            try_success = False

        if try_success and not await self.wait_and_click("auction_sell_reregister_confirm", timeout=5):
            log("Не удалось ткнуть по auction_sell_reregister_confirm", self.window_id)
            try_success = False

        await asyncio.sleep(0.3)

        succ = False
        if try_success:
            xy, rgb = parseCBT("auction_sell_select_all_inactive", profile=self.profile)
            succ = await self.profile.check_pixel(xy, rgb, timeout=70, thr=0)

        if succ:
            log("Успешно перевыставил аук!", self.window_id)
        else:
            log("Не удалось перевыставить аук!", self.window_id)

        await self.wait_and_click("main_menu_gui", timeout=1)

        return succ
