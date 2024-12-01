from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import BlacklistUser
from aiogram import types


async def add_to_blacklist(message: types.Message, session: AsyncSession, user_id: int, username: str = None, reason: str = None):
    try:
        # Проверяем, является ли session экземпляром AsyncSession
        if not isinstance(session, AsyncSession):
            raise ValueError(f"Ожидался объект AsyncSession, но получен {type(session)}")

        # Проверяем, есть ли уже пользователь в черном списке
        result = await session.execute(select(BlacklistUser).filter_by(user_id=user_id))
        existing_user = result.scalar()

        if existing_user:
            # Если пользователь уже есть в черном списке
            await message.answer(f"Пользователь с ID {user_id} уже в черном списке.")
            return

        # Если пользователя нет, добавляем его в черный список
        user = BlacklistUser(user_id=user_id, username=username or 'Не указано', reason=reason or 'Не указано')
        session.add(user)
        await session.commit()
        print(f"Пользователь с ID {user_id} добавлен в черный список.")
    except Exception as e:
        print(f"Ошибка при добавлении пользователя с ID {user_id}: {e}")
        await session.rollback()  # Откат в случае ошибки
        await message.answer("Произошла ошибка при добавлении пользователя в черный список.")

# Проверить, заблокирован ли пользователь
async def is_blacklisted(session: AsyncSession, user_id: int) -> bool:
    try:
        # Проверяем наличие пользователя в черном списке
        query = select(BlacklistUser).where(BlacklistUser.user_id == user_id)
        result = await session.execute(query)
        user = result.scalar_one_or_none()
        return user is not None
    except Exception as e:
        print(f"Ошибка при проверке пользователя с ID {user_id}: {e}")
        return False

# Получить всех пользователей в черном списке
async def get_all_blacklisted_users(session: AsyncSession):
    try:
        # Получаем список пользователей из черного списка
        result = await session.execute(select(BlacklistUser))
        users = result.scalars().all()  # Получаем все объекты BlacklistUser

        return users
    except Exception as e:
        print(f"Ошибка при получении пользователей: {e}")
        return []

# Количество клиентов в черном списке
async def count_blacklist_users(session: AsyncSession) -> int:
    try:
        # Запрос для подсчета всех записей в таблице BlacklistUser
        query = select(func.count(BlacklistUser.id))
        result = await session.execute(query)
        count = result.scalar()  # Получаем единственное значение (количество)
        return count
    except Exception as e:
        print(f"Ошибка при подсчете пользователей в черном списке: {e}")
        return None

# Добавить клиента в ЧС
async def add_user_to_blacklist(session: AsyncSession, user_id: int, username: str = None, reason: str = None):
    try:
        # Проверяем, есть ли уже такой пользователь в черном списке
        existing_user = await session.execute(select(BlacklistUser).filter_by(user_id=user_id))
        if existing_user.scalar_one_or_none():
            return "Этот пользователь уже в черном списке."

        # Создаем новый объект пользователя и добавляем его в черный список
        new_user = BlacklistUser(user_id=user_id, username=username, reason=reason)
        session.add(new_user)
        await session.commit()

        return f"Пользователь с ID {user_id} успешно добавлен в черный список."

    except Exception as e:
        print(f"Ошибка при добавлении пользователя в черный список: {e}")
        return "Произошла ошибка при добавлении пользователя."

# Удалить из черного списка
async def remove_user_from_blacklist(session: AsyncSession, user_id: int):
    try:
        # Получаем пользователя из черного списка по ID
        result = await session.execute(select(BlacklistUser).filter_by(user_id=user_id))
        user = result.scalar_one_or_none()

        if user is None:
            return f"Пользователь с ID {user_id} не найден в черном списке."

        # Удаляем пользователя
        await session.delete(user)
        await session.commit()

        return f"Пользователь с ID {user_id} успешно удален из черного списка."

    except Exception as e:
        # Логируем ошибку
        print(f"Ошибка при удалении пользователя с ID {user_id} из черного списка: {e}")

        # В случае ошибки откатываем транзакцию
        await session.rollback()

        return "Произошла ошибка при удалении пользователя из черного списка."