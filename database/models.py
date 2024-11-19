
from datetime import datetime, timedelta
from sqlalchemy import String, Boolean, DateTime, Text, func, Integer, DECIMAL,LargeBinary
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# Базовый класс с полями для отслеживания времени создания и обновления
class Base(DeclarativeBase):
    created: Mapped[DateTime] = mapped_column(DateTime, default=func.now())
    updated: Mapped[DateTime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())


# Класс продукта
class Product(Base):
    __tablename__ = 'product'

    id: Mapped[int] = mapped_column(Integer,primary_key=True)
    name: Mapped[str] = mapped_column(String(15), nullable=False)
    price: Mapped[int] = mapped_column(Integer,nullable=False) # Работать тут
    count_day: Mapped[int] = mapped_column(Integer, nullable=True)  # Пример столбца


# Класс пользователя
class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    status: Mapped[bool] = mapped_column(Boolean, default=False)

    subscription_start: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    subscription_end: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    def __init__(self, user_id, product: Product, username=None, status=False):
        self.user_id = user_id
        self.username = username
        self.status = status
        self.subscription_start = datetime.utcnow()

        # Установка даты окончания подписки
        if product.count_day:
            self.subscription_end = self.subscription_start + timedelta(days=product.count_day)
        else:
            self.subscription_end = None  # Если count_day не указан




    # config_file: Mapped[str] = mapped_column(Text, nullable=True)  # Содержимое config.conf
    # qr_code: Mapped[bytes] = mapped_column(LargeBinary, nullable=True)  # Поле для хранения QR-кода в бинарном виде
