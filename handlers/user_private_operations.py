import asyncio
import os

from aiogram import types
from aiogram.types import FSInputFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from bot_instance import bot
from database.models import User
from kbds.inline import get_inlineMix_btns


# Управление клиентами
async def show_all_users(callback_query: types.CallbackQuery, session: AsyncSession):
    try:
        # Получение всех пользователей с продуктами
        async with session.begin():
            result = await session.execute(
                select(User).options(joinedload(User.product))
            )
            users = result.scalars().all()

        if not users:
            await callback_query.message.answer("Нет зарегистрированных пользователей.")
            return

        # Перебираем пользователей и выводим информацию о каждом
        for user in users:
            subscription_status = "Активна" if user.status else "Неактивна"
            username = user.username if user.username else "Не указано"
            product_name = user.product.name if user.product and user.product.name else "Не привязан"
            start = user.subscription_start.strftime("%d-%m-%Y") if user.subscription_start else "Не указано"
            end = user.subscription_end.strftime("%d-%m-%Y") if user.subscription_end else "Не указано"

            # Формирование информации о пользователе
            user_info = (
                f"Пользователь ID: {user.user_id}\n"
                f"Username: {username}\n"
                f"Продукт: {product_name}\n"
                f"Статус подписки: {subscription_status}\n"
                f"Подписка началась: {start}\n"
                f"Подписка заканчивается: {end}\n"
            )

            # Создание кнопок для пользователя
            buttons = get_inlineMix_btns(btns={
                "Активировать": f"activate_user_{user.user_id}",
                "Деактивировать": f"deactivate_user_{user.user_id}",
                "Удалить": f"delete_user_{user.user_id}",
                "Написать": f"write_user_{user.user_id}",
                "Просмотр Конфиг": f"view_config_{user.user_id}",
            })

            # Отправка сообщения с кнопками
            await callback_query.message.answer(user_info, reply_markup=buttons)

    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка при получении информации о пользователях. Ошибка: {e}")

# Метод для подсчета активных пользователей

# Метод для получения списка активных пользователей
async def get_active(session: AsyncSession) -> list:
    try:
        # Выполняем запрос для получения всех активных пользователей
        async with session.begin():
            result = await session.execute(
                select(User).filter(User.status == True)  # Только активные пользователи
            )
            active_users = result.scalars().all()

        # Возвращаем список активных пользователей
        return active_users

    except Exception as e:
        print(f"Ошибка при получении активных пользователей: {e}")
        return []  # Возвращаем пустой список в случае ошибки


# Отправка Конфигов в ЛК
async def send_config_and_qr_button(message: types.Message, user_id: int):
    try:
        username = f"user_{user_id}"
        config_path = f"/home/jacksmile/configs/{username}.conf"
        qr_path = f"/home/jacksmile/PycharmProjects/vpn_bot_v1.1/users_configs/qr_png/qr_{user_id}.png"

        # Проверяем, существуют ли файлы конфигурации и QR-кода
        if not os.path.exists(config_path):
            await message.answer("Конфигурационный файл не найден.")
            return

        if not os.path.exists(qr_path):
            await message.answer("QR-код не найден.")
            return

        # Отправляем конфиг-файл пользователю
        document = FSInputFile(config_path)
        await bot.send_document(chat_id=message.chat.id, document=document)

        # Отправляем сообщение с кнопкой для показа QR-кода
        await message.answer(
            f"<strong>{message.from_user.first_name}</strong>, ваш конфиг файл.",
            reply_markup=get_inlineMix_btns(btns={"Показать QR": f"qr_{user_id}"})
        )

    except Exception as e:
        await message.answer(f"Произошла ошибка при отправке конфигурации: {str(e)}")
        print(f"Ошибка при отправке конфигурации: {e}")


async def get_subscription_info(user_id: int, session: AsyncSession) -> str:
    try:
        # Запрос для получения информации о пользователе с продуктом
        async with session.begin():
            result = await session.execute(
                select(User).options(joinedload(User.product)).where(User.user_id == user_id)
            )
            user = result.scalar_one_or_none()

        if not user:
            return "Пользователь не найден."

        # Формирование информации о подписке
        subscription_status = "Активна" if user.status else "Неактивна"
        username = user.username if user.username else "Не указано"
        product_name = user.product.name if user.product and user.product.name else "Не привязан"

        start = user.subscription_start.strftime("%d-%m-%Y") if user.subscription_start else "Не указано"
        end = user.subscription_end.strftime("%d-%m-%Y") if user.subscription_end else "Не указано"

        return (
            f"👋 Добро пожаловать, <b>{username}</b>!\n\n"
            f"✅ <b>Статус подписки</b>: <b>{subscription_status}</b>\n"
            f"💼 <b>Ваш продукт</b>: <b>{product_name}</b>\n"
            f"📆 <b>Подписка началась</b>: <b>{start}</b>\n"
            f"🗓️ <b>Подписка заканчивается</b>: <b>{end}</b>\n"
        )


    except Exception as e:
        return f"Произошла ошибка при получении информации о подписке. Попробуйте позже. Ошибка: {e}"


async def delete_user_by_id_from_pivpn(user_id: int) -> bool:
    """
    Удаление пользователя из PiVPN по ID.

    :param user_id: ID пользователя для удаления.
    :return: Успешность операции (True/False).
    """
    username = f"user_{user_id}"  # Формируем имя пользователя
    try:
        process = await asyncio.create_subprocess_exec(
            "sudo", "-S", "/usr/local/bin/pivpn", "-r", "-n", username, "-y",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate(input=b'\n')

        if process.returncode == 0:
            print(f"Пользователь с ID {user_id} успешно удалён из PiVPN. Вывод: {stdout.decode()}")
            return True
        else:
            print(f"Ошибка при удалении пользователя с ID {user_id}: {stderr.decode()}")
            return False
    except asyncio.TimeoutError:
        print(f"Удаление пользователя с ID {user_id} превысило время ожидания.")
        return False
    except Exception as e:
        print(f"Ошибка при удалении пользователя с ID {user_id}: {e}")
        return False


async def deactivate_user_from_pivpn(user_id: int) -> bool:
    """
    Деактивация пользователя в PiVPN.

    :param user_id: ID пользователя для деактивации.
    :return: Успешность операции (True/False).
    """
    username = f"user_{user_id}"  # Формируем имя пользователя
    try:
        process = await asyncio.create_subprocess_exec(
            "sudo", "-S", "/usr/local/bin/pivpn", "-off", "-n", username, "-y",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate(input=b'\n')

        if process.returncode == 0:
            print(f"Пользователь с ID {user_id} деактивирован в PiVPN. Вывод: {stdout.decode()}")
            return True
        else:
            print(f"Ошибка деактивации пользователя с ID {user_id}: {stderr.decode()}")
            return False
    except asyncio.TimeoutError:
        print(f"Деактивация пользователя с ID {user_id} превысила время ожидания.")
        return False
    except Exception as e:
        print(f"Ошибка при деактивации пользователя с ID {user_id}: {e}")
        return False


async def activate_user_in_pivpn(user_id: int) -> bool:
    """
    Активация пользователя в PiVPN.

    :param user_id: ID пользователя для активации.
    :return: Успешность операции (True/False).
    """
    username = f"user_{user_id}"  # Формируем имя пользователя
    try:
        process = await asyncio.create_subprocess_exec(
            "sudo", "-S", "/usr/local/bin/pivpn", "-on", "-n", username, "-y",  # Команда для активации
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate(input=b'\n')

        if process.returncode == 0:
            print(f"Пользователь с ID {user_id} активирован в PiVPN. Вывод: {stdout.decode()}")
            return True
        else:
            print(f"Ошибка активации пользователя с ID {user_id}: {stderr.decode()}")
            return False
    except asyncio.TimeoutError:
        print(f"Активация пользователя с ID {user_id} превысила время ожидания.")
        return False
    except Exception as e:
        print(f"Ошибка при активации пользователя с ID {user_id}: {e}")
        return False


async def toggle_pivpn_user(user_id: int, action: str) -> bool:
    """
    Функция для активации или деактивации пользователя в PiVPN.
    :param user_id: ID пользователя
    :param action: Действие - 'on' для активации, 'off' для деактивации
    :return: Успешность выполнения
    """
    username = f"user_{user_id}"
    command = "-on" if action == "on" else "-off"

    try:
        # Создаем асинхронный процесс для выполнения команды в системе
        process = await asyncio.create_subprocess_exec(
            "sudo", "-S", "/usr/local/bin/pivpn", command, "-n", username, "-y",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )

        stdout, stderr = await process.communicate(input=b'\n')

        if process.returncode == 0:
            print(f"Пользователь {username} {action} в PiVPN.")
            return True
        else:
            print(f"Ошибка выполнения команды для {username}: {stderr.decode()}")
            return False
    except Exception as e:
        print(f"Ошибка при {action} пользователя {username} в PiVPN: {e}")
        return False
