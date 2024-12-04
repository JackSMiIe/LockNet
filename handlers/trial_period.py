import asyncio

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import CallbackQuery, FSInputFile

from bot_instance import bot
from database.models import TrialUser, UsedTrialUser, TrialProduct
from aiogram import types

from kbds.inline import get_inlineMix_btns


async def process_trial_subscription(callback: CallbackQuery, session: AsyncSession):

    user_id = callback.from_user.id
    username = callback.from_user.username or "Не указан"

    try:
        # Проверяем, использовал ли пользователь пробную подписку ранее
        query = select(UsedTrialUser).where(UsedTrialUser.user_id == user_id)
        result = await session.execute(query)
        used_trial_user = result.scalar()

        if used_trial_user:
            return await callback.message.answer(
                "<b>У вас уже есть активная подписка или вы уже использовали свой пробный период</b>"
            ,parse_mode='HTML')

        # Извлекаем ID продукта из callback-данных
        product_id = int(callback.data.split('_')[2])

        # Проверяем, существует ли продукт
        result = await session.execute(select(TrialProduct).where(TrialProduct.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            return await callback.message.answer("Выбранный продукт не найден.")

        # Проверяем, есть ли пользователь уже в таблице TrialUser
        result = await session.execute(select(TrialUser).where(TrialUser.user_id == user_id))
        existing_user = result.scalar_one_or_none()
        if existing_user:
            return await callback.message.answer(
                "Вы уже используете пробный период. Дождитесь его окончания."
            )

        # Добавляем пользователя в таблицы TrialUser и UsedTrialUser
        trial_user = TrialUser(
            user_id=user_id,
            username=username,
            count_day=product.count_day
        )
        used_trial_user = UsedTrialUser(user_id=user_id)

        session.add(trial_user)
        session.add(used_trial_user)
        await session.commit()

        # Уведомляем об успешной регистрации
        await callback.message.answer(
            f"Вы успешно активировали пробный период на {product.count_day} дней. Спасибо, {username}!"
        )
        await generate_and_send_qr(callback.message, session,user_id)
        return


    except Exception as e:
        await session.rollback()  # Откатываем транзакцию при ошибке
        return await callback.message.answer(f"Произошла ошибка: {str(e)}")


async def generate_and_send_qr(message: types.Message, session: AsyncSession,user_id):
    user_id = user_id # Правки были тут user_id
    username = f"user_{user_id}"
    qr_path = f"/home/jacksmile/PycharmProjects/vpn_bot_v1.1/users_configs/qr_png/qr_{user_id}.png"
    config_path = f"/home/jacksmile/configs/{username}.conf"

    try:
        # Создание конфигурационного файла с помощью pivpn
        process = await asyncio.create_subprocess_exec(
            "sudo", "-S", "/usr/local/bin/pivpn", "-a", "-n", username,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate(input=b'\n')

        if process.returncode != 0:
            await message.answer(f"Ошибка при создании конфигурации: {stderr.decode()}")
            return

        # Генерация QR-кода для конфигурационного файла
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
        await message.answer(f"<strong>{message.from_user.first_name}</strong>, ваш конфиг файл успешно сгенерирован.",
                             reply_markup=get_inlineMix_btns(btns={"Показать QR": f"qr_{user_id}"}))

        # Подтверждаем успешное завершение транзакции
        await session.commit()


    except Exception as e:
        # Откатываем транзакцию в случае ошибки
        await session.rollback()
        await message.answer(f"Произошла ошибка: {str(e)}")
        print(f"Ошибка в процессе генерации и отправки QR-кода: {e}")
