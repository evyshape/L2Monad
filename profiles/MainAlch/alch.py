import random
import json
from bot.windows.runtime import RuntimeData
from profiles.base import BaseProfile
from bot.misc import ALCH_DEBUG
from bot.alchemy.main_alch import check_slots, roll, check_bless, match_slots, pre_init, get_alch_var
from bot.clogger import log
import asyncio

class MainAlchemy(BaseProfile):
    def __init__(self, window_info, settings=None, preset=None):
        super().__init__(window_info, settings=settings)
        self.runtime_data = RuntimeData(current_state="alchemy")
        self.alch_cfg = preset

    def profile_version(self):
        return "1.0.0"

    def profile_name(self):
        return "Main Alchemy"

    async def main_loop(self):
        window_id, window = self.window_id, self.window_info[self.window_id]
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

                    await asyncio.sleep(1)
                    bless = await check_bless(self)
                    await roll(self, step=1, kb=kb)
                    var = await get_alch_var(self)
                    log(var, window_id)
                    result = await check_slots(self, var)
                    #log(json.dumps(result, indent=4, ensure_ascii=False), window_id)
                    if match_slots(result, bless, self.alch_cfg):
                        self.notify_screenshot("Выкрутил алхимку успешно")

                        log("Выкрутил то что надо, проверяй окно", window_id)
                        await roll(self, step=3, kb=kb)
                        if hasattr(self, '_saved_pos'):
                            left, top, w, h = self._saved_pos
                            await self._resize(w, h, left, top)
                        return
                    else:
                        await roll(self, step=2, kb=kb)

                elif init == "more":
                    await roll(self, step=2, kb=kb)

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

    async def roll_loop(self, iterations=10, kb=None, var=None):
        window_id, window = self.window_id, self.window_info[self.window_id]
        kb = None
        try:
            await roll(self, step=1, kb=kb)
            var = await get_alch_var(self)
            log(var, window_id)
            await roll(self, step=2, kb=kb)
            for i in range(1, iterations + 1):
                try:
                    log(f"{i}/{iterations}", window_id)
                    await asyncio.sleep(random.uniform(0.25, 1))
                    bless = await check_bless(self)
                    await roll(self, step=1, kb=kb)
                    await asyncio.sleep(random.uniform(0.35, 0.5))
                    result = await check_slots(self, var)

                    if ALCH_DEBUG:
                        log(json.dumps(result, indent=4, ensure_ascii=False), window_id)

                    if match_slots(result, bless, self.alch_cfg):
                        self.notify_screenshot("Выкрутил алхимку успешно")

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
