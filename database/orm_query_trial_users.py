from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import UsedTrialUser


async def count_used_trial_users(session: AsyncSession) -> int | None:
    try:
        # Запрос для подсчета всех записей в таблице UsedTrialUser
        query = select(func.count(UsedTrialUser.id))
        result = await session.execute(query)
        count = result.scalar()  # Получаем единственное значение (количество)
        return count
    except Exception as e:
        print(f"Ошибка при подсчете пользователей в таблице UsedTrialUser: {e}")
        return None  # Возвращаем None, если произошла ошибка