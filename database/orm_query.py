
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Product

async def orm_add_product(session: AsyncSession, data: dict):
    try:
        # Используем конструктор модели Product
        new_product = Product(
            name=data['name'],
            price=float(data['price']),  # Ожидаем цену в формате float или str
            count_day=int(data['count_day']) if data.get('count_day') else None
        )
        session.add(new_product)
        await session.commit()
    except Exception as e:
        print(f"Ошибка при добавлении продукта: {e}")
        await session.rollback()

async def orm_get_products(session: AsyncSession):
    query = select(Product)
    result = await session.execute(query)
    return result.scalars().all()


async def orm_get_product(session: AsyncSession, product_id: int):
    query = select(Product).where(Product.id == product_id)
    result = await session.execute(query)
    return result.scalar()


async def orm_update_product(session: AsyncSession, product_id: int, data):
    query = update(Product).where(Product.id == product_id).values(
        name=data["name"],
        price=float(data["price"]),
        )
    await session.execute(query)
    await session.commit()


async def orm_delete_product(session: AsyncSession, product_id: int):
    query = delete(Product).where(Product.id == product_id)
    await session.execute(query)
    await session.commit()
# Подсчет ко-ва продуктов
async def count_products(session: AsyncSession) -> int | None:
    try:
        # Подсчитываем количество записей в таблице Product
        query = select(func.count(Product.id))
        result = await session.execute(query)
        count = result.scalar()  # Получаем единственное значение (количество)
        return count
    except Exception as e:
        print(f"Ошибка при подсчете продуктов: {e}")
        return None

# Продукт с названием Акция

async def count_promotion_products(session: AsyncSession) -> int:
    try:
        # Запрос с использованием func.lower() для приведения к нижнему регистру
        query = select(func.count()).where(Product.name == "Акция")
        print(query)
        result = await session.execute(query)
        count = result.scalar()  # Получаем количество продуктов
        return count
    except Exception as e:
        print(f"Ошибка при подсчёте продуктов 'акция': {e}")
        return None



