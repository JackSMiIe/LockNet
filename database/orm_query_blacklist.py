# from sqlalchemy import delete
# from sqlalchemy.ext.asyncio import AsyncSession
# from sqlalchemy.future import select
# from .models import BlacklistUser
#
# # Добавить пользователя в черный список
# async def add_to_blacklist(session: AsyncSession, user_id: int, reason: str = None):
#     pass
#
#
# # Удалить пользователя из черного списка
# async def remove_from_blacklist(session: AsyncSession, user_id: int):
#     try:
#         # Составляем запрос на удаление
#         query = delete(BlacklistUser).where(BlacklistUser.user_id == user_id)
#         # Выполняем запрос
#         await session.execute(query)
#         await session.commit()
#         print(f"Пользователь с ID {user_id} удален.")
#     except Exception as e:
#         print(f"Ошибка при удалении пользователя с ID {user_id}: {e}")
#         await session.rollback()
#
# # Проверить, заблокирован ли пользователь
# async def is_blacklisted(session: AsyncSession, user_id: int) -> bool:
#     pass
#
# # Получить всех пользователей в черном списке
# async def get_all_blacklisted_users(session: AsyncSession):
#     try:
#         query = select(BlacklistUser)
#         result = await session.execute(query)
#         users = result.scalars().all()
#         return users
#     except Exception as e:
#         print(f"Ошибка при получении пользователей: {e}")
#         return []
