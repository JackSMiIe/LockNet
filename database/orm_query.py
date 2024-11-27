
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Product

async def orm_add_product(session: AsyncSession, data: dict):
    price_in_cents = int(round(float(data['price']) * 100))  # Округляем до двух знаков после запятой
    obj = Product(
        name=data['name'],
        price=price_in_cents,
        count_day=int(data['count_day'])
    )
    session.add(obj)
    await session.commit()

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


