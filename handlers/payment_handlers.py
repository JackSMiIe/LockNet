from aiogram import types
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import select
import os
import logging
from database.models import Product
from aiogram.types import LabeledPrice
from bot_instance import bot
from handlers.payment_states import PaymentStates


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
