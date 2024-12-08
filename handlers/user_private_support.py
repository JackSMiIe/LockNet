from bot_instance import bot
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import SupportTicket


# Функция для принудительного решения задачи
async def resolve_ticket(session: AsyncSession, user_id: int, issue_description: str):
    """Помечает задачу как решенную."""
    query = (
        select(SupportTicket)
        .where(SupportTicket.user_id == user_id, SupportTicket.issue_description == issue_description)
    )

    result = await session.execute(query)
    ticket = result.scalar_one_or_none()

    if ticket:
        ticket.is_resolved = True  # Помечаем задачу как решенную
        await session.commit()  # Сохраняем изменения
        return True
    else:
        return False

# Функция для отправки сообщения клиенту
async def send_answer_to_client(ticket_id: int, user_id: int, admin_message: str, issue_description: str):
    """Отправка сообщения клиенту."""
    try:
        await bot.send_message(
            user_id,
            f"Ваше обращение №{ticket_id} было решено.\n\n"
            f"<b>Ваше обращение:</b> {issue_description}\n\n"
            f"<b>Ответ от администратора:</b> {admin_message}",
            parse_mode='HTML'  # Используем HTML для форматирования
        )
        return "Успешно"
    except Exception as e:
        return f"Ошибка при отправке ответа: {str(e)}"

