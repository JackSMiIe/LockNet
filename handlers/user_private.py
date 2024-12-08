# Внешние библиотеки
from aiogram import  Router, F
from aiogram.exceptions import TelegramNotFound, TelegramAPIError
from aiogram.filters import CommandStart, Command, or_f, StateFilter
from aiogram.types import ReplyKeyboardRemove
from aiogram.utils.formatting import as_marked_section, Bold
from dotenv import load_dotenv, find_dotenv
# Модели и ORM запросы
from database.models import User, SupportTicket
from database.orm_query import orm_get_products
from database.orm_query_blacklist import is_blacklisted
from database.orm_query_trial_product import get_trial_products
from database.orm_query_trial_users import get_trial_subscription_info
# Фильтры
from filters.chat_types import ChatTypeFilter
# Кнопки
from kbds.reply import get_keyboard
# Обработчики
from handlers.admin_operations import ADMIN_LIST
from handlers.user_private_operations import *
from handlers.payment_handlers import *
from handlers.trial_period import process_trial_subscription


# # Внешние библиотеки
# from aiogram import types, Router, F
# from aiogram.exceptions import TelegramAPIError, TelegramNotFound
# from aiogram.fsm.context import FSMContext
# from aiogram.filters import CommandStart, Command, or_f, StateFilter
# from aiogram.fsm.state import StatesGroup, State
# from aiogram.types import ReplyKeyboardRemove, FSInputFile
# from aiogram.utils.formatting import as_marked_section, Bold
# from dotenv import load_dotenv, find_dotenv
# from sqlalchemy import select
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from bot_instance import bot
# from common.bot_cmds_list import private
# # Модели и ORM запросы
# from database.models import User, SupportTicket
# from database.orm_query import orm_get_products
# from database.orm_query_trial_product import get_trial_products
# from database.orm_query_trial_users import get_trial_subscription_info
# # Фильтры и кнопки
# from filters.chat_types import ChatTypeFilter
# from handlers.admin_operations import ADMIN_LIST
# from handlers.user_private_operations import get_subscription_info, send_config_and_qr_button
# from kbds.inline import get_inlineMix_btns
# from kbds.reply import get_keyboard
# # Обработчики
# from handlers.payment_handlers import pay, process_pre_checkout_query, process_successful_payment
# from handlers.trial_period import process_trial_subscription


load_dotenv(find_dotenv())
user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))

# Команда старт
@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message, state: FSMContext, session: AsyncSession):
    # Проверяем, находится ли пользователь в черном списке
    if await is_blacklisted(session, message.from_user.id):
        await message.answer("Вы находитесь в черном списке. Доступ к боту ограничен.")
        return  # Прерываем обработку, если пользователь в черном списке

    # Если пользователь не в черном списке, продолжаем выполнение
    await state.clear()
    bot_info = await bot.get_me()
    await message.answer(
        f"Привет, <b>{message.from_user.first_name}</b>! 👋\n\n"
        f"Вы находитесь в нашем {bot_info.username}. 🌐 Мы обеспечиваем стабильное и безопасное подключение через сервер, расположенный в Нидерландах 🇳🇱.\n\n"
        f"Просто наслаждайтесь безопасным интернет-серфингом, а мы позаботимся о вашей конфиденциальности и скорости соединения. 🔐⚡\n\n"
        f"Если вам нужно больше информации или помощь — всегда рады помочь! 😊\n\n"
        f"Выберите действие 👇",
        parse_mode='HTML',
        reply_markup=get_keyboard(
            "💼 Тарифы",
            "🎁 Пробный период",
            "👤 Личный кабинет",
            "📖 Инструкции",
            "🛠 Поддержка",
            placeholder="Что вас интересует?",
            sizes=(2, 2, 1),
        ),
    )


@user_private_router.message(F.text == "👤 Личный кабинет")
async def personal_cabinet(message: types.Message, session: AsyncSession):
    user_id = message.from_user.id
    try:
        # Проверяем пробную подписку
        trial_info = await get_trial_subscription_info(user_id, session)

        if "не находитесь в пробной подписке" in trial_info:
            # Если пользователя нет в пробной подписке, проверяем основную таблицу
            dashboard = await get_subscription_info(user_id, session)
            if "Пользователь не найден" in dashboard:
                # Если пользователя нет и в основной таблице
                await message.answer("<b>Вы еще не зарегистрированы.</b>",parse_mode='HTML')
            else:
                # Проверяем, активна ли подписка
                if "Активна" in dashboard:
                    await message.answer(dashboard,parse_mode='HTML')
                    # Если подписка активна, вызываем функцию для отправки конфиг-файла и кнопки
                    await send_config_and_qr_button(message, user_id)
                else:
                    await message.answer("<b>Ваша подписка не активна.</b>",parse_mode='HTML')
        else:
            # Если пользователь найден в таблице TrialUser
            await message.answer(trial_info)
            # Вызываем функцию для отправки конфиг-файла и кнопки только в случае, если пробная подписка активна
            if "Активна" in trial_info:
                await send_config_and_qr_button(message, user_id)
            else:
                await message.answer("Ваша пробная подписка не активна. Конфиг не может быть отправлен.")

    except Exception as e:
        await message.answer(f"Произошла ошибка при получении информации о подписке. Попробуйте позже. Ошибка: {e}")



# Обработчик команды "Пробный период"
@user_private_router.message(F.text == "🎁 Пробный период")
async def trial_period_cmd(message: types.Message, session: AsyncSession):
    # Убираем обычную клавиатуру
    await message.answer("Открываю список пробных периодов ⬇️")

    # Получаем список пробных продуктов
    trial_products = await get_trial_products(session)

    if not trial_products:
        # Если пробных продуктов нет
        await message.answer("Товара нет ❌")
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
            "💼 Тарифы",  # Информация о тарифах
            "🎁 Пробный период",  # Предложение попробовать бесплатно
            "👤 Личный кабинет",  # Данные пользователя
            "📖 Инструкции",  # Как пользоваться
            "🛠 Поддержка",  # Помощь и обратная связь
            placeholder="Что вас интересует?",
            sizes=(2, 2, 1),  # Логически сгруппировано: 2 верхних, 2 нижних, 1 последняя
        ),
    )

# Варианты подписки
@user_private_router.message(F.text == "💼 Тарифы")
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
class SupportStates(StatesGroup):
    waiting_for_support_message = State()

@user_private_router.message(F.text == "🛠 Поддержка")
async def support_start(message: types.Message, state: FSMContext):
    """Запрашивает выбор действия у пользователя."""
    await message.answer(
        "Выберите действие ⬇️",
        reply_markup=get_inlineMix_btns(
            btns={
                "🛠️ Описать проблему": "describe_problem",
                "❓ Частые вопросы": "frequent_questions",
            },
            sizes=(1, 1)  # Кнопки по одной в каждом ряду
        )
    )
@user_private_router.callback_query(F.data.startswith("describe_problem"))
async def handle_describe_problem(callback: types.CallbackQuery, state: FSMContext):
    """Запрашивает описание проблемы у пользователя."""
    await callback.message.answer("Опишите вашу проблему. Мы постараемся помочь.")
    await state.set_state(SupportStates.waiting_for_support_message)


@user_private_router.message(StateFilter(SupportStates.waiting_for_support_message))
async def handle_support_message(message: types.Message, state: FSMContext):
    """Сохраняет описание проблемы и уведомляет администратора после подтверждения."""
    user_id = message.from_user.id
    username = message.from_user.username
    issue_description = message.text

    # Предлагаем пользователю подтвердить или отменить
    await message.answer(
        "Вы хотите отправить следующее описание проблемы?\n\n"
        f"<b>{issue_description}</b>\n\n"
        "Выберите действие:",
        parse_mode='HTML',
        reply_markup=get_inlineMix_btns(btns={
            "✅ Отправить": "confirm_issue",
            "❌ Отменить": "cancel_issue",
        })
    )

    # Сохраняем описание проблемы в контексте состояния
    await state.update_data(issue_description=issue_description)


@user_private_router.callback_query(F.data == "confirm_issue")
async def confirm_issue(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    """Подтверждает отправку проблемы и уведомляет администратора."""
    user_data = await state.get_data()
    issue_description = user_data.get("issue_description")
    user_id = callback.from_user.id
    username = callback.from_user.username

    try:
        # Создаем тикет
        ticket = SupportTicket(
            user_id=user_id,
            username=username,
            issue_description=issue_description
        )
        session.add(ticket)
        await session.commit()

        # Уведомляем пользователя
        await callback.message.answer(
            f"Ваш запрос принят! Номер обращения: <b>{ticket.id}</b>. Мы скоро свяжемся с вами.",
            parse_mode='HTML'
        )

        # Уведомляем администратора
        for admin_id in ADMIN_LIST:
            await bot.send_message(
                admin_id,
                f"🔔 Новое обращение #{ticket.id} от @{username} (ID: {user_id}):\n\n{issue_description}\n\n"
                f"Для обработки обращения перейдите на страницу с тикетами.",
            )

        # Очищаем состояние
        await state.clear()
    except Exception as e:
        await callback.message.answer("Произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.")
        # Логирование ошибки
        print(f"Ошибка при обработке запроса: {e}")


@user_private_router.callback_query(F.data == "cancel_issue")
async def cancel_issue(callback: types.CallbackQuery, state: FSMContext):
    """Отменяет отправку проблемы и возвращает пользователя в начальное состояние."""
    await callback.message.answer("Ваш запрос был отменен. Напишите снова, если возникнут другие вопросы.")
    await state.clear()


@user_private_router.callback_query(F.data.startswith("frequent_questions"))
async def handle_faq(callback: types.CallbackQuery):
    """Отправляет пользователю список часто задаваемых вопросов."""
    faq_text = (
        "Вот некоторые часто задаваемые вопросы:\n\n"
        "1. Как подключиться к VPN?\n"
        "   - Для подключения используйте инструкцию в разделе 'Инструкции'. Мы предоставим файл конфигурации для вашего устройства.\n\n"
        "2. Какие тарифы доступны?\n"
        "   - У нас есть тарифы на 1 месяц, 3 месяца. Выберите нужный тариф в разделе 'Тарифы'.\n\n"
        "3. Где находятся серверы?\n"
        "   - Наши серверы находятся в Нидерландах 🇳🇱, что гарантирует стабильную работу и конфиденциальность.\n\n"
        "4. Как начать пробный период?\n"
        "   - Для активации пробного периода выберите раздел 'Пробный период'.\n\n"
        "5. Как получить помощь по настройке?\n"
        "   - Обратитесь в раздел 'Поддержка', и наши специалисты помогут вам с настройкой.\n\n"
        "6. Что делать, если у меня возникла проблема с подключением?\n"
        "   - Описание проблемы можно отправить в раздел 'Описать проблему'. Мы оперативно решим вашу задачу.\n\n"
        "7. Как узнать срок действия моей подписки?\n"
        "   - Просмотрите раздел 'Личный кабинет', чтобы получить информацию о статусе вашей подписки.\n\n"
        "8. Какие способы оплаты доступны?\n"
        "   - Мы поддерживаем несколько способов оплаты, доступных в разделе 'Тарифы'."
    )

    await callback.message.answer(faq_text)

# Способы оплаты
# @user_private_router.message(F.text.lower() == "способы оплаты")
# @user_private_router.message(Command("payment"))
# async def payment_cmd(message: types.Message):
#     text = as_marked_section(
#         Bold("Способы оплаты:"),
#         "Картой в боте",
#         "При получении карта/кеш",
#         "В заведении",
#         marker="✅ ",
#     )
#     await message.answer(text.as_html())

# Инструкции
@user_private_router.message(F.text == "📖 Инструкции")
async def send_instructions(message: types.Message):
    url = 'https://jacksmiie.github.io/LockNet/'
    # Используем HTML-ссылку
    await message.answer(f'Вы можете просмотреть инструкции по <a href="{url}">ссылке</a>.', parse_mode='HTML')

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



