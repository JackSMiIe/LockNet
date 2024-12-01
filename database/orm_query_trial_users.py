import asyncio

from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import TrialUser


async def count_trial_users(session: AsyncSession) -> int | None:
    try:
        # Запрос для подсчета всех записей в таблице UsedTrialUser
        query = select(func.count(TrialUser.id))
        result = await session.execute(query)
        count = result.scalar()  # Получаем единственное значение (количество)
        return count
    except Exception as e:
        print(f"Ошибка при подсчете пользователей в таблице UsedTrialUser: {e}")
        return None  # Возвращаем None, если произошла ошибка


# Метод для удаления пользователя из TrialUser и pivpn
async def remove_trial_user(session: AsyncSession, user_id: int):
    try:
        # Получаем пользователя из TrialUser по user_id
        result = await session.execute(select(TrialUser).filter(TrialUser.user_id == user_id))
        trial_user = result.scalars().first()

        if trial_user:
            print(f"Пользователь {trial_user.username} с ID {trial_user.user_id} найден в TrialUser.")

            # Удаление из pivpn
            username = f"user_{trial_user.user_id}"
            process = await asyncio.create_subprocess_exec(
                "sudo", "-S", "/usr/local/bin/pivpn", "-r", "-n", username, "-y",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=b'\n')

            if process.returncode == 0:
                print(f"(Trial) Пользователь {trial_user.username} с ID {trial_user.user_id} успешно удален из pivpn.\nВывод: {stdout.decode()}")

                # Теперь удаляем пользователя из базы данных TrialUser
                await session.execute(
                    delete(TrialUser).where(TrialUser.user_id == trial_user.user_id)
                )
                await session.commit()

                print(f"(Trial) Пользователь {trial_user.username} с ID {trial_user.user_id} удален из базы данных TrialUser.")
                return f"Пользователь {trial_user.username} с ID {trial_user.user_id} успешно удален из TrialUser и pivpn."
            else:
                print(f"(Trial) Ошибка при удалении пользователя {trial_user.username} из pivpn. Ошибка: {stderr.decode()}")
                return f"Ошибка при удалении пользователя {trial_user.username} из pivpn."
        else:
            print(f"Пользователь с ID {user_id} не найден в TrialUser.")
            return f"Пользователь с ID {user_id} не найден в пробном периоде."
    except Exception as e:
        print(f"(Trial) Ошибка при обработке пользователя с ID {user_id}: {e}")
        return f"Произошла ошибка при удалении пользователя с ID {user_id} из TrialUser."