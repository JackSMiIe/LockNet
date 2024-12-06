from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SupportTicket

# Все клиенты
async def get_all_users_with_tickets(session: AsyncSession):
    """Возвращает список всех пользователей с их обращениями."""
    query = select(SupportTicket.user_id, SupportTicket.username, SupportTicket.issue_description).distinct()
    result = await session.execute(query)
    return result.all()  # Возвращает список кортежей (user_id, username, issue_description)


# Не решенные задачи
async def get_all_users_with_tickets_false(session: AsyncSession):
    """Возвращает список всех пользователей с нерешенными обращениями."""
    query = (
        select(SupportTicket.id,SupportTicket.user_id, SupportTicket.username, SupportTicket.issue_description)
        .where(SupportTicket.is_resolved == False)  # Условие для нерешенных обращений
        .distinct()
    )
    result = await session.execute(query)
    return result.all()
# Решенные задачи
async def get_all_users_with_tickets_true(session: AsyncSession):
    result = await session.execute(select(SupportTicket).filter(SupportTicket.is_resolved == True))
    return result.scalars().all()

