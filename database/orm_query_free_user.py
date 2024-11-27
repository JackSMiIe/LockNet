from sqlalchemy import select, update, delete, func
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import FreeUser



async def add_free_user(session: AsyncSession, user_id: int, username: str = None) -> bool:
    """
    Добавляет пользователя в таблицу FreeUser.
    Возвращает True, если пользователь добавлен успешно, иначе False.
    """
    try:
        new_user = FreeUser(user_id=user_id, username=username)
        session.add(new_user)
        await session.commit()
        return True
    except IntegrityError as e:
        await session.rollback()
        print(f"Ошибка добавления пользователя {user_id}: {e}")
        return False
    except SQLAlchemyError as e:
        await session.rollback()
        print(f"Общая ошибка SQLAlchemy при добавлении пользователя {user_id}: {e}")
        return False
    except Exception as e:
        print(f"Неизвестная ошибка при добавлении пользователя {user_id}: {e}")
        return False


async def get_all_free_users(session: AsyncSession) -> list[FreeUser]:
    """
    Получает всех пользователей из таблицы FreeUser.
    Возвращает список объектов FreeUser.
    """
    try:
        query = select(FreeUser)
        result = await session.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        print(f"Общая ошибка SQLAlchemy при получении всех пользователей: {e}")
        return []
    except Exception as e:
        print(f"Неизвестная ошибка при получении всех пользователей: {e}")
        return []


async def update_free_user_status(session: AsyncSession, user_id: int, status: bool) -> bool:
    """
    Обновляет статус пользователя по user_id в таблице FreeUser.
    Возвращает True, если статус обновлен, иначе False.
    """
    try:
        query = (
            update(FreeUser)
            .where(FreeUser.user_id == user_id)
            .values(status=status)
        )
        result = await session.execute(query)
        if result.rowcount > 0:
            await session.commit()
            return True
        await session.rollback()
        return False
    except SQLAlchemyError as e:
        await session.rollback()
        print(f"Общая ошибка SQLAlchemy при обновлении статуса пользователя {user_id}: {e}")
        return False
    except Exception as e:
        print(f"Неизвестная ошибка при обновлении статуса пользователя {user_id}: {e}")
        return False


async def delete_free_user(session: AsyncSession, user_id: int) -> bool:
    """
    Удаляет пользователя по user_id из таблицы FreeUser.
    Возвращает True, если пользователь удален, иначе False.
    """
    try:
        query = delete(FreeUser).where(FreeUser.user_id == user_id)
        result = await session.execute(query)
        if result.rowcount > 0:
            await session.commit()
            return True
        await session.rollback()
        return False
    except SQLAlchemyError as e:
        await session.rollback()
        print(f"Общая ошибка SQLAlchemy при удалении пользователя {user_id}: {e}")
        return False
    except Exception as e:
        print(f"Неизвестная ошибка при удалении пользователя {user_id}: {e}")
        return False

# Подсчет количества пользователей
async def count_free_users(session: AsyncSession) -> int | None:
    try:
        # Запрос для подсчета всех записей в таблице FreeUser
        query = select(func.count(FreeUser.id))
        result = await session.execute(query)
        count = result.scalar()  # Получаем единственное значение (количество)
        return count
    except Exception as e:
        print(f"Ошибка при подсчете пользователей в таблице FreeUser: {e}")
        return None  # Возвращаем None, если произошла ошибка