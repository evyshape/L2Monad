import asyncio
import traceback
from bot.clogger import log

class BotManager:
    def __init__(self):
        self.bots = {}  # {window_nick: bot}

    def get_bot(self, window_nick):
        return self.bots.get(window_nick)

    def is_running(self, window_nick):
        bot = self.get_bot(window_nick)
        if not bot:
            return False
        return getattr(bot, "running", False)

    async def start_bot(self, bot_class, window_nick, window_info, settings, **kwargs):
        if window_nick in self.bots:
            return

        bot = bot_class({window_nick: window_info}, settings=settings, **kwargs)
        bot.window_nick = window_nick
        bot.running = True
        self.bots[window_nick] = bot
        bot._task = asyncio.create_task(self._run_bot(bot))

    async def _run_bot(self, bot):
        try:
            await bot.on_start()  # await main_loop
        except asyncio.CancelledError:
            pass
        except Exception as e:
            log(f"Бот {bot.window_nick} умер: {e}\n{traceback.format_exc()}", level="ERROR")
            try:
                await bot.on_stop()
            except Exception:
                pass
        finally:
            bot.running = False
            bot._task = None
            self.bots.pop(bot.window_nick, None)

    async def stop_bot(self, window_nick):
        bot = self.get_bot(window_nick)
        if not bot:
            return
        if bot._task:
            bot._task.cancel()
        await bot.on_stop()
        bot.running = False
        bot._task = None
        self.bots.pop(window_nick, None)
