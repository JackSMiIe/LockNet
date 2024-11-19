from aiogram import Router, types, F
from aiogram.filters import Command, or_f, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from database.orm_query import orm_add_product, orm_get_products, orm_delete_product
from database.orm_query_users import orm_count_users_with_true_status
from filters.chat_types import ChatTypeFilter, IsAdmin
from kbds.inline import get_inlineMix_btns
from kbds.reply import get_keyboard

ADMIN_KB = get_keyboard(
    "Добавить товар",
    "Ассортимент",
    placeholder="Выберите действие",
    sizes=(2,),
)

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

# Главное меню администратора
@admin_router.message(Command("admin"))
async def admin_features(message: types.Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)

# Показ ассортимента товаров
@admin_router.message(F.text.lower() == 'ассортимент')
async def menu_cmd(message: types.Message, session: AsyncSession):
    for product in await orm_get_products(session):
        await message.answer(
            f'<strong>{product.name}</strong>\nЦена: {product.price} руб.\nКол-во дней: {product.count_day}',
            reply_markup=get_inlineMix_btns(btns={
                'Удалить': f'delete_{product.id}',
                'Изменить': f'change_{product.id}'
            })
        )
    await message.answer('Ок, актуальный прайс ⬆️')

# Обработка удаления товара
@admin_router.callback_query(F.data.startswith('delete_'))
async def delete_product(callback: types.CallbackQuery, session: AsyncSession):
    product_id = int(callback.data.split('_')[-1])
    await orm_delete_product(session, product_id)
    await callback.answer('Товар удален')
    await callback.message.answer('Товар удален')

# Изменение товара
@admin_router.message(or_f(Command("change"), F.text.lower() == 'изменить товар'))
async def change_price(message: types.Message):
    await message.answer('Что будем менять?')

# Состояния для добавления товара
class AddProduct(StatesGroup):
    name = State()
    count_day = State()
    price = State()

# Начало добавления товара
@admin_router.message(StateFilter(None), F.text.lower() == 'добавить товар')
async def admin_add(message: types.Message, state: FSMContext):
    await message.answer("Введите название:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddProduct.name)

# Команда отмены
@admin_router.message(StateFilter("*"), or_f(Command("отмена"), F.text.casefold() == "отмена"))
async def cancel_handler(message: types.Message, state: FSMContext):
    if await state.get_state():
        await state.clear()
        await message.answer("Действия отменены", reply_markup=ADMIN_KB)

# Команда "назад" для возврата на предыдущий шаг
@admin_router.message(StateFilter("*"), or_f(Command("назад"), F.text.casefold() == "назад"))
async def back_step_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == AddProduct.count_day.state:
        await state.set_state(AddProduct.name)
        await message.answer("Введите название товара заново:")
    elif current_state == AddProduct.price.state:
        await state.set_state(AddProduct.count_day)
        await message.answer("Введите количество дней подписки заново:")
    else:
        await message.answer("Вы на первом шаге или неверная команда.")

# Обработка ввода названия товара
@admin_router.message(AddProduct.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите количество дней подписки:")
    await state.set_state(AddProduct.count_day)

# Обработка ввода количества дней подписки
@admin_router.message(AddProduct.count_day, F.text)
async def add_count_day(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите корректное число для количества дней!")
        return
    await state.update_data(count_day=int(message.text))
    await message.answer("Введите стоимость товара:")
    await state.set_state(AddProduct.price)

# Обработка ввода цены товара
@admin_router.message(AddProduct.price, F.text)
async def add_price(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        price = float(message.text) # ост тут
        if price < 80:
            await message.answer("Цена должна быть больше 80!")
            return
        # print(price)
        # price = float(message.text) Было так
    except ValueError:
        await message.answer("Введите корректное число для стоимости!")
        return

    await state.update_data(price=price)
    data = await state.get_data()
    try:
        await orm_add_product(session, data)
        await message.answer("Товар успешно добавлен!", reply_markup=ADMIN_KB)
    except Exception as e:
        await message.answer(f"Ошибка при добавлении товара: {e}")
    finally:
        await state.clear()

# Команды для выхода и отмены в любое время
@admin_router.message(or_f(F.text.lower() == 'выход', F.text.lower() == 'отмена'))
async def admin_exit(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выход выполнен.", reply_markup=ADMIN_KB)


@admin_router.message(F.text.lower() == 'количество активных пользователей')
async def count_active_users(message: types.Message, session: AsyncSession):
    count = await orm_count_users_with_true_status(session)
    await message.answer(f"Количество активных пользователей (со статусом True): {count}", reply_markup=ADMIN_KB)