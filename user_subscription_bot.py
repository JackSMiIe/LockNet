import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from bot_instance import bot
from database import orm_query_users,orm_query_trial_product


# Проверка окончания подписки клиентов и отключения их!
async def check_subscriptions(session: AsyncSession):
    while True:
        print("Запуск проверки подписок...")
        try:
            # Получаем всех пользователей
            users = await orm_query_users.orm_get_users(session)

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


# Использовали ли клиент Пробную подписку
async def check_subscriptions_trial(session: AsyncSession):
    while True:
        print("Запуск проверки Trial подписок...")
        try:
            # Получаем всех пользователей Trial
            users = await orm_query_trial_product.get_trial_products(session)

            if not users:
                print("(Trial) Пользователей Trial не найдено. Следующая проверка через 1 час...")
                await asyncio.sleep(3600)  # Ждем 1 час перед повторной проверкой
                continue

            for user in users:
                # Проверяем дату окончания подписки
                if user.subscription_end and datetime.utcnow() > user.subscription_end:
                    username = f"user_{user.user_id}"

                    try:
                        # Удаляем пользователя с помощью pivpn
                        process = await asyncio.create_subprocess_exec(
                            "sudo", "-S", "/usr/local/bin/pivpn", "-r", "-n", username, "-y",
                            stdin=asyncio.subprocess.PIPE,
                            stdout=asyncio.subprocess.PIPE,
                            stderr=asyncio.subprocess.PIPE
                        )
                        stdout, stderr = await process.communicate(input=b'\n')

                        if process.returncode == 0:
                            print(f"(Trial) Пользователь {user.username} с ID {user.user_id} "
                                  f"успешно удален из Trial подписки.\nВывод: {stdout.decode()}")
                            # Сообщение клиенту, что подписка закончилась
                            try:
                                await bot.send_message(
                                    chat_id=user.user_id,
                                    text=(
                                        f"Здравствуйте, {user.username}!\n\n"
                                        "Ваш пробный период закончился. "
                                        "Вы можете перейти на платный режим, чтобы продолжить пользоваться услугами. "
                                        "Для активации выберите подходящий тариф в боте."
                                    )
                                )
                                print(f"(Trial) Уведомление отправлено пользователю {user.user_id}.")
                            except Exception as notify_error:
                                print(f"(Trial) Ошибка отправки уведомления для {user.user_id}: {notify_error}")
                        else:
                            print(f"(Trial) Ошибка удаления для {username}: {stderr.decode()}")
                            continue  # Переход к следующему пользователю

                        # Убираем пользователя из базы
                        session.add(user)
                    except asyncio.TimeoutError:
                        print(f"(Trial) Команда для пользователя {username} превысила время ожидания.")
                    except Exception as e:
                        print(f"(Trial) Ошибка при выполнении команды для {username}: {e}")

            # Фиксируем изменения в базе
            await session.commit()
            print("(Trial) Проверка подписок завершена.")

        except Exception as e:
            print(f"(Trial) Ошибка при проверке Trial: {e}")
            await session.rollback()
        finally:
            if session:
                await session.close()

        # Ожидание перед следующей проверкой
        await asyncio.sleep(3600)  # Проверяем подписки каждый час
