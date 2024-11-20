import logging,asyncio
import os

from aiogram.exceptions import TelegramAPIError, TelegramNotFound
from datetime import datetime,timedelta
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile
from sqlalchemy.exc import SQLAlchemyError
from bot_instance import bot
from aiogram import F, types, Router
from aiogram.filters import CommandStart, Command, or_f, StateFilter
from aiogram.utils.formatting import (
    as_list,
    as_marked_section,
    Bold,
)
from dotenv import load_dotenv, find_dotenv
from sqlalchemy import select
from database.models import User
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Product
from database.orm_query import orm_add_product, orm_get_products
from filters.chat_types import ChatTypeFilter
from handlers.payment_handlers import pay, process_pre_checkout_query
from kbds.inline import get_inlineMix_btns
from kbds.reply import get_keyboard
from handlers.payment_states import PaymentStates

load_dotenv(find_dotenv())
user_private_router = Router()
user_private_router.message.filter(ChatTypeFilter(["private"]))




@user_private_router.message(CommandStart())
async def start_cmd(message: types.Message):
    print(message.from_user.id)
    await message.answer(
        f"<b>{message.from_user.first_name}</b>\nДобро пожаловать в наш VPN бот!\nВыберите действие:",parse_mode='HTML',
        reply_markup=get_keyboard(
            "Варианты подписки",
            "Способы оплаты",
            "О сервере",
            "Инструкции",
            placeholder="Что вас интересует?",
            sizes=(2, 2)
        ),
    )

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


@user_private_router.message(F.text.lower() == "о сервере")
@user_private_router.message(Command("about"))
async def about_cmd(message: types.Message):
    await message.answer("<b>Сервер</b>, расположенный в Нидерландах, "
                         "предлагает высокую скорость соединения и "
                         "минимальные задержки для пользователей", parse_mode="HTML")

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
async def process_pay(message: types.Message, state: FSMContext, session: AsyncSession):
    current_state = await state.get_state()
    if current_state == PaymentStates.waiting_for_payment_2 and message.successful_payment:
        if message.successful_payment.invoice_payload.startswith('wtf'):
            # Получаем product_id из полезной нагрузки
            product_id = int(message.successful_payment.invoice_payload.split('_')[1])

            # Получаем продукт из базы данных по его ID
            query = select(Product).where(Product.id == product_id)
            result = await session.execute(query)
            product = result.scalar()

            # Проверяем, существует ли продукт
            if not product:
                await message.answer("Произошла ошибка: продукт не найден.")
                return

            # Выводим сообщение после успешной оплаты
            await bot.send_message(message.from_user.id, 'Оплата прошла успешно! Спасибо.')

            # Создаем нового пользователя с учетом продукта
            user_id = message.from_user.id
            username = message.from_user.username

            # Проверка, существует ли пользователь в базе данных
            query = select(User).where(User.user_id == user_id)
            result = await session.execute(query)
            existing_user = result.scalar()

            if existing_user:
                # Пользователь уже существует — проверяем и продлеваем подписку
                current_date = datetime.utcnow()
                if existing_user.subscription_end and existing_user.subscription_end > current_date:
                    # Подписка активна — продлеваем от текущей даты окончания
                    existing_user.subscription_end += timedelta(days=product.count_day)
                else:
                    # Подписка истекла или не установлена — начинаем с сегодняшнего дня
                    existing_user.subscription_start = current_date
                    existing_user.subscription_end = current_date + timedelta(days=product.count_day)
                    if not existing_user.status:  # Если пользователь не активен
                        print(f"До изменения: {existing_user.status}")
                        existing_user.status = True  # Активируем пользователя
                        print(f"После изменения: {existing_user.status}")
                        username = f"user_{existing_user.user_id}"

                        try:
                            process = await asyncio.create_subprocess_exec(
                                "sudo", "-S", "/usr/local/bin/pivpn", "-on","-n", username, "-y", # -n можно убрать или оставить(смотреть логи)
                                stdin=asyncio.subprocess.PIPE,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )

                            stdout, stderr = await process.communicate(input=b'\n')

                            if process.returncode == 0:
                                print(f"Пользователь {existing_user.username} c ID {existing_user.user_id} активирован.\n"
                                      f"Вывод: {stdout.decode()}")
                            else:
                                print(f"Ошибка выполнения команды для {username}: {stderr.decode()}")

                        except asyncio.TimeoutError:
                            print(f"Команда для пользователя {username} превысила время ожидания.")
                        except Exception as e:
                            print(f"Ошибка при выполнении команды для {username}: {e}")
                await session.commit()
                formatted_date = existing_user.subscription_end.strftime("%d.%m.%Y")
                await message.answer(f"Подписка успешно продлена до {formatted_date}")
            else:
                # Создаем нового пользователя, если он не существует
                new_user = User(
                    user_id=user_id,
                    username=username,
                    status=True,
                    product=product  # передаем продукт для инициализации даты окончания подписки
                )

                # После создания new_user можно задать subscription_start и subscription_end
                new_user.subscription_start = datetime.utcnow()
                new_user.subscription_end = datetime.utcnow() + timedelta(days=product.count_day)

                session.add(new_user)
                await session.commit()
                await message.answer("Вы успешно зарегистрированы.")

            # Устанавливаем состояние как успешная оплата
            await state.set_state(PaymentStates.payment_successful)
            await generate_and_send_qr(message, state, session)
# Генерация QR-code
async def generate_and_send_qr(message: types.Message, state: FSMContext, session: AsyncSession):
    current_state = await state.get_state()
    if current_state == PaymentStates.payment_successful:
        user_id = message.from_user.id
        username = f"user_{user_id}"
        qr_path = f"/home/jacksmile/PycharmProjects/vpn_bot_v1.1/users_configs/qr_png/qr_{user_id}.png"
        config_path = f"/home/jacksmile/configs/{username}.conf"

        try:
            # Проверка, существует ли пользователь в базе данных
            query = select(User).where(User.user_id == user_id)
            result = await session.execute(query)
            existing_user = result.scalar()

            if existing_user:
                # Пользователь уже зарегистрирован — обновляем только подписку
                await message.answer("Подписка успешно продлена.")
                await state.clear()
            else:
                # Добавляем нового пользователя в базу данных, если он еще не зарегистрирован
                new_user = User(user_id=user_id, username=message.from_user.username, status=True)
                session.add(new_user)
                await session.commit()
                await message.answer("Вы успешно зарегистрированы.")

            # Асинхронное добавление нового пользователя с помощью команды pivpn
            process = await asyncio.create_subprocess_exec(
                "sudo", "-S", "/usr/local/bin/pivpn", "-a", "-n", username,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=b'\n')
            if process.returncode != 0:
                try:
                    document = FSInputFile(config_path)
                    # Отправка конфигурационного файла пользователю
                    await bot.send_document(chat_id=message.chat.id, document=document)
                    # Сообщение об успешной генерации конфигурации
                    await message.answer(
                        f"<strong>{message.from_user.first_name}</strong>, ваш конфиг файл успешно сгенерирован.",
                        reply_markup=get_inlineMix_btns(btns={"Показать QR": f"qr_{user_id}"})
                    )
                    return  # Завершаем выполнение после успешной отправки документа
                except Exception as e:
                    # Если документ не найден или произошла ошибка при отправке
                    await message.answer("Ваши файлы не найдены. Обратитесь в техподдержку!")
                    return

            # Асинхронное создание QR-кода из конфигурационного файла
            process = await asyncio.create_subprocess_exec(
                "sudo", "-S", "qrencode", "-o", qr_path, "-r", config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                await message.answer(f"Ошибка при создании QR-кода: {stderr.decode()}")
                return

            # Отправка конфиг-файла пользователю
            document = FSInputFile(config_path)
            await bot.send_document(chat_id=message.chat.id, document=document)
            await message.answer(
                f"<strong>{message.from_user.first_name}</strong>, ваш конфиг файл успешно сгенерирован.",
                reply_markup=get_inlineMix_btns(btns={"Показать QR": f"qr_{user_id}"})
            )
            await state.clear()

        except Exception as e:
            await message.answer(f"Произошла неизвестная ошибка: {e}")
            await session.rollback()  # Откат транзакции в случае ошибки
            await state.clear()
        else:
            await session.commit()

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
