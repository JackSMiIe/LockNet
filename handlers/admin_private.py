from aiogram import Router, types, F
from aiogram.filters import Command, or_f, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.util import await_only

from database.orm_query import orm_add_product, orm_get_products, orm_delete_product
from database.orm_query_blacklist import get_all_blacklisted_users, add_to_blacklist
from database.orm_query_users import orm_count_users_with_true_status
from filters.chat_types import ChatTypeFilter, IsAdmin
from kbds.inline import get_inlineMix_btns, get_callback_btns
from kbds.reply import get_keyboard
from handlers.payment_states import PaymentStates

ADMIN_KB = get_keyboard(
    "Товары",            # Кнопка для управления товарами
    "ЧС",                # Кнопка для управления черным списком
    "Пользователи",      # Кнопка для управления пользователями
    "Статистика",        # Кнопка для просмотра статистики
    "Администраторы",      # Кнопка для управления ролями
    placeholder="Выберите действие",
    sizes=(3, 2),         # Размеры для упорядочивания кнопок
)

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

# Главное меню администратора
@admin_router.message(Command("admin"))
async def admin_features(message: types.Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)
#-----------------
"""ЧС"""

# Получить черный список
# Класс для ввода текста(состояние)
class TextInputStates(StatesGroup):
    waiting_for_text = State()

@admin_router.message(F.text.lower() == 'черный список')
async def show_blacklist(message: types.Message, session: AsyncSession):
    # Получаем всех пользователей в черном списке
    users = await get_all_blacklisted_users(session)

    # Формируем сообщение с данными пользователей
    if users:
        blacklist_info = "\n".join(
            [f"ID: {user.user_id}, Username: {user.username}, Причина: {user.reason}" for user in users]
        )
        await message.answer(f"Список пользователей в черном списке:\n{blacklist_info}")
    else:
        await message.answer("Черный список пуст.")

# Внести в ЧС
@admin_router.message(F.text.lower() == "внести в чс")
async def start_blacklist_process(message: types.Message, state: FSMContext):
    # Отправляем сообщение с инструкцией и клавиатурой
    await message.answer(
        "Введите <b>ID</b> и <b>причину</b> через запятую. <b>Пример</b>: 424629424, Плохое поведение в чате",
        parse_mode='HTML',
        reply_markup=get_inlineMix_btns(btns={
            'Добавить в ЧС': 'add_to_blacklist_',
            'Отмена': 'cancel_handler_',
        })
    )

@admin_router.callback_query(F.data.startswith('add_to_blacklist_'))
async def process_blacklist_input(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    # Отправляем сообщение с инструкцией и запрашиваем ввод
    await callback_query.message.answer(
        "Введите <b>ID</b> и <b>причину</b> через запятую. <b>Пример</b>: 424629424, Плохое поведение в чате",
        parse_mode='HTML'
    )
    await state.set_state(TextInputStates.waiting_for_text)  # Устанавливаем состояние для ввода текста

@admin_router.message(TextInputStates.waiting_for_text)
async def handle_blacklist_input(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        # Проверяем наличие запятой в тексте
        if ',' not in message.text:
            await message.answer("Неверный формат. Введите ID и причину через запятую. Пример: 424629424, Плохое поведение в чате")
            return

        # Разделяем строку на ID и причину
        user_id_str, reason = map(str.strip, message.text.split(',', maxsplit=1))

        # Проверяем, что ID — это число
        if not user_id_str.isdigit():
            await message.answer("ID должен быть числом. Попробуйте снова.")
            return

        # Преобразуем ID в целое число
        user_id = int(user_id_str)

        # Добавляем пользователя в черный список
        await add_to_blacklist(session, user_id, reason)

        # Подтверждаем успешное добавление
        await message.answer(f"Пользователь с ID {user_id} добавлен в черный список.",reply_markup=ADMIN_KB)
        await state.clear()  # Завершаем FSM
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")
        await state.clear()


@admin_router.callback_query(StateFilter("*"),F.data == "cancel_handler_")
async def cancel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    # Проверяем, есть ли активное состояние
    if await state.get_state():
        await state.clear()  # Сбрасываем состояние
        await callback_query.message.answer("Действия отменены", reply_markup=ADMIN_KB)
    else:
        await callback_query.message.answer("Нет активных действий для отмены.")
#--------------


# Показ ассортимента товаров
@admin_router.message(F.text.lower() == 'товары')
async def menu_cmd(message: types.Message, session: AsyncSession):
    await message.answer('<b>Выберите действие:</b>', reply_markup=get_inlineMix_btns(btns={
        'Добавить товар': 'добавить товар_',
        'Добавить акцию': 'добавить акцию_',
        'Ассортимент': 'ассортимент_',
        'Главное меню': 'назад_'
    }),parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('ассортимент_'))
async def menu_cmd(callback_query: types.CallbackQuery, session: AsyncSession):
    # Получаем все товары
    products = await orm_get_products(session)

    if not products:
        await callback_query.message.answer('В ассортименте нет товаров.')
        return

    # Разделяем товары на две категории: "Акция" и остальные
    action_products = [product for product in products if 'Акция' in product.name]
    other_products = [product for product in products if 'Акция' not in product.name]
    other_products = sorted(other_products, key=lambda p: p.name.lower())

    # Формируем сообщение с товарами с "Акция"
    if action_products:
        for product in action_products:
            response_message = (f"<strong>{product.name}</strong>\n"
                                 f"Цена: {product.price} руб.\n"
                                 f"Кол-во дней: {product.count_day}\n\n")
            # Отправляем товары с "Акция" и кнопки для управления
            await callback_query.message.answer(
                response_message,
                reply_markup=get_inlineMix_btns(btns={
                    'Удалить': f'delete_{product.id}',
                    'Назад': 'назад_'
                })
            )

    # Формируем сообщение с остальными товарами
    if other_products:
        for product in other_products:
            response_message = (f"<strong>{product.name}</strong>\n"
                                 f"Цена: {product.price} руб.\n"
                                 f"Кол-во дней: {product.count_day}\n\n")
            # Отправляем остальные товары и кнопки для управления
            await callback_query.message.answer(
                response_message,
                reply_markup=get_inlineMix_btns(btns={
                    'Удалить': f'delete_{product.id}',
                    'Назад': 'назад_'
                })
            )

    await callback_query.message.answer('Ок, актуальный прайс ⬆️')


# Обработка удаления товара
@admin_router.callback_query(F.data.startswith('delete_'))
async def delete_product(callback: types.CallbackQuery, session: AsyncSession):
    # Извлекаем ID продукта из данных callback
    product_id = int(callback.data.split('_')[-1])

    # Удаляем продукт из базы данных
    await orm_delete_product(session, product_id)

    # Ответ на callback-запрос
    await callback.answer('Товар удален', reply_markup=get_inlineMix_btns(btns={
        'Назад': 'назад_',
        'Ассортимент': 'ассортимент_',
    }))

    # Отправка сообщения с подтверждением удаления
    await callback.message.answer('Товар удален', reply_markup=get_inlineMix_btns(btns={
        'Назад': 'назад_',
        'Ассортимент': 'ассортимент_',

    }))

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
@admin_router.callback_query(F.data.startswith('добавить товар_'))
async def admin_add(callback: types.CallbackQuery, state: FSMContext):
    print("Кнопка 'Добавить товар' нажата")  # Логирование
    await callback.message.answer("Введите название товара:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddProduct.name)

@admin_router.callback_query(F.data.startswith('добавить акцию_'))
async def admin_add(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    # Получаем список продуктов
    promotion = await orm_get_products(session)

    # Проверяем, есть ли продукт с именем "Акция"
    existing_promotion = next((product for product in promotion if product.name.lower() == "акция"), None)

    if existing_promotion:
        # Если акция уже существует, сообщаем об этом
        await callback.message.answer(
            'Акция уже существует. Для добавления новой акции сначала удалите старую.')
        await state.clear()  # Очистим состояние, если это необходимо
    else:
        # Если акции нет, создаем новую
        await state.update_data(name="Акция")
        await callback.message.answer("Введите количество дней акции:", reply_markup=get_inlineMix_btns(btns={
            'Отмена' : 'назад_'
        }))
        await state.set_state(AddProduct.count_day)  # Переводим в следующее состояние для ввода цены

# Команда отмены
# Команда отмены
@admin_router.message(StateFilter("*"), or_f(Command("отмена"), F.text.casefold() == "отмена"))
async def cancel_handler(message: types.Message, state: FSMContext):
    if await state.get_state():
        await state.clear()  # Очистка состояния
        await message.answer("Действия отменены", reply_markup=ADMIN_KB)
    else:
        await message.answer("Нет активных действий для отмены.", reply_markup=ADMIN_KB)


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
        price = float(message.text)
        if price < 80:
            await message.answer("Цена должна быть больше 80!")
            return
    except ValueError:
        await message.answer("Введите корректное число для стоимости!")
        return

    await state.update_data(price=price)
    data = await state.get_data()

    try:
        await orm_add_product(session, data)
        await message.answer("Товар успешно добавлен!",reply_markup=get_inlineMix_btns(btns={
            'Ассортимент': 'ассортимент_',
            'Назад': 'назад_'
        }))

    except Exception as e:
        await message.answer(f"Ошибка при добавлении товара: {e}")
    finally:
        await state.clear()

# Обработка нажатия на кнопку "Назад" для возвращения в главное меню
@admin_router.callback_query(F.data == 'назад_')
async def back_to_menu(callback_query: types.CallbackQuery, state: FSMContext):
    # Очистить текущее состояние
    await state.clear()
    # Ответ на нажатие кнопки "Назад"
    await callback_query.message.answer("Вы вернулись в меню.", reply_markup=ADMIN_KB)

# @admin_router.callback_query(F.data == 'назад')
# async def back_to_menu(callback_query: types.CallbackQuery):
#     await callback_query.message.answer("Вы вернулись в меню.", reply_markup=ADMIN_KB)

# Команды для выхода и отмены в любое время
@admin_router.message(or_f(F.text.lower() == 'выход', F.text.lower() == 'отмена'))
async def admin_exit(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выход выполнен.", reply_markup=ADMIN_KB)


@admin_router.message(F.text.lower() == 'количество активных пользователей')
async def count_active_users(message: types.Message, session: AsyncSession):
    count = await orm_count_users_with_true_status(session)
    await message.answer(f"Количество активных пользователей (со статусом True): {count}", reply_markup=ADMIN_KB)