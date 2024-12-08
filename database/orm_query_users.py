from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import User


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







