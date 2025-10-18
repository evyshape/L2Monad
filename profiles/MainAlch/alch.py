import random
import json
from bot.windows.runtime import RuntimeData
from profiles.base import BaseProfile
from bot.methods.other import MouseEvents, screenshot_window
from bot.alchemy.main_alch import check_slots, roll, check_bless, match_slots, pre_init
from tgbot.keyboards.screenshot import delete_screenshot_kb
from bot.clogger import log
import asyncio

class MainAlchemy(BaseProfile):
    def __init__(self, window_info, settings=None, preset=None):
        from tgbot.bot import TgBot
        super().__init__(window_info, settings=settings)
        self.mouse = MouseEvents()
        self._child_tasks = []
        self.tgbot = TgBot()
        self.runtime_data = RuntimeData(current_state="alchemy")
        self.alch_cfg = preset
        #print(preset)

    def profile_version(self):
        return "1.0.0"

    def profile_name(self):
        return "Main Alchemy"

    async def main_loop(self):
        window_id, window = next(iter(self.window_info.items()))
        kb = None
        try:
            resized = await self.smart_resize()
            if resized:
                init = await pre_init(self)

                if init is None:
                    log("Чет пошло не так, смотри в окно", window_id)
                    if hasattr(self, '_saved_pos'):
                        left, top, w, h = self._saved_pos
                        await self._resize(w, h, left, top)
                    return

                if init == "zero":
                    log("Алхимка не заряжена, верну окно назад", window_id)
                    if hasattr(self, '_saved_pos'):
                        left, top, w, h = self._saved_pos
                        await self._resize(w, h, left, top)
                    return

                if init == "first":
                    await asyncio.sleep(2)
                    bless = await check_bless(self)
                    await roll(self, step=1, kb=kb)
                    result = await check_slots(self)
                    #log(json.dumps(result, indent=4, ensure_ascii=False), window_id)
                    if match_slots(result, bless, self.alch_cfg):
                        if self.settings.TELEGRAM_NOTIFIES:
                            screenn = screenshot_window(self.window_info, tg=True)
                            self.tgbot.send_pic(
                                photo=screenn,
                                caption=f"Выкрутил алхимку успешно",
                                parse_mode="HTML",
                                nickname=window_id,
                                reply_markup=delete_screenshot_kb()
                            )

                        log("Выкрутил то что надо, проверяй окно", window_id)
                        await roll(self, step=3, kb=kb)
                        if hasattr(self, '_saved_pos'):
                            left, top, w, h = self._saved_pos
                            await self._resize(w, h, left, top)
                        return
                    else:
                        await roll(self, step=2, kb=kb)

                if init == "more":
                    #todo мб чет добаивть хз
                    pass

                await self.roll_loop(iterations=self.alch_cfg["MAX_ROLLS"], kb=kb)

            elif resized is None:
                log("Окно не нашло себе места... завершаю профиль", window_id)
                return

        except asyncio.CancelledError:
            log("Профиль остановлен вручную", window_id)
            raise

    async def on_stop(self):
        for task in self._child_tasks:
            task.cancel()
        await asyncio.gather(*self._child_tasks, return_exceptions=True)
        await super().on_stop()

    async def roll_loop(self, iterations=10, kb=None):
        window_id, window = next(iter(self.window_info.items()))
        kb = None
        try:
            await roll(self, step=1, kb=kb)
            await roll(self, step=2, kb=kb)
            for i in range(1, iterations + 1):
                try:
                    log(f"{i}/{iterations}", window_id)
                    await asyncio.sleep(random.uniform(0.25, 1.55))
                    bless = await check_bless(self)
                    await roll(self, step=1, kb=kb)
                    result = await check_slots(self)
                    #log(json.dumps(result, indent=4, ensure_ascii=False), window_id)
                    if match_slots(result, bless, self.alch_cfg):
                        if self.settings.TELEGRAM_NOTIFIES:
                            screenn = screenshot_window(self.window_info, tg=True)
                            self.tgbot.send_pic(
                                photo=screenn,
                                caption=f"Выкрутил алхимку успешно",
                                parse_mode="HTML",
                                nickname=window_id,
                                reply_markup=delete_screenshot_kb()
                            )

                        log("Выкрутил то что надо, проверяй окно", window_id)
                        await roll(self, step=3, kb=kb)
                        break
                    else:
                        await roll(self, step=2, kb=kb)

                except asyncio.CancelledError:
                    log("stoped", window_id)
                    raise
                except Exception as e:
                    log(f"Ошибка на крутке {i}: {e}", window_id)
        finally:
            if hasattr(self, '_saved_pos'):
                left, top, w, h = self._saved_pos
                await self._resize(w, h, left, top)

    def is_running(self):
        return self.running
