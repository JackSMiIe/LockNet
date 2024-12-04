from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select, delete
import asyncio
import os
import logging
from database.models import Product, User, UsedTrialUser, TrialUser
from aiogram.types import LabeledPrice, FSInputFile
from bot_instance import bot
from datetime import datetime, timedelta

from database.orm_query_free_user import update_free_user_status
from database.orm_query_used_trial_user import get_all_users
from kbds.inline import get_inlineMix_btns



# Состояния оплаты
class PaymentStates(StatesGroup):
    waiting_for_payment = State()        # Начало оплаты
    waiting_for_payment_2 = State()      # Ожидание подтверждения оплаты
    payment_successful = State()         # Состояние успешной оплаты
    # generating_qr_and_config = State()   # Создание конфиг клиента
    # sending_qr_and_config = State()      # Отправка конфиг и QR
    # saving_client_info = State()         # Сохранение клиента в БД


#Обработчик для кнопки оплаты FSM
async def pay(callback: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    current_state = await state.get_state()
    if current_state not in [None, PaymentStates.payment_successful]:
        await callback.answer("Вы уже находитесь в процессе оплаты.", show_alert=True)
        return
    try:
        product_id = int(callback.data.split('_')[1])
        query = select(Product).where(Product.id == product_id)
        result = await session.execute(query)
        product = result.scalar()

        if product:
            await state.set_state(PaymentStates.waiting_for_payment)
            await bot.send_invoice(
                chat_id=callback.from_user.id,
                title="Оплата подписки",
                description=f"Тариф {product.name}",
                payload=f"wtf_{product_id}",
                provider_token=os.getenv('TOKEN_CASH'),
                currency='RUB',
                prices=[LabeledPrice(label=product.name, amount=int(product.price))],
            )
        else:
            await callback.answer("Продукт не найден", show_alert=True)
    except SQLAlchemyError as e:
        logging.error(f"Ошибка при запросе к базе данных: {str(e)}")
        await callback.answer("Ошибка базы данных", show_alert=True)
        await session.rollback()
    except Exception as e:
        logging.error(f"Неизвестная ошибка: {str(e)}")
        await callback.answer(f"Ошибка: {str(e)}", show_alert=True)
        await session.rollback()
    else:
        await session.commit()

# Обработчик для предварительной проверки платежа
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery, state: FSMContext):
    current_state = await state.get_state()
    if current_state == PaymentStates.waiting_for_payment:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)
        # Переключаемся на следующее состояние ожидания подтверждения платежа
        await state.set_state(PaymentStates.waiting_for_payment_2)
    else:
        await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=False,error_message="Ошибка: платеж не может быть обработан в текущем состоянии."
        )

# # Обработчик успешной оплаты
async def process_successful_payment(message: types.Message, state, session: AsyncSession):
    user_id = message.from_user.id
    username = message.from_user.username or f"user_{user_id}"

    # Проверка, что данные в платеже правильные
    try:
        if not message.successful_payment.invoice_payload.startswith('wtf'):
            await message.answer("Некорректные данные в платеже.")
            return

        # Извлечение product_id из payload
        product_id = int(message.successful_payment.invoice_payload.split('_')[1])

        # Получение продукта из базы данных
        product_query = select(Product).where(Product.id == product_id)
        product_result = await session.execute(product_query)
        product = product_result.scalar()

        if not product:
            await message.answer("Произошла ошибка: продукт не найден.")
            return

    except Exception as e:
        await message.answer(f"Ошибка при проверке платежа: {e}")
        return

    # Логика работы с пользователем (удаление из TrialUser и переход на платную подписку)
    try:
        # Получаем пользователя, который хочет перейти на платную подписку
        user_result = await session.execute(select(TrialUser).filter(TrialUser.user_id == user_id))
        user = user_result.scalars().first()

        if user:
            # Если пользователь найден в TrialUser
            print(f"Пользователь {user.username} с ID {user.user_id} найден в TrialUser.")

            # Удаляем пользователя из pivpn
            pivpn_username = f"user_{user.user_id}"
            try:
                process = await asyncio.create_subprocess_exec(
                    "sudo", "-S", "/usr/local/bin/pivpn", "-r", "-n", pivpn_username, "-y",
                    stdin=asyncio.subprocess.PIPE,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                stdout, stderr = await process.communicate(input=b'\n')

                if process.returncode == 0:
                    print(f"(Trial) Пользователь {user.username} с ID {user.user_id} успешно удален из pivpn.\nВывод: {stdout.decode()}")

                    # Теперь удаляем его из таблицы TrialUser
                    await session.execute(delete(TrialUser).where(TrialUser.user_id == user.user_id))
                    await session.commit()

                    print(f"(Trial) Пользователь {user.username} с ID {user.user_id} удален из базы данных TrialUser.")

                else:
                    print(f"(Trial) Ошибка при удалении пользователя {user.username} с ID {user.user_id} из pivpn. Ошибка: {stderr.decode()}")

            except Exception as e:
                print(f"(Trial) Ошибка при удалении пользователя {user.username} с ID {user.user_id} из pivpn: {e}")
        else:
            print(f"Пользователь с ID {user_id} не найден в TrialUser. Возможно, он уже не в пробной версии.")
            # Дополнительно: можно реализовать логику для перехода на платную подписку

    except Exception as e:
        print(f"(Trial) Общая ошибка при обработке пользователя: {e}")

    # Работа с платной подпиской
    try:
        # Проверка существования пользователя
        user_query = select(User).where(User.user_id == user_id)
        user_result = await session.execute(user_query)
        existing_user = user_result.scalar()

        current_date = datetime.utcnow()

        if existing_user:
            # Продление подписки
            if existing_user.subscription_end and existing_user.subscription_end > current_date:
                existing_user.subscription_end += timedelta(days=product.count_day)
            else:
                existing_user.subscription_start = current_date
                existing_user.subscription_end = current_date + timedelta(days=product.count_day)
                if not existing_user.status:
                    await activate_vpn_user(existing_user)

            await session.commit()
            formatted_date = existing_user.subscription_end.strftime("%d.%m.%Y")
            await message.answer(f"Подписка успешно продлена до {formatted_date}.")
        else:
            session.add(product)
            # Создание нового пользователя
            new_user = User(
                user_id=user_id,
                username=username,
                status=True,
                product=product  # передаем продукт для инициализации даты окончания подписки
            )

            # После создания new_user можно задать subscription_start и subscription_end
            new_user.subscription_start = datetime.utcnow()
            new_user.subscription_end = datetime.utcnow() + timedelta(days=product.count_day)

            users = await get_all_users(session) # Проверка на Триал
            if any(user.user_id == user_id for user in users):
                print("Вы в списке used_trial_user")
            else:
                used_trial_user = UsedTrialUser(user_id=user_id)
                session.add(used_trial_user)  # Добавляем нового пользователя
                print("Пользователь добавлен used_trial_user")

            # session.add(product)
            # new_user.product = product


            session.add(new_user)
            await session.commit()
            await message.answer("Вы успешно зарегистрированы.")

        # Обновление состояния и отправка QR-кода
        await state.set_state(PaymentStates.payment_successful)
        await generate_and_send_qr(message, state, session)

    except Exception as e:
        await session.rollback()
        await message.answer(f"Произошла ошибка при обработке оплаты. Подробности: {e}")


async def activate_vpn_user(user):

    username = f"user_{user.user_id}"

    try:
        # Выполнение команды активации
        process = await asyncio.create_subprocess_exec(
            "sudo", "-S", "/usr/local/bin/pivpn", "-on", "-n", username, "-y",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate(input=b'\n')


        if process.returncode == 0:
            user.status = True
            print(f"Пользователь {user.username} с ID {user.user_id} успешно активирован.\nВывод: {stdout.decode()}")


        else:
            print(f"Ошибка активации пользователя {username}. Код возврата: {process.returncode}\n"
                  f"Ошибка: {stderr.decode()}")
    except asyncio.TimeoutError:
        print(f"Время ожидания команды активации пользователя {username} истекло.")
    except Exception as e:
        print(f"Произошла ошибка при активации пользователя {username}: {e}")




# генерация кода
async def generate_and_send_qr(message: types.Message, state: FSMContext, session: AsyncSession):
    current_state = await state.get_state()
    if current_state == PaymentStates.payment_successful:
        user_id = message.from_user.id
        username = f"user_{user_id}"
        qr_path = f"/home/jacksmile/PycharmProjects/vpn_bot_v1.1/users_configs/qr_png/qr_{user_id}.png"
        config_path = f"/home/jacksmile/configs/{username}.conf"

        try:
            # Проверка, существует ли пользователь в базе данных
            query = select(User).where(User.user_id == user_id)
            result = await session.execute(query)
            existing_user = result.scalar()

            if existing_user:
                # Пользователь уже зарегистрирован — обновляем только подписку
                # await message.answer("Подписка успешно продлена.")
                await state.clear()
            else:
                # Добавляем нового пользователя в базу данных, если он еще не зарегистрирован
                # new_user = User(user_id=user_id, username=message.from_user.username, status=True)
                # session.add(new_user)
                # print('ДОБАВЛЕН')
                # await session.commit()
                await message.answer("Вы успешно зарегистрированы.")

            # Асинхронное добавление нового пользователя с помощью команды pivpn
            process = await asyncio.create_subprocess_exec(
                "sudo", "-S", "/usr/local/bin/pivpn", "-a", "-n", username,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(input=b'\n')
            if process.returncode != 0:
                try:
                    document = FSInputFile(config_path)
                    # Отправка конфигурационного файла пользователю
                    await bot.send_document(chat_id=message.chat.id, document=document)
                    # Сообщение об успешной генерации конфигурации
                    await message.answer(
                        f"<strong>{message.from_user.first_name}</strong>, ваш конфиг файл успешно сгенерирован.",
                        reply_markup=get_inlineMix_btns(btns={"Показать QR": f"qr_{user_id}"})
                    )
                    return  # Завершаем выполнение после успешной отправки документа
                except Exception as e:
                    # Если документ не найден или произошла ошибка при отправке
                    await message.answer("Ваши файлы не найдены. Обратитесь в техподдержку!")
                    return

            # Асинхронное создание QR-кода из конфигурационного файла
            process = await asyncio.create_subprocess_exec(
                "sudo", "-S", "qrencode", "-o", qr_path, "-r", config_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate()
            if process.returncode != 0:
                await message.answer(f"Ошибка при создании QR-кода: {stderr.decode()}")
                return

            # Отправка конфиг-файла пользователю
            document = FSInputFile(config_path)
            await bot.send_document(chat_id=message.chat.id, document=document)
            await message.answer(
                f"<strong>{message.from_user.first_name}</strong>, ваш конфиг файл успешно сгенерирован.",
                reply_markup=get_inlineMix_btns(btns={"Показать QR": f"qr_{user_id}"})
            )
            await state.clear()

        except Exception as e:
            await message.answer(f"Произошла неизвестная ошибка: {e}")
            await session.rollback()  # Откат транзакции в случае ошибки
            await state.clear()
        else:
            await session.commit()
