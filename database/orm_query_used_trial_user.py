from sqlalchemy import select, delete
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import UsedTrialUser


async def add_user(session: AsyncSession, user_id: int) -> bool:
    """
    Добавляет пользователя в таблицу UsedTrialUser.
    Возвращает True, если пользователь добавлен успешно, иначе False.
    """
    try:
        new_user = UsedTrialUser(user_id=user_id)
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


async def get_all_users(session: AsyncSession) -> list[UsedTrialUser]:
    """
    Получает всех пользователей из таблицы UsedTrialUser.
    Возвращает список объектов UsedTrialUser.
    """
    try:
        query = select(UsedTrialUser)
        result = await session.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        print(f"Общая ошибка SQLAlchemy при получении всех пользователей: {e}")
        return []
    except Exception as e:
        print(f"Неизвестная ошибка при получении всех пользователей: {e}")
        return []


async def delete_user(session: AsyncSession, user_id: int) -> bool:
    """
    Удаляет пользователя по user_id из таблицы UsedTrialUser.
    Возвращает True, если пользователь удален, иначе False.
    """
    try:
        query = delete(UsedTrialUser).where(UsedTrialUser.user_id == user_id)
        result = await session.execute(query)
        if result.rowcount > 0:  # Проверяем, были ли строки затронуты
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
