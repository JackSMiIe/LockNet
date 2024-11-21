
import asyncio

from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from database import orm_query_users

async def check_subscriptions(session: AsyncSession):
    print('Hello')
    while True:
        print("Запуск проверки подписок...")
        try:
            # Получаем всех пользователей
            users = await orm_query_users.orm_get_products(session)

            # Если нет пользователей, просто пропускаем проверку
            if not users:
                print("Пользователей не найдено. Повторяем проверку через 12 часов...")
                await asyncio.sleep(43200)  # Ждем 12 часов перед повторной проверкой
                continue  # Переходим к следующей итерации цикла

            for user in users:
                # Проверяем дату окончания подписки
                if user.subscription_end and datetime.utcnow() > user.subscription_end:
                    if user.status:  # Если пользователь активен
                        user.status = False  # Деактивируем пользователя
                        username = f"user_{user.user_id}"

                        try:
                            process = await asyncio.create_subprocess_exec(
                                "sudo", "-S", "/usr/local/bin/pivpn", "-off","-n", username, "-y", # -n можно убрать или оставить(смотреть логи)
                                stdin=asyncio.subprocess.PIPE,
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE
                            )

                            stdout, stderr = await process.communicate(input=b'\n')

                            if process.returncode == 0:
                                print(f"Пользователь {user.username} c ID {user.user_id} деактивирован.\n"
                                      f"Вывод: {stdout.decode()}")
                            else:
                                print(f"Ошибка выполнения команды для {username}: {stderr.decode()}")

                        except asyncio.TimeoutError:
                            print(f"Команда для пользователя {username} превысила время ожидания.")
                        except Exception as e:
                            print(f"Ошибка при выполнении команды для {username}: {e}")

                        session.add(user)  # Добавляем изменения в сессию
            await session.commit()  # Фиксируем изменения в базе данных
            print("Проверка подписок завершена.")
        except Exception as e:
            print(f"Ошибка при проверке подписок: {e}")
            await session.rollback()  # Откат изменений при ошибке
        finally:
            if session:
                await session.close()  # Явное закрытие сессии

        # Ожидание перед следующей проверкой
        await asyncio.sleep(3600)  # Проверяем подписки каждый час


