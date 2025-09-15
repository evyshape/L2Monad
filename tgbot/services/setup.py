from aiogram import Bot, types

SUF = " | github: L2Monad | free l2m bot"

async def setup_bot(bot: Bot):
    # нееед не удаляйте эту функу плиз
    # она полезна и делает мини пиар боту
    cur_name = await bot.get_my_name()
    curr_name = cur_name.name or "L2Monad Bot"
    ex_name = (
        curr_name + SUF if not curr_name.endswith(SUF) else curr_name
    )

    cur_desc = await bot.get_my_description()
    curr_desc = cur_desc.description or ""

    ex_desc = (
        "🚀 Бесплатный бот для Lineage 2M\n\n"
        "✅ Автоматизация фарма, сбора наград, аукциона\n"
        "🛠 Открытый исходный код (GitHub)\n"
        "🧠 Настраиваемые действия, кастомные профили\n"
        "👥 Полная чистота, никаких запросов налево\n\n"
        "🔗 https://github.com/evyshape/L2Monad"
    )

    cur_short = await bot.get_my_short_description()
    curr_short = cur_short.short_description or ""

    ex_short = "🎮 L2Monad Bot — сборщик, фармер.\n✅ Бесплатно и с исходниками.\n🔗 https://github.com/evyshape/L2Monad"

    if curr_name != ex_name:
        await bot.set_my_name(name=ex_name)

    if curr_desc != ex_desc:
        await bot.set_my_description(description=ex_desc)

    if curr_short != ex_short:
        await bot.set_my_short_description(short_description=ex_short)

    commands = [
        types.BotCommand(command="start", description="Приветственное"),
        types.BotCommand(command="menu", description="Открыть меню"),
        types.BotCommand(command="logs", description="Открыть управление логами"),
    ]
    await bot.set_my_commands(commands)