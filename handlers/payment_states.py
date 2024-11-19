from aiogram.fsm.state import StatesGroup, State


class PaymentStates(StatesGroup):
    waiting_for_payment = State()        # Начало оплаты
    waiting_for_payment_2 = State()      # Ожидание подтверждения оплаты
    payment_successful = State()         # Состояние успешной оплаты
    generating_qr_and_config = State()   # Создание конфиг клиента
    sending_qr_and_config = State()      # Отправка конфиг и QR
    saving_client_info = State()         # Сохранение клиента в БД