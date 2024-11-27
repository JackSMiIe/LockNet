from sqlalchemy import delete, func
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from database.models import TrialProduct


# Получить продукт
async def get_trial_products(session: AsyncSession):
    try:
        # Получаем все продукты с пробным периодом (count_day > 0)
        query = select(TrialProduct)
        result = await session.execute(query)
        return result.scalars().all()
    except SQLAlchemyError as e:
        # Логируем ошибку, чтобы легче было отладить проблему
        print(f"Ошибка при получении продуктов: {e}")
        return []  # Возвращаем пустой список вместо None

# Добавить продукт
async def add_trial_product(session: AsyncSession, name: str, count_day: int):
    try:
        # Создаем новый экземпляр продукта с пробным периодом
        new_product = TrialProduct(name=name, count_day=count_day)

        # Добавляем продукт в сессию
        session.add(new_product)

        # Коммитим изменения в базе данных
        await session.commit()
        return new_product
    except SQLAlchemyError as e:
        # Логируем ошибку, чтобы легче было отладить проблему
        print(f"Ошибка при добавлении продукта: {e}")
        await session.rollback()  # Откатываем изменения в случае ошибки
        return None


# Удалить продукт
async def delete_trial_product(session: AsyncSession, product_id: int):
    try:
        # Получаем продукт по id
        product = await session.get(TrialProduct, product_id)

        if product:
            # Удаляем продукт из сессии
            await session.delete(product)

            # Коммитим изменения в базе данных
            await session.commit()
            print(f"Продукт удален.")
            return product  # Возвращаем удаленный продукт

        else:
            print(f"Продукт с ID {product_id} не найден.")
            return None  # Возвращаем None, если продукта нет в базе

    except SQLAlchemyError as e:
        # Логируем ошибку
        print(f"Ошибка при удалении продукта: {e}")
        await session.rollback()  # Откатываем изменения в случае ошибки
        return None
# Подсчет кл-ва Акций
async def count_trial_products(session: AsyncSession) -> int | None:
    try:
        # Подсчитываем количество записей в таблице TrialProduct
        query = select(func.count(TrialProduct.id))
        result = await session.execute(query)
        count = result.scalar()  # Получаем единственное значение (количество)
        return count
    except Exception as e:
        print(f"Ошибка при подсчете продуктов в пробном периоде: {e}")
        return None