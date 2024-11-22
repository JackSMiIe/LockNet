from sqlalchemy import delete
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
        return users
    except Exception as e:
        print(f"Ошибка при получении пользователей: {e}")
        return []
