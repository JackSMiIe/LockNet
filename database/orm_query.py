
from sqlalchemy import select,update,delete
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

# """Запрос цены для дальнейшей оплаты"""
# async def orm_get_price(session: AsyncSession, product_id: int) -> int:
#     query = select(Product.price).where(Product.id == product_id)
#     result = await session.execute(query)
#     price = result.scalar()
#
#     if price is not None:
#         return int(price * 100)
#     else:
#         raise ValueError("Product not found")
