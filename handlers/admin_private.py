from itertools import product

from aiogram import Router, types, F
from aiogram.filters import Command, or_f, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from sqlalchemy.ext.asyncio import AsyncSession

from handlers.admin_operations import AdminStates, process_remove_admin_id

from database.orm_query import orm_add_product, orm_get_products, orm_delete_product, count_products, \
    count_promotion_products
from database.orm_query_blacklist import get_all_blacklisted_users, add_to_blacklist, count_blacklist_users, \
    add_user_to_blacklist, remove_user_from_blacklist
from database.orm_query_free_user import count_free_users
from database.orm_query_trial_product import get_trial_products, add_trial_product, delete_trial_product, \
    count_trial_products
from database.orm_query_trial_users import count_trial_users
from database.orm_query_users import orm_count_users_with_true_status, count_inactive_users, count_total_users,orm_get_users
from filters.chat_types import ChatTypeFilter, IsAdmin
from handlers.admin_operations import add_admin, remove_admin, list_admins, process_admin_id
from kbds.inline import get_inlineMix_btns, get_callback_btns
from kbds.reply import get_keyboard


ADMIN_KB = get_keyboard(
    "📦 Товары",            # Кнопка для управления товарами
    "🚫 ЧС",                # Кнопка для управления черным списком
    "👤 Пользователи",      # Кнопка для управления пользователями
    "📊 Статистика",        # Кнопка для просмотра статистики
    "🔑 Администраторы",      # Кнопка для управления ролями
    placeholder="Выберите действие",
    sizes=(3, 2),         # Размеры для упорядочивания кнопок
)

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

# Главное меню администратора
@admin_router.message(Command("admin"))
async def admin_features(message: types.Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)
#-----------------
"""ЧС"""

# Получить черный список
# Класс для ввода текста(состояние)
class TextInputStates(StatesGroup):
    waiting_for_text = State()

@admin_router.message(F.text.lower() == 'черный список')
async def show_blacklist(message: types.Message, session: AsyncSession):
    # Получаем всех пользователей в черном списке
    users = await get_all_blacklisted_users(session)

    # Формируем сообщение с данными пользователей
    if users:
        blacklist_info = "\n".join(
            [f"ID: {user.user_id}, Username: {user.username}, Причина: {user.reason}" for user in users]
        )
        await message.answer(f"Список пользователей в черном списке:\n{blacklist_info}")
    else:
        await message.answer("Черный список пуст.")

# Внести в ЧС
@admin_router.message(F.text.lower() == "внести в чс")
async def start_blacklist_process(message: types.Message, state: FSMContext):
    # Отправляем сообщение с инструкцией и клавиатурой
    await message.answer(
        "Введите <b>ID</b> и <b>причину</b> через запятую. <b>Пример</b>: 424629424, Плохое поведение в чате",
        parse_mode='HTML',
        reply_markup=get_inlineMix_btns(btns={
            'Добавить в ЧС': 'add_to_blacklist_',
            'Отмена': 'cancel_handler_',
        })
    )

@admin_router.callback_query(F.data.startswith('add_to_blacklist_'))
async def process_blacklist_input(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    # Отправляем сообщение с инструкцией и запрашиваем ввод
    await callback_query.message.answer(
        "Введите <b>ID</b> и <b>причину</b> через запятую. <b>Пример</b>: 424629424, Плохое поведение в чате",
        parse_mode='HTML'
    )
    await state.set_state(TextInputStates.waiting_for_text)  # Устанавливаем состояние для ввода текста

@admin_router.message(TextInputStates.waiting_for_text)
async def handle_blacklist_input(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        # Проверяем наличие запятой в тексте
        if ',' not in message.text:
            await message.answer("Неверный формат. Введите ID и причину через запятую. Пример: 424629424, Плохое поведение в чате")
            return

        # Разделяем строку на ID и причину
        user_id_str, reason = map(str.strip, message.text.split(',', maxsplit=1))

        # Проверяем, что ID — это число
        if not user_id_str.isdigit():
            await message.answer("ID должен быть числом. Попробуйте снова.")
            return

        # Преобразуем ID в целое число
        user_id = int(user_id_str)

        # Добавляем пользователя в черный список
        await add_to_blacklist(session, user_id, reason)

        # Подтверждаем успешное добавление
        await message.answer(f"Пользователь с ID {user_id} добавлен в черный список.",reply_markup=ADMIN_KB)
        await state.clear()  # Завершаем FSM
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")
        await state.clear()


@admin_router.callback_query(StateFilter("*"),F.data == "cancel_handler_")
async def cancel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    # Проверяем, есть ли активное состояние
    if await state.get_state():
        await state.clear()  # Сбрасываем состояние
        await callback_query.message.answer("Действия отменены", reply_markup=ADMIN_KB)
    else:
        await callback_query.message.answer("Нет активных действий для отмены.")
#--------------


# Показ ассортимента товаров
@admin_router.message(F.text == '📦 Товары')
async def menu_cmd(message: types.Message, session: AsyncSession):
    await message.answer('<b>Выберите действие:</b>', reply_markup=get_inlineMix_btns(btns={
        'Добавить товар': 'добавить товар_',
        'Добавить акцию': 'добавить акцию_',
        'Пробный период' : 'пробный период_',
        'Ассортимент': 'ассортимент_',
        'Главное меню': 'назад_'
    }),parse_mode='HTML')

@admin_router.callback_query(F.data.startswith('пробный период_'))
async def trial_menu(callback_query: types.CallbackQuery, state: FSMContext):
    await callback_query.message.answer('Пробный период')
    await callback_query.message.answer('Действия:', reply_markup=get_inlineMix_btns(btns={
        'Просмотр': 'show_trial_',
        'Добавить': 'add_trial_',
    }))
# Удаление продукта
@admin_router.callback_query(F.data.startswith('delete_trial_'))
async def delete_trial_product_callback(callback_query: types.CallbackQuery, session: AsyncSession):
    try:
        # Печатаем callback_query.data для диагностики
        print(f"Полученные данные: {callback_query.data}")

        # Извлекаем product_id из callback_data
        data = callback_query.data.split('_')[-1]

        # Преобразуем ID продукта в целое число
        try:
            product_id = int(data)
        except ValueError:
            await callback_query.message.answer(f"Ошибка: некорректный ID продукта ({data}).")
            return

        # Вызываем функцию для удаления продукта
        deleted_product = await delete_trial_product(session, product_id)

        if deleted_product:
            # Если продукт был успешно удалён
            await callback_query.message.answer(f"Продукт с ID {product_id} был успешно удалён.")
        else:
            # Если продукт не найден
            await callback_query.message.answer(f"Продукт с ID {product_id} не найден или не удалось удалить.")

    except Exception as e:
        # Логируем и сообщаем об ошибке
        print(f"Произошла ошибка при удалении продукта: {str(e)}")
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")


# Получить все товары с пробным периодом
@admin_router.callback_query(F.data.startswith('show_trial_'))
async def trial_period_callback(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        # Получаем все продукты с пробным периодом
        products = await get_trial_products(session)

        if not products:
            # Если продуктов нет, отправляем сообщение и прекращаем выполнение
            await callback_query.message.answer('В ассортименте нет товаров.')
            return

        # Отправляем каждый продукт в отдельном сообщении
        for product in products:
            response_message = (f"<strong>{product.name}</strong>\n"
                                 f"Кол-во дней: {product.count_day}\n\n")
            await callback_query.message.answer(response_message, reply_markup=get_inlineMix_btns(btns={
                'Удалить': f"delete_trial_{product.id}"
            }))

    except Exception as e:
        # Логируем исключение и выводим информацию о проблемах
        print(f"Произошла ошибка при обработке запроса: {str(e)}")
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")

# Добавить товар пробный период
class ProductState(StatesGroup):
    waiting_for_product_name = State()
    waiting_for_product_days = State()

# Обработчик для добавления товара с пробным периодом
@admin_router.callback_query(F.data.startswith('add_trial_'))
async def add_trial_product_callback(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    try:
        # Проверяем, есть ли уже продукт с пробным периодом
        existing_products = await get_trial_products(session)

        if len(existing_products) >= 1:
            # Если в базе уже есть хотя бы один продукт с пробным периодом, выводим сообщение
            await callback_query.message.answer(
                "<b>В базе уже есть товар с пробным периодом. Только один товар может быть добавлен.</b>",parse_mode='HTML')
            return

        # Запрашиваем у пользователя название продукта
        await callback_query.message.answer("Введите название продукта:")

        # Переходим в состояние ожидания ввода названия
        await state.set_state(ProductState.waiting_for_product_name)

    except Exception as e:
        # Логируем исключение и выводим информацию о проблемах
        print(f"Произошла ошибка при добавлении продукта: {str(e)}")
        await callback_query.message.answer(f"Произошла ошибка: {str(e)}")

# Обработчик для получения названия товара
@admin_router.message(ProductState.waiting_for_product_name)
async def process_product_name(message: types.Message, state: FSMContext, session: AsyncSession):
    product_name = message.text.strip()

    # Проверка на пустое имя
    if not product_name:
        await message.answer("Название продукта не может быть пустым. Пожалуйста, введите название снова.")
        return

    # Сохраняем название в состоянии
    await state.update_data(product_name=product_name)

    # Переходим к запросу количества дней
    await message.answer("Введите количество дней пробного периода:")

    # Переходим в состояние ожидания ввода количества дней
    await state.set_state(ProductState.waiting_for_product_days)

# Обработчик для получения количества дней пробного периода
@admin_router.message(ProductState.waiting_for_product_days)
async def process_product_days(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        # Получаем количество дней и проверяем на корректность
        count_day = int(message.text.strip())
        if count_day <= 0:
            await message.answer("Количество дней должно быть положительным числом. Пожалуйста, введите снова.")
            return
    except ValueError:
        await message.answer("Пожалуйста, введите правильное количество дней.")
        return

    # Получаем данные из состояния
    user_data = await state.get_data()
    product_name = user_data.get("product_name")

    # Добавляем новый товар в базу данных
    try:
        new_product = await add_trial_product(session, product_name, count_day)
        await message.answer(f"Продукт <strong>{new_product.name}</strong> с пробным периодом на {new_product.count_day} дней успешно добавлен!")
    except Exception as e:
        await message.answer(f"Произошла ошибка при добавлении продукта: {str(e)}")

    # Завершаем состояние
    await state.clear()


# Ассортимент
@admin_router.callback_query(F.data.startswith('ассортимент_'))
async def menu_cmd(callback_query: types.CallbackQuery, session: AsyncSession):
    # Получаем все товары
    products = await orm_get_products(session)

    if not products:
        await callback_query.message.answer('В ассортименте нет товаров.')
        return

    # Разделяем товары на две категории: "Акция" и остальные
    action_products = [product for product in products if 'Акция' in product.name]
    other_products = [product for product in products if 'Акция' not in product.name]
    other_products = sorted(other_products, key=lambda p: p.name.lower())

    # Формируем сообщение с товарами с "Акция"
    if action_products:
        for product in action_products:
            response_message = (f"<strong>{product.name}</strong>\n"
                                 f"Цена: {product.price} руб.\n"
                                 f"Кол-во дней: {product.count_day}\n\n")
            # Отправляем товары с "Акция" и кнопки для управления
            await callback_query.message.answer(
                response_message,
                reply_markup=get_inlineMix_btns(btns={
                    'Удалить': f'delete_{product.id}',
                    'Назад': 'назад_'
                })
            )

    # Формируем сообщение с остальными товарами
    if other_products:
        for product in other_products:
            response_message = (f"<strong>{product.name}</strong>\n"
                                 f"Цена: {product.price} руб.\n"
                                 f"Кол-во дней: {product.count_day}\n\n")
            # Отправляем остальные товары и кнопки для управления
            await callback_query.message.answer(
                response_message,
                reply_markup=get_inlineMix_btns(btns={
                    'Удалить': f'delete_{product.id}',
                    'Назад': 'назад_'
                })
            )

    await callback_query.message.answer('Ок, актуальный прайс ⬆️')


# Обработка удаления товара
@admin_router.callback_query(F.data.startswith('delete_'))
async def delete_product(callback: types.CallbackQuery, session: AsyncSession):
    # Извлекаем ID продукта из данных callback
    product_id = int(callback.data.split('_')[-1])

    # Удаляем продукт из базы данных
    await orm_delete_product(session, product_id)

    # Ответ на callback-запрос
    await callback.answer('Товар удален', reply_markup=get_inlineMix_btns(btns={
        'Назад': 'назад_',
        'Ассортимент': 'ассортимент_',
    }))

    # Отправка сообщения с подтверждением удаления
    await callback.message.answer('Товар удален', reply_markup=get_inlineMix_btns(btns={
        'Назад': 'назад_',
        'Ассортимент': 'ассортимент_',

    }))

# Изменение товара
@admin_router.message(or_f(Command("change"), F.text.lower() == 'изменить товар'))
async def change_price(message: types.Message):
    await message.answer('Что будем менять?')

# Состояния для добавления товара
class AddProduct(StatesGroup):
    name = State()
    count_day = State()
    price = State()

# Начало добавления товара
@admin_router.callback_query(F.data.startswith('добавить товар_'))
async def admin_add(callback: types.CallbackQuery, state: FSMContext):
    print("Кнопка 'Добавить товар' нажата")  # Логирование
    await callback.message.answer("Введите название товара:", reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(AddProduct.name)

@admin_router.callback_query(F.data.startswith('добавить акцию_'))
async def admin_add(callback: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    # Получаем список продуктов
    promotion = await orm_get_products(session)

    # Проверяем, есть ли продукт с именем "Акция"
    existing_promotion = next((product for product in promotion if product.name.lower() == "акция"), None)

    if existing_promotion:
        # Если акция уже существует, сообщаем об этом
        await callback.message.answer(
            'Акция уже существует. Для добавления новой акции сначала удалите старую.')
        await state.clear()  # Очистим состояние, если это необходимо
    else:
        # Если акции нет, создаем новую
        await state.update_data(name="Акция")
        await callback.message.answer("Введите количество дней акции:", reply_markup=get_inlineMix_btns(btns={
            'Отмена' : 'назад_'
        }))
        await state.set_state(AddProduct.count_day)  # Переводим в следующее состояние для ввода цены

# Команда отмены
# Команда отмены
@admin_router.message(StateFilter("*"), or_f(Command("отмена"), F.text.casefold() == "отмена"))
async def cancel_handler(message: types.Message, state: FSMContext):
    if await state.get_state():
        await state.clear()  # Очистка состояния
        await message.answer("Действия отменены", reply_markup=ADMIN_KB)
    else:
        await message.answer("Нет активных действий для отмены.", reply_markup=ADMIN_KB)


# Команда "назад" для возврата на предыдущий шаг
@admin_router.message(StateFilter("*"), or_f(Command("назад"), F.text.casefold() == "назад"))
async def back_step_handler(message: types.Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state == AddProduct.count_day.state:
        await state.set_state(AddProduct.name)
        await message.answer("Введите название товара заново:")
    elif current_state == AddProduct.price.state:
        await state.set_state(AddProduct.count_day)
        await message.answer("Введите количество дней подписки заново:")
    else:
        await message.answer("Вы на первом шаге или неверная команда.")

# Обработка ввода названия товара
@admin_router.message(AddProduct.name, F.text)
async def add_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Введите количество дней подписки:")
    await state.set_state(AddProduct.count_day)

# Обработка ввода количества дней подписки
@admin_router.message(AddProduct.count_day, F.text)
async def add_count_day(message: types.Message, state: FSMContext):
    if not message.text.isdigit():
        await message.answer("Введите корректное число для количества дней!")
        return
    await state.update_data(count_day=int(message.text))
    await message.answer("Введите стоимость товара:")
    await state.set_state(AddProduct.price)

# Обработка ввода цены товара
@admin_router.message(AddProduct.price, F.text)
async def add_price(message: types.Message, state: FSMContext, session: AsyncSession):
    try:
        price = float(message.text)
        if price < 80:
            await message.answer("Цена должна быть больше 80!")
            return
    except ValueError:
        await message.answer("Введите корректное число для стоимости!")
        return

    await state.update_data(price=price)
    data = await state.get_data()

    try:
        await orm_add_product(session, data)
        await message.answer("Товар успешно добавлен!",reply_markup=get_inlineMix_btns(btns={
            'Ассортимент': 'ассортимент_',
            'Назад': 'назад_'
        }))

    except Exception as e:
        await message.answer(f"Ошибка при добавлении товара: {e}")
    finally:
        await state.clear()

# Обработка нажатия на кнопку "Назад" для возвращения в главное меню
@admin_router.callback_query(F.data == 'назад_')
async def back_to_menu(callback_query: types.CallbackQuery, state: FSMContext):
    # Очистить текущее состояние
    await state.clear()
    # Ответ на нажатие кнопки "Назад"
    await callback_query.message.answer("Вы вернулись в меню.", reply_markup=ADMIN_KB)

# @admin_router.callback_query(F.data == 'назад')
# async def back_to_menu(callback_query: types.CallbackQuery):
#     await callback_query.message.answer("Вы вернулись в меню.", reply_markup=ADMIN_KB)

# Команды для выхода и отмены в любое время
@admin_router.message(or_f(F.text.lower() == 'выход', F.text.lower() == 'отмена'))
async def admin_exit(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Выход выполнен.", reply_markup=ADMIN_KB)


@admin_router.message(F.text.lower() == 'количество активных пользователей')
async def count_active_users(message: types.Message, session: AsyncSession):
    count = await orm_count_users_with_true_status(session)
    await message.answer(f"Количество активных пользователей (со статусом True): {count}", reply_markup=ADMIN_KB)

# Общая статистика
@admin_router.message(F.text == '📊 Статистика')
async def statistic(message: types.Message, session: AsyncSession):
    # Получаем количество активных пользователей
    active_users = await orm_count_users_with_true_status(session)

    # Подсчет клиентов с пробным периодом
    trial_users = await count_trial_users(session)
    # Черный список
    black_list = await count_blacklist_users(session)
    # Подсчет кл-ва продуктов
    count_product = await count_products(session)
    # Подсчет Безлимитных клиентов
    free_users = await count_free_users(session)
    # Подсчет ко-ва Акций
    trial_product = await count_trial_products(session)
    # Получаем количество неактивных пользователей
    inactive_users_count = await count_inactive_users(session)
    # Продукт с названием акция
    promotion_product = await count_promotion_products(session)
    # Получаем общее количество пользователей
    total_users_count = await count_total_users(session)

    # Формируем сообщение
    stats_message = (
        f"Количество активных пользователей : {active_users}\n"
        f"Неактивных пользователей : {inactive_users_count}\n"
        f"Всего пользователей : {total_users_count}\n"
        f"Безлимитных клиентов : {free_users}\n"
        f"Клиенты с пробным периодом : {trial_users}\n" # отс тут 
        f"Кл-во созданных продуктов : {count_product}\n"
        f"Кл-во Акций : {promotion_product}\n"
        f"Пробный продукт(должен быть всегда = 1) : {trial_product}\n"
        f"В черном списке :{black_list}")

    # Отправляем все статистики в одном сообщении
    await message.answer(stats_message)

"""Черный список (ЧС)"""
@admin_router.message(F.text == '🚫 ЧС')
async def black_list(message: types.Message, session: AsyncSession):
    await message.answer('Выберите действие: ', reply_markup=get_inlineMix_btns(btns={
        'Список клиентов(ЧС)': 'get_users_',
        'Добавить клиента': 'add_users_',
        'Удалить клиента': 'dell_users_',

    }))
# Показать список ЧС
@admin_router.callback_query(F.data == 'get_users_')
async def delete_user_from_blacklist(callback_query: types.CallbackQuery, session: AsyncSession):
    try:
        # Получаем список пользователей из черного списка
        users_list = await get_all_blacklisted_users(session)
        if not users_list:
            await callback_query.message.answer("<b>Список пуст.</b>",parse_mode='HTML')
            return

        for user in users_list:
            formatted_user = f"ID: {user.user_id}, Username: {user.username or 'Нет имени'}"

            await callback_query.message.answer(formatted_user)


    except Exception as e:
        print(f"Ошибка при получении пользователей: {e}")
        await callback_query.message.answer(f"Произошла ошибка при получении списка пользователей: {str(e)}")



# Удаление из ЧС
@admin_router.callback_query(F.data == 'dell_users_')
async def delete_user_from_blacklist(callback_query: types.CallbackQuery, session: AsyncSession):
    try:
        # Получаем список пользователей из черного списка
        users_list = await get_all_blacklisted_users(session)

        # Если список пуст, отправляем сообщение
        if not users_list:
            await callback_query.message.answer("<b>Список пуст.</b>",parse_mode='HTML')
            return

        # Формируем кнопки для каждого пользователя
        for user in users_list:
            formatted_user = f"ID: {user.user_id}, Username: {user.username or 'Нет имени'}"
            callback_data = f'dellUser_{user.user_id}_{user.username}'

            buttons = get_inlineMix_btns(btns={
                'Удалить из ЧС': callback_data
            })

            # Отправляем сообщение с кнопками для удаления из ЧС
            await callback_query.message.answer(formatted_user, reply_markup=buttons)

    except Exception as e:
        # Логируем ошибку
        print(f"Ошибка при получении пользователей: {e}")
        await callback_query.message.answer("Произошла ошибка при получении списка пользователей.")

# Удаление из ЧС
@admin_router.callback_query(F.data.startswith('dellUser_'))
async def remove_user_from_blacklist_handler(callback_query: types.CallbackQuery, session: AsyncSession):
    try:
        # Извлекаем данные из callback_data
        data = callback_query.data.split('_')
        if len(data) < 3:
            await callback_query.answer("Неверный формат данных.")
            return

        user_id = int(data[1])  # user_id находится во втором элементе
        username = '_'.join(data[2:])  # username — это все, что идет после user_id

        # Логируем процесс удаления
        print(f"Получен запрос на удаление из ЧС для пользователя: ID={user_id}, Username={username}")

        # Удаляем пользователя из черного списка
        result = await remove_user_from_blacklist(session, user_id)

        # Отправляем результат удаления
        await callback_query.answer(result)
        if "успешно" in result:
            await callback_query.message.answer(
                f"Пользователь {username} с ID {user_id} был успешно удален из черного списка.")
        else:
            await callback_query.message.answer(f"Ошибка: {result}")


    except Exception as e:
        # Логируем ошибку и отправляем пользователю сообщение
        print(f"Ошибка при удалении пользователя из ЧС: {e}")
        await callback_query.answer("Произошла ошибка при удалении пользователя из черного списка.")



# Выводит весь список пользователей и кнопку добавить в ЧС
@admin_router.callback_query(F.data == 'add_users_')
async def black_list_users(callback_query: types.CallbackQuery, session: AsyncSession):
    try:
        # Получаем список пользователей
        users_list = await orm_get_users(session)

        # Если список пуст, отправляем сообщение
        if not users_list:
            await callback_query.message.answer("<b>Список пуст.</b>",parse_mode='HTML')
            return

        # Создаем сообщение и кнопки для каждого пользователя
        for user in users_list:
            formatted_user = f"ID: {user.user_id}, Username: {user.username or 'Нет имени'}"
            # Формируем callback_data с передачей user_id и username
            callback_data = f'addUser_{user.user_id}_{user.username}'

            # Кнопки для добавления в черный список
            buttons = get_inlineMix_btns(btns={
                'Добавить в ЧС': callback_data
            })

            # Отправляем сообщение с кнопками для каждого пользователя
            await callback_query.message.answer(formatted_user, reply_markup=buttons)
    except Exception as e:
        # Логируем и отправляем сообщение об ошибке
        print(f"Ошибка: {e}")
        await callback_query.message.answer("Произошла ошибка при получении пользователей.")

# Добавление по кнопке Добавить
@admin_router.callback_query(F.data.startswith('addUser_'))
async def add_user_black(callback: types.CallbackQuery, session: AsyncSession):
    try:
        # Извлекаем данные из callback_data
        data = callback.data.split('_')
        if len(data) < 3:
            await callback.answer("Неверный формат данных. Ожидается формат 'addUser_<user_id>_<username>'.")
            return

        user_id = int(data[1])  # user_id находится во втором элементе
        username = '_'.join(data[2:])  # username — это все, что идет после user_id

        # Если username пустой, присваиваем значение "Не указано"
        if not username:
            username = 'Не указано'

        # Логируем username и user_id
        print(f"Получен запрос на добавление в ЧС для пользователя: ID={user_id}, Username={username}")

        # Вставляем пользователя в черный список
        # Здесь передаем правильный объект сессии
        await add_to_blacklist(callback.message, session, user_id, username)

        # Отправляем ответ
        await callback.message.answer(f"Пользователь {username} с ID {user_id} был добавлен в черный список.")
    except Exception as e:
        # Логируем ошибку и отправляем пользователю сообщение
        print(f"Ошибка при добавлении пользователя в ЧС: {e}")
        await callback.answer("Произошла ошибка при добавлении пользователя в черный список.")


"""Администраторы"""
@admin_router.message(F.text == '🔑 Администраторы')
async def admin_panel(message: types.Message, session: AsyncSession):
    await message.answer('Выберите действие: ', reply_markup=get_inlineMix_btns(btns={
        'Добавить': 'addAdmin_',
        'Удалить': 'removeAdmin_',
        'Список': 'listAdmins_',
    }))
# Добавление Администратора
@admin_router.callback_query(F.data.startswith('addAdmin_'))
async def handle_add_admin(callback_query: types.CallbackQuery, state: FSMContext):
    """Хэндлер для удаления администратора."""
    await add_admin(callback_query,state)
@admin_router.message(AdminStates.waiting_for_admin_id)
async def process_admin_id_message(message: types.Message, state: FSMContext):
    """Обрабатывает введенный ID администратора."""
    await process_admin_id(message, state)
    await message.answer('Выберите действие:', reply_markup=ADMIN_KB)

# Удаление Администратора
@admin_router.callback_query(F.data.startswith('removeAdmin_'))
async def handle_remove_admin(callback_query: types.CallbackQuery,state: FSMContext):
    """Хэндлер для удаления администратора."""
    await remove_admin(callback_query,state)

@admin_router.message(AdminStates.waiting_dell_for_admin_id)
async def process_admin_id_message(message: types.Message, state: FSMContext):
    """Обрабатывает введенный ID администратора."""
    await process_remove_admin_id(message, state)
    await message.answer('Выберите действие:',reply_markup=ADMIN_KB)


# Список Администраторов
@admin_router.callback_query(F.data.startswith('listAdmins_'))
async def handle_list_admins(callback_query: types.CallbackQuery):
    """Хэндлер для удаления администратора."""
    await list_admins(callback_query)