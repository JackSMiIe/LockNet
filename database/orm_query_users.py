import os

from aiogram.types import FSInputFile
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload
from aiogram import types

from bot_instance import bot
from database.models import User
from kbds.inline import get_inlineMix_btns


# Настройка логирования


# Получить все записи БД
async def orm_get_users(session: AsyncSession):
    try:
        query = select(User)
        result = await session.execute(query)
        users = result.scalars().all()
        return users
    except Exception as e:
        print(f"Ошибка при получении пользователей: {e}")
        return []

# Запрос на удаление по ID
async def orm_delete_user(session: AsyncSession, user_id: int):
    try:
        # Составляем запрос на удаление
        query = delete(User).where(User.user_id == user_id)
        # Выполняем запрос
        await session.execute(query)
        await session.commit()
        print(f"Пользователь с ID {user_id} удален.")
    except Exception as e:
        print(f"Ошибка при удалении пользователя с ID {user_id}: {e}")
        await session.rollback()

# Обновление клиента
async def orm_update_user_status(session: AsyncSession, user_id: int, new_status: bool):
    try:
        # Составляем запрос на обновление
        query = update(User).where(User.user_id == user_id).values(status=new_status)
        # Выполняем запрос
        await session.execute(query)
        await session.commit()
        print(f"Статус пользователя с ID {user_id} обновлен на {new_status}")
    except Exception as e:
        print(f"Ошибка при обновлении статуса пользователя с ID {user_id}: {e}")
        await session.rollback()

# Подсчет пользователей со статусом True
async def orm_count_users_with_true_status(session: AsyncSession):
    try:
        query = select(User).filter(User.status == True)  # Выбираем пользователей со статусом True
        result = await session.execute(query)
        users = result.scalars().all()  # Получаем все результаты
        count = len(users)  # Подсчитываем количество пользователей
        return count
    except Exception as e:
        print(f"Ошибка при подсчете пользователей со статусом True: {e}")
        return None


async def count_active_users(session: AsyncSession) -> int:
    """
    Подсчитывает количество активных пользователей (статус True).
    """
    query = select(func.count()).select_from(User).where(User.status.is_(True))
    result = await session.execute(query)
    return result.scalar()


async def count_inactive_users(session: AsyncSession) -> int:
    """
    Подсчитывает количество неактивных пользователей (статус False).
    """
    query = select(func.count()).select_from(User).where(User.status.is_(False))
    result = await session.execute(query)
    return result.scalar()


async def count_total_users(session: AsyncSession) -> int:
    """
    Подсчитывает общее количество пользователей.
    """
    query = select(func.count()).select_from(User)
    result = await session.execute(query)
    return result.scalar()


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

        return  (
            f"Добро пожаловать, {username}!\n\n"
            f"Ваш статус подписки: {subscription_status}\n"
            f"Ваш продукт: {product_name}\n"
            f"Подписка началась: {start}\n"
            f"Подписка заканчивается: {end}\n"
        )


    except Exception as e:
        return f"Произошла ошибка при получении информации о подписке. Попробуйте позже. Ошибка: {e}"
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
