from aiogram import Router, types

router = Router()

@router.callback_query(lambda c: c.data == "ignore")
async def ignore_callback(call: types.CallbackQuery):
    await call.answer()

@router.callback_query(lambda c: c.data == "todo_cb")
async def todo_callback(call: types.CallbackQuery):
    await call.answer(text="⚠️ Функция в разработке")