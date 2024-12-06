
from datetime import datetime, timedelta
from sqlalchemy import String, Boolean, DateTime, Text, func, Integer, DECIMAL, LargeBinary, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session, relationship


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

    def __init__(self, name: str, price: float, count_day: int = None):
        self.name = name
        self.price = int(round(price * 100))  # Конвертация цены в центы
        self.count_day = count_day
# Пробный продукт (всегда 1)
class TrialProduct(Base):
    __tablename__ = 'trial_product'

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(15), nullable=False)
    count_day: Mapped[int] = mapped_column(Integer, nullable=True)  # Количество дней пробного периода
    description: Mapped[str] = mapped_column(Text, nullable=True)  # Описание продукта (необязательно)

    def __init__(self, name: str, count_day: int, description: str = None):
        self.name = name
        self.count_day = count_day
        self.description = description

# Класс пользователя
class User(Base):
    __tablename__ = 'user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    rate: Mapped[int] = mapped_column(Integer, ForeignKey('product.id', ondelete="SET NULL"), nullable=True)  # Ссылка на id продукта
    status: Mapped[bool] = mapped_column(Boolean, default=False)

    subscription_start: Mapped[DateTime] = mapped_column(DateTime, nullable=True)
    subscription_end: Mapped[DateTime] = mapped_column(DateTime, nullable=True)

    product: Mapped["Product"] = relationship("Product", backref="users")  # Связь с продуктом

    def __init__(self, user_id, product: Product, username=None, status=False):
        self.user_id = user_id
        self.username = username
        self.status = status
        self.subscription_start = datetime.utcnow()

        # Устанавливаем дату окончания подписки в зависимости от count_day продукта
        if product.count_day:
            self.subscription_end = self.subscription_start + timedelta(days=product.count_day)
        else:
            self.subscription_end = None  # Если count_day не указан

        self.product = product


#Черный список
class BlacklistUser(Base):
    __tablename__ = 'blacklist'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)  # добавлено поле для username
    reason: Mapped[str] = mapped_column(Text, nullable=True)


    def __init__(self, user_id, username=None, reason=None):
        self.user_id = user_id
        self.username = username or "Не указано"  # если username не передан, то ставим значение "Не указано"
        self.reason = reason or "Причина не указана"

# Класс временных пользователей (триальная подписка)
class TrialUser(Base):
    __tablename__ = 'trial_user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    trial_start: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)
    trial_end: Mapped[DateTime] = mapped_column(DateTime, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    def __init__(self, user_id: int, count_day: int, username: str = None):
        self.user_id = user_id
        self.username = username
        self.trial_start = datetime.utcnow()
        self.trial_end = self.trial_start + timedelta(days=count_day)
        self.is_active = True

# Класс пользователей с бесплатным доступом
class FreeUser(Base):
    __tablename__ = 'free_user'

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    username: Mapped[str] = mapped_column(String(255), nullable=True)
    registered_on: Mapped[DateTime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[bool] = mapped_column(Boolean, default=True)

    def __init__(self, user_id: int, username: str = None):
        self.user_id = user_id
        self.username = username
        self.registered_on = datetime.utcnow()
        self.status = True
# Использованный пробный период ID клиентов (для невозможности использовать пробный период вновь)
class UsedTrialUser(Base):
    __tablename__ = "used_trial_user"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

# Поддержка
class SupportTicket(Base):
    __tablename__ = "support_tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)  # Уникальный ID обращения
    user_id: Mapped[int] = mapped_column(Integer, nullable=False)  # Telegram ID пользователя
    username: Mapped[str | None] = mapped_column(String(150), nullable=True)  # Имя пользователя (если есть)
    issue_description: Mapped[str] = mapped_column(Text, nullable=False)  # Текст обращения
    created_at: Mapped[datetime] = mapped_column(default=datetime.utcnow)  # Время создания обращения
    is_resolved: Mapped[bool] = mapped_column(Boolean, default=False)  # Статус обращения
    admin_response: Mapped[str | None] = mapped_column(Text, nullable=True)  # Ответ администратора (если есть)

    def __init__(self, user_id: int, username: str | None, issue_description: str):
        self.user_id = user_id
        self.username = username
        self.issue_description = issue_description

    def __repr__(self):
        return (
            f"<SupportTicket(id={self.id}, user_id={self.user_id}, username={self.username}, "
            f"created_at={self.created_at}, is_resolved={self.is_resolved})>"
        )
