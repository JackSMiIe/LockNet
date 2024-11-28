from sqlalchemy import delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from .models import BlacklistUser

# Добавить пользователя в черный список
async def add_to_blacklist(session: AsyncSession, user_id: int, reason: str = None):
    try:
        # Создаем нового пользователя для добавления в черный список
        user = BlacklistUser(user_id=user_id, reason=reason)
        session.add(user)
        await session.commit()
        print(f"Пользователь с ID {user_id} добавлен в черный список.")
    except Exception as e:
        print(f"Ошибка при добавлении пользователя с ID {user_id}: {e}")
        await session.rollback()


# Удалить пользователя из черного списка
async def remove_from_blacklist(session: AsyncSession, user_id: int):
    try:
        # Составляем запрос на удаление
        query = delete(BlacklistUser).where(BlacklistUser.user_id == user_id)
        # Выполняем запрос
        await session.execute(query)
        await session.commit()
        print(f"Пользователь с ID {user_id} удален.")
    except Exception as e:
        print(f"Ошибка при удалении пользователя с ID {user_id}: {e}")
        await session.rollback()

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
        query = select(BlacklistUser)
        result = await session.execute(query)
        users = result.scalars().all()

        if users:
            # Формируем строку с перечнем всех пользователей и их данных
            user_list = "\n".join([
                f"ID: {user.user_id}, Причина: {user.reason}"
                for user in users
            ])
        else:
            user_list = "Черный список пуст."

        return user_list
    except Exception as e:
        print(f"Ошибка при получении пользователей из черного списка: {e}")
        return "Произошла ошибка при получении данных."

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
        user_to_remove = await session.execute(select(BlacklistUser).filter_by(user_id=user_id))
        user = user_to_remove.scalar_one_or_none()

        if user is None:
            return "Пользователь не найден в черном списке."

        # Удаляем пользователя
        await session.delete(user)
        await session.commit()

        return f"Пользователь с ID {user_id} успешно удален из черного списка."

    except Exception as e:
        print(f"Ошибка при удалении пользователя из черного списка: {e}")
        return "Произошла ошибка при удалении пользователя."