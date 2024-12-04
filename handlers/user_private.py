# Внешние библиотеки
from aiogram import types, Router, F
from aiogram.exceptions import TelegramAPIError, TelegramNotFound
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandStart, Command, or_f
from aiogram.types import ReplyKeyboardRemove, FSInputFile
from aiogram.utils.formatting import as_marked_section, Bold
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
# Модели и ORM запросы
from database.models import User
from database.orm_query import orm_get_products
from database.orm_query_trial_product import get_trial_products
# Фильтры и кнопки
from filters.chat_types import ChatTypeFilter
from kbds.inline import get_inlineMix_btns
from kbds.reply import get_keyboard
# Обработчики
from handlers.payment_handlers import pay, process_pre_checkout_query, process_successful_payment
from handlers.trial_period import process_trial_subscription


load_dotenv(find_dotenv())
user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))


# Команда старт
@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message):
    print(message.from_user.id)
    await message.answer(
        f"<b>{message.from_user.first_name}</b>\nДобро пожаловать в наш VPN бот!\nВыберите действие:",
        parse_mode='HTML',
        reply_markup=get_keyboard(
            "Варианты подписки",
            "Способы оплаты",
            "О сервере",
            "Инструкции",
            "Пробный период",  # Добавляем кнопку для пробного периода
            placeholder="Что вас интересует?",
            sizes=(2, 2, 1)  # Настраиваем размеры (последняя строка будет отдельной)
        ),
    )

# Обработчик команды "Пробный период"
@user_private_router.message(F.text.casefold() == "пробный период")
async def trial_period_cmd(message: types.Message, session: AsyncSession, state: FSMContext):
    # Убираем обычную клавиатуру
    await message.answer("Открываю список пробных периодов...", reply_markup=ReplyKeyboardRemove())

    # Получаем список пробных продуктов
    trial_products = await get_trial_products(session)

    if not trial_products:
        # Если пробных продуктов нет
        await message.answer("Товара нет.",reply_markup=get_inlineMix_btns(btns={
            'Назад' : 'menu_'
        }))
        return

    # Если продукты есть, отправляем их с inline-кнопками
    for product in trial_products:
        print(product.id)
        await message.answer(
            f'<strong>{product.name}</strong>\n'
            f'Кол-во дней: {product.count_day}\n',
            reply_markup=get_inlineMix_btns(btns={
                'Подключить': f'pay_trial_{product.id}',  # Callback с ID продукта
                'Назад': 'menu_',  # Вернуться к главному меню
            }),
            parse_mode="HTML"
        )

# Обработчик для кнопки "Подключить"
@user_private_router.callback_query(F.data.startswith('pay_trial_'))
async def pay_trial_handler(callback: types.CallbackQuery, session: AsyncSession):
    await process_trial_subscription(callback, session)
    await callback.answer()

# Главное меню
@user_private_router.callback_query(F.data == 'menu_')
async def back_callback(callback_query: types.CallbackQuery, state: FSMContext):
    # Очищаем состояние FSM, если нужно
    await state.clear()
    # Отправляем сообщение с главным меню
    await callback_query.message.answer(
        '<b>Выберите действие:</b>',
        parse_mode='HTML',
        reply_markup=get_keyboard(
            "Варианты подписки",
            "Способы оплаты",
            "О сервере",
            "Инструкции",
            "Пробный период",
            placeholder="Что вас интересует?",
            sizes=(2, 2, 1)
        ),
    )

# Варианты подписки
@user_private_router.message(or_f(Command("subscription_plans"), (F.text.lower() == "варианты подписки")))
async def menu_cmd(message: types.Message, session: AsyncSession):
    # Проверяем, зарегистрирован ли пользователь
    user_id = message.from_user.id
    query = select(User).where(User.user_id == user_id)
    result = await session.execute(query)
    existing_user = result.scalar()

    for product in await orm_get_products(session):
        # Определяем текст кнопки в зависимости от наличия пользователя
        button_text = 'Продлить' if existing_user else 'Купить'

        await message.answer(
            f'<strong>{product.name}</strong>\n'
            f'Цена: {product.price} руб.\n',
            # f'Количество дней: {product.count_day}',
            reply_markup=get_inlineMix_btns(btns={
                button_text: f'pay_{product.id}',
                'Подробнее': f'change_{product.id}'
            })
        )

# О сервере
@user_private_router.message(F.text.lower() == "о сервере")
@user_private_router.message(Command("about"))
async def about_cmd(message: types.Message):
    await message.answer("<b>Сервер</b>, расположенный в Нидерландах, "
                         "предлагает высокую скорость соединения и "
                         "минимальные задержки для пользователей", parse_mode="HTML")

# Способы оплаты
@user_private_router.message(F.text.lower() == "способы оплаты")
@user_private_router.message(Command("payment"))
async def payment_cmd(message: types.Message):
    text = as_marked_section(
        Bold("Способы оплаты:"),
        "Картой в боте",
        "При получении карта/кеш",
        "В заведении",
        marker="✅ ",
    )
    await message.answer(text.as_html())

# Инструкции
@user_private_router.message(F.text.lower() == "инструкции")
@user_private_router.message(Command("inst"))
async def about_cmd(message: types.Message):
    await message.answer("<b>Здесь будет описание:</b>", parse_mode="HTML")

# Обработчик для кнопки оплаты FSM
@user_private_router.callback_query(F.data.startswith('pay_'))
async def payment_handler(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    await pay(callback, session, state)

# Обработчик для предварительной проверки платежа
@user_private_router.pre_checkout_query()
async def process_pay(pre_checkout_query: types.PreCheckoutQuery, state: FSMContext):
    await process_pre_checkout_query(pre_checkout_query, state)

# Обработчик успешной оплаты
@user_private_router.message(F.successful_payment)
async def successful_payment_handler(message: types.Message, state: FSMContext, session: AsyncSession):
    await process_successful_payment(message, state, session)

# Кнопка показать qr_code
@user_private_router.callback_query(F.data.startswith('qr_'))
async def send_qr(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    qr_path = f"/home/jacksmile/PycharmProjects/vpn_bot_v1.1/users_configs/qr_png/qr_{user_id}.png"

    try:
        # Отправка QR-кода
        photo = FSInputFile(qr_path)
        await callback.message.answer_photo(photo=photo)
    except Exception as e:
        await callback.message.answer(f"Ошибка при отправке QR-кода: {e}")


# Обработка всех файлов кроме текста
@user_private_router.message(~F.text)
async def allow_text_only(message: types.Message):
    try:
        await message.delete()  # Удаляем сообщение пользователя
        await message.answer("Можно отправлять только текстовые сообщения!")  # Отправляем уведомление
    except TelegramNotFound:
        # Если сообщение уже удалено
        pass
    except TelegramAPIError as e:
        # Обработка других ошибок Telegram API
        print(f"Ошибка при удалении сообщения: {e}")
