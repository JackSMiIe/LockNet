# Внешние библиотеки
from aiogram import Router, F
from aiogram.filters import Command, or_f, StateFilter
# ORM-запросы
from database.orm_support import *
from database.orm_query import *
from database.orm_query_blacklist import *
from database.orm_query_free_user import *
from database.orm_query_trial_product import *
from database.orm_query_trial_users import *
from database.orm_query_users import *
# Фильтры
from filters.chat_types import ChatTypeFilter, IsAdmin
# Обработчики администратора
from handlers.admin_operations import *
# Обработчики пользователей
from handlers.user_private_operations import *
from handlers.user_private_support import *
# Кнопки
from kbds.inline import get_inlineMix_btns
from kbds.reply import get_keyboard

# from aiogram import Router, types, F
# from aiogram.filters import Command, or_f, StateFilter
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import StatesGroup, State
# from sqlalchemy import select
#
# from sqlalchemy.ext.asyncio import AsyncSession
#
# from bot_instance import bot
# from database.models import User
# from database.orm_support import get_all_users_with_tickets, get_all_users_with_tickets_false, \
#     get_all_users_with_tickets_true
# from handlers.admin_operations import AdminStates, process_remove_admin_id
#
# from database.orm_query import orm_add_product, orm_get_products, orm_delete_product, count_products, \
#     count_promotion_products
# from database.orm_query_blacklist import get_all_blacklisted_users, add_to_blacklist, count_blacklist_users, \
#     add_user_to_blacklist, remove_user_from_blacklist
# from database.orm_query_free_user import count_free_users
# from database.orm_query_trial_product import get_trial_products, add_trial_product, delete_trial_product, \
#     count_trial_products
# from database.orm_query_trial_users import count_trial_users
# from database.orm_query_users import orm_count_users_with_true_status, count_inactive_users, count_total_users, \
#     orm_get_users
# from filters.chat_types import ChatTypeFilter, IsAdmin
# from handlers.admin_operations import add_admin, remove_admin, list_admins, process_admin_id
# from handlers.user_private_operations import show_all_users, send_config_and_qr_button, get_active, \
#     delete_user_by_id_from_pivpn, toggle_pivpn_user
# from handlers.user_private_support import resolve_ticket, send_answer_to_client
# from kbds.inline import get_inlineMix_btns, get_callback_btns
# from kbds.reply import get_keyboard


ADMIN_KB = get_keyboard(
    "📦 Товары",            # Кнопка для управления товарами
    "🚫 ЧС",                # Кнопка для управления черным списком
    "👤 Пользователи",      # Кнопка для управления пользователями
    "📊 Статистика",        # Кнопка для просмотра статистики
    "🔑 Администраторы",
    "Support",# Кнопка для управления ролями
    placeholder="Выберите действие",
    sizes=(3, 3),         # Размеры для упорядочивания кнопок
)

admin_router = Router()
admin_router.message.filter(ChatTypeFilter(["private"]), IsAdmin())

# Главное меню администратора
@admin_router.message(Command("admin"))
async def admin_features(message: types.Message):
    await message.answer("Что хотите сделать?", reply_markup=ADMIN_KB)


"""Пользователи"""
class AdminState(StatesGroup):
    waiting_for_message = State()
    waiting_for_message_all = State()

# Отмена действий
@admin_router.message(StateFilter("*"), or_f(Command("отмена"), F.text.casefold() == "отмена"))
async def cancel_handler(message: types.Message, state: FSMContext):
    if await state.get_state():
        await state.clear()  # Очистка состояния
        await message.answer("Действия отменены", reply_markup=ADMIN_KB)
    else:
        await message.answer("Нет активных действий для отмены.", reply_markup=ADMIN_KB)

@admin_router.callback_query(F.data == 'cancel_handler_')
async def cancel_handler(callback_query: types.CallbackQuery, state: FSMContext):
    # Отменяем процесс
    await callback_query.message.answer("Операция отменена.", reply_markup=ADMIN_KB)
    await state.clear()


# Активация/Деактивация
@admin_router.callback_query(F.data.startswith("activate_user_"))
async def activate_user(callback_query: types.CallbackQuery, session: AsyncSession):
    user_id = int(callback_query.data.split("_")[2])

    async with session.begin():
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if user:
            user.status = True
            session.add(user)
            await session.commit()

            # Активация в PiVPN
            if await toggle_pivpn_user(user_id, "on"):
                await callback_query.message.answer(f"Пользователь {user.username} был активирован в системе и в PiVPN.")
            else:
                await callback_query.message.answer(f"Пользователь {user.username} был активирован в системе, но не удалось изменить статус в PiVPN.")
        else:
            await callback_query.message.answer(f"Пользователь с ID {user_id} не найден.")


@admin_router.callback_query(F.data.startswith("deactivate_user_"))
async def deactivate_user(callback_query: types.CallbackQuery, session: AsyncSession):
    user_id = int(callback_query.data.split("_")[2])

    async with session.begin():
        result = await session.execute(select(User).where(User.user_id == user_id))
        user = result.scalar_one_or_none()

        if user:
            user.status = False
            session.add(user)
            await session.commit()

            # Деактивация в PiVPN
            if await toggle_pivpn_user(user_id, "off"):
                await callback_query.message.answer(f"Пользователь {user.username} был деактивирован в системе и в PiVPN.")
            else:
                await callback_query.message.answer(f"Пользователь {user.username} был деактивирован в системе, но не удалось изменить статус в PiVPN.")
        else:
            await callback_query.message.answer(f"Пользователь с ID {user_id} не найден.")


@admin_router.message(or_f(Command("users"), (F.text == "👤 Пользователи")))
async def users_list(message: types.Message):
    await message.answer('Выберите действие: ', reply_markup=get_inlineMix_btns(btns={
        'Управление клиентами': 'users_list_',
        'Рассылка': 'newsletter_',

    }))
# Удаление пользователя
@admin_router.callback_query(F.data.startswith("delete_user_"))
async def confirm_delete_user(callback_query: types.CallbackQuery):
    user_id = callback_query.data.split("_")[-1]

    # Запрашиваем подтверждение удаления
    await callback_query.message.answer(
        f"Вы уверены, что хотите удалить пользователя с ID {user_id}?",
        reply_markup=get_inlineMix_btns(btns={
            "Да, удалить": f"confirm_delete_user_{user_id}",
            "Отмена": "cancel_handler_",
        })
    )

@admin_router.callback_query(F.data.startswith("confirm_delete_user_"))
async def delete_user(callback_query: types.CallbackQuery, session: AsyncSession):
    user_id = int(callback_query.data.split("_")[-1])

    try:
        # Сначала удаляем пользователя из PiVPN
        pivpn_deleted = await delete_user_by_id_from_pivpn(user_id)

        if not pivpn_deleted:
            await callback_query.message.answer(f"Не удалось удалить пользователя с ID {user_id} из PiVPN.")
            return

        async with session.begin():
            # Удаление пользователя из базы данных
            result = await session.execute(select(User).where(User.user_id == user_id))
            user = result.scalar_one_or_none()

            if user:
                await session.delete(user)
                await session.commit()
                await callback_query.message.answer(f"Пользователь с ID {user_id} успешно удален из базы данных.")
            else:
                await callback_query.message.answer(f"Пользователь с ID {user_id} не найден.")

    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка при удалении пользователя. Ошибка: {e}")

# Показать всех клиентов
@admin_router.callback_query(F.data == 'users_list_')
async def handle_show_users(callback_query: types.CallbackQuery, session: AsyncSession):
    await show_all_users(callback_query, session)
# Обработка нажатия на кнопку "Просмотр Конфиг"
@admin_router.callback_query(F.data.startswith("view_config_"))
async def handle_view_config(callback_query: types.CallbackQuery, state: FSMContext):
    # Извлекаем user_id из callback_data
    user_id = callback_query.data.split("_")[-1]

    # Вызов функции для отправки конфигов и QR-кода
    await send_config_and_qr_button(callback_query.message, int(user_id))

# Кнопка Управление клиентами
@admin_router.callback_query(F.data.startswith('write_user_'))
async def handle_write_user(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        # Извлечение ID пользователя из callback_data
        user_id = callback_query.data.split('_')[-1]

        # Сохраняем ID пользователя в состоянии
        await state.update_data(target_user_id=user_id)

        # Запрашиваем ввод сообщения
        await callback_query.message.answer(
            f"Введите сообщение для пользователя с ID {user_id}:"
        ,reply_markup=get_inlineMix_btns(btns={
                'Отмена': 'cancel_handler_'
            }))

        # Переход в состояние ожидания сообщения
        await state.set_state(AdminState.waiting_for_message)

    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка: {e}")
# Кнопка Управление клиентами
@admin_router.message(AdminState.waiting_for_message)
async def handle_admin_message(message: types.Message, state: FSMContext):
    try:
        # Получаем сохраненные данные (ID целевого пользователя)
        data = await state.get_data()
        target_user_id = data.get("target_user_id")

        if not target_user_id:
            await message.answer("Ошибка: пользователь не выбран.")
            return

        # Сохраняем сообщение в состоянии
        await state.update_data(admin_message=message)

        # Спрашиваем подтверждение у администратора
        await message.answer(
            f"<b>Вы уверены, что хотите отправить это сообщение?</b>\n\n"
            f"<b>Сообщение:</b>\n{message.text if message.text else '[не текстовое сообщение]'}",
            parse_mode='HTML',
            reply_markup=get_inlineMix_btns(btns={
                'Подтвердить отправку': 'confirm_send',
                'Отмена': 'cancel_handler_'
            })
        )
    except Exception as e:
        await message.answer(f"Произошла ошибка: {e}")

@admin_router.callback_query(F.data == 'confirm_send')
async def confirm_send(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        # Получаем данные из состояния
        data = await state.get_data()
        target_user_id = data.get("target_user_id")
        admin_message = data.get("admin_message")

        if not target_user_id or not admin_message:
            await callback_query.message.answer("Ошибка: данные для отправки отсутствуют.")
            await state.clear()
            return

        # Отправляем сообщение в зависимости от его типа
        if admin_message.document:
            await bot.send_document(
                chat_id=target_user_id,
                document=admin_message.document.file_id,
                caption="Конфиг от администратора"
            )
        elif admin_message.photo:
            await bot.send_photo(
                chat_id=target_user_id,
                photo=admin_message.photo[-1].file_id,
                caption="Изображение от администратора"
            )
        elif admin_message.text:
            await bot.send_message(
                chat_id=target_user_id,
                text=f"<b>Сообщение от администратора:</b>\n{admin_message.text}",
                parse_mode='HTML'
            )
        else:
            await callback_query.message.answer("Тип сообщения не поддерживается.")

        # Подтверждаем успешную отправку
        await callback_query.message.answer("Сообщение успешно отправлено!")

        # Сбрасываем состояние
        await state.clear()

    except Exception as e:
        await callback_query.message.answer(f"Произошла ошибка при отправке сообщения: {e}")

@admin_router.callback_query(F.data == 'newsletter_')
async def handle_newsletter(callback_query: types.CallbackQuery):
    # Кнопки для выбора шаблона рассылки
    template_buttons = get_inlineMix_btns(btns={
        'Шаблон 1: На сервере ведутся работы': 'template_1',
        'Шаблон 2: Обновление на сервере': 'template_2',
        'Шаблон 3: Сервер работает': 'template_3',
        'Свой шаблон': 'custom_template',  # Добавляем кнопку для собственного шаблона
    })
    await callback_query.message.answer('Выберите шаблон для рассылки:', reply_markup=template_buttons)
# Обработчик для выбора шаблона
@admin_router.callback_query(F.data.in_(['template_1', 'template_2', 'template_3', 'custom_template']))
@admin_router.callback_query(F.data.in_(['template_1', 'template_2', 'template_3', 'custom_template']))
async def handle_template_selection(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    selected_template = callback_query.data
    await state.update_data(selected_template=selected_template)

    if selected_template in ['template_1', 'template_2', 'template_3']:
        # Получаем текст шаблона
        template_text = get_template_text(selected_template)
        # Добавляем префикс "Сообщение от Администратора"
        full_text = f"Сообщение от Администратора:\n\n{template_text}"
        await state.update_data(message_text=full_text)

        # Отправляем сообщение для подтверждения
        await callback_query.message.answer(
            f"Вы выбрали следующий текст для рассылки:\n\n{full_text}\n\nПодтвердите отправку.",
            reply_markup=get_inlineMix_btns(btns={
                'Подтвердить': 'confirm_message_all',
                'Отмена': 'cancel_handler_'
            })
        )

    else:
        # Запрашиваем текст для custom_template
        await callback_query.message.answer(
            "Введите сообщение, которое будет отправлено всем пользователям:",
            reply_markup=get_inlineMix_btns(btns={'Отмена': 'cancel_handler_'})
        )
        await state.set_state(AdminState.waiting_for_message_all)


@admin_router.message(AdminState.waiting_for_message_all)
async def handle_custom_template_message(message: types.Message, state: FSMContext):
    # Сохраняем введенный текст
    custom_text = message.text
    full_text = f"Сообщение от Администратора:\n\n{custom_text}"
    await state.update_data(message_text=full_text)

    # Запрашиваем подтверждение отправки
    await message.answer(
        f"Вы ввели следующий текст для рассылки:\n\n{full_text}\n\nПодтвердите отправку.",
        reply_markup=get_inlineMix_btns(btns={
            'Подтвердить': 'confirm_message_all',
            'Отмена': 'cancel_handler_'
        })
    )


@admin_router.callback_query(F.data == 'confirm_message_all')
async def confirm_and_send_newsletter(callback_query: types.CallbackQuery, state: FSMContext, session: AsyncSession):
    # Получаем текст сообщения из состояния
    data = await state.get_data()
    template_text = data.get('message_text')

    if not template_text:
        await callback_query.message.answer("Ошибка: текст для рассылки не найден.")
        await state.clear()
        return

    # Отправка сообщения всем активным пользователям
    await send_newsletter_to_users(template_text, session, callback_query.message, state)


# Функция для получения текста шаблона
def get_template_text(selected_template):
    templates = {
        'template_1': "В настоящий момент сервер временно недоступен, так как ведутся технические работы. Пожалуйста, ожидайте. Мы сообщим, когда доступность будет восстановлена.",
        'template_2': "На сервере проводятся обновления. Это может повлиять на работу системы. Мы работаем над тем, чтобы все было готово в кратчайшие сроки.",
        'template_3': "Мы рады сообщить, что сервер снова работает в обычном режиме. Все системы восстановлены, и теперь доступность сервиса полностью восстановлена.\n\nСпасибо за терпение!"
    }
    return templates.get(selected_template, "")
# Функция для отправки рассылки
async def send_newsletter_to_users(template_text, session, message, state):
    # Получаем список активных пользователей
    active_users = await get_active(session)

    if not active_users:
        await message.answer("Нет активных пользователей для рассылки.")
        await state.clear()
        return

    # Отправляем сообщение всем активным пользователям
    for user in active_users:
        try:
            await bot.send_message(chat_id=user.user_id, text=template_text)
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {user.user_id}: {e}")

    # Подтверждение рассылки
    await message.answer(f"Рассылка успешно отправлена всем {len(active_users)} активным пользователям!")

    # Сбрасываем состояние
    await state.clear()

"""Поддержка"""
@admin_router.message(or_f(Command("support"), (F.text.casefold() == "support")))
async def support_list(message: types.Message):
    await message.answer('Выберите действие: ', reply_markup=get_inlineMix_btns(btns={
        'Список проблем': 'support_list_',
        'Завершённые': 'true_list_',

    }))


@admin_router.callback_query(F.data == 'true_list_')
async def show_support(callback_query: types.CallbackQuery, session: AsyncSession):
    try:
        # Получаем всех пользователей с открытыми обращениями (status = True или аналогичный флаг)
        users = await get_all_users_with_tickets_true(session)

        # Проверяем, есть ли пользователи с обращениями
        if users:
            # Если есть, выводим информацию по каждому из них
            for user in users:
                user_info = (
                    f"<b>№ Обращения:</b> {user.id}\n"
                    f"<b>ID:</b> {user.user_id}\n"
                    f"<b>Username:</b> @{user.username}\n"
                    f"<b>Причина:</b> {user.issue_description}\n"
                )
                await callback_query.message.answer(
                    f"<b>Обращение:</b>\n{user_info}",
                    parse_mode='HTML'
                )
        else:
            # Если нет пользователей с обращениями
            await callback_query.message.answer("Нет пользователей с активными обращениями.")

    except Exception as e:
        # Обрабатываем возможные ошибки и логируем их
        print(f"Ошибка при получении тикетов: {e}")
        await callback_query.message.answer("Произошла ошибка при загрузке обращений. Попробуйте позже.")


# Нерешенные задачи
@admin_router.callback_query(F.data == 'support_list_')
async def show_support(callback_query: types.CallbackQuery, session: AsyncSession):
    users = await get_all_users_with_tickets_false(session)
    if users:
        for user in users:
            user_info = (
                f"№ Обращения: {user.id}\n"
                f"ID: {user.user_id}\n"
                f"Username: {user.username}\n"
                f"Причина: {user.issue_description}\n"
            )
            # Создаем callback_data, включающую ticket_id, user_id и описание проблемы
            callback_data_answer = f"answer_{user.id}_{user.user_id}_{user.issue_description}"
            callback_data_complete = f"complete_{user.user_id}_{user.issue_description}"

            await callback_query.message.answer(
                f"<b>Обращение:</b>\n{user_info}",
                parse_mode='HTML',
                reply_markup=get_inlineMix_btns(btns={
                    'Ответить': callback_data_answer,
                    'Спам': callback_data_complete,
                })
            )
    else:
        await callback_query.message.answer("Нет пользователей с нерешенными обращениями.")


# Ответ Администратора
class TicketAnswerState(StatesGroup):  # Наследуем от StatesGroup
    waiting_for_answer = State()


# Запуск состояния FSM
@admin_router.callback_query(F.data.startswith('answer_'))
async def handle_answer_ticket(callback_query: types.CallbackQuery, session: AsyncSession, state: FSMContext):
    # Извлекаем ticket_id, user_id и issue_description из callback_data
    _, ticket_id, user_id, issue_description = callback_query.data.split('_', 3)

    # Сохраняем ticket_id, user_id и описание проблемы в FSM, чтобы они были доступны при ответе
    await state.update_data(ticket_id=ticket_id, user_id=user_id, issue_description=issue_description)

    # Запрашиваем у администратора текст ответа
    await callback_query.message.answer("Введите ваш ответ на обращение клиента:")

    # Переходим в состояние ожидания ответа от администратора
    await state.set_state(TicketAnswerState.waiting_for_answer)


# Обработка сообщения администратора с ответом
@admin_router.message(TicketAnswerState.waiting_for_answer)
async def admin_reply_to_ticket(message: types.Message, state: FSMContext,session: AsyncSession):
    # Получаем данные из FSM
    user_data = await state.get_data()
    ticket_id = user_data.get('ticket_id')
    user_id = user_data.get('user_id')
    issue_description = user_data.get('issue_description')

    if not ticket_id or not user_id or not issue_description:
        await message.answer("Ошибка: Не удалось найти данные тикета.")
        return

    admin_message = message.text  # Ответ администратора

    try:
        # Отправляем ответ клиенту
        response_message = await send_answer_to_client(ticket_id,user_id, admin_message,issue_description)

        # Информируем администратора о том, что ответ отправлен и тикет закрыт
        await message.answer(f"Ответ на Обращения №{ticket_id} отправлен клиенту: {response_message}")

        # Закрытие тикета (если нужно)
        # await close_ticket_in_database(ticket_id, session)

        # Завершаем состояние FSM
        await resolve_ticket(session, user_id, issue_description)

        await state.clear()

    except Exception as e:
        await message.answer(f"Произошла ошибка при отправке ответа: {str(e)}")


# Функция для закрытия тикета (если необходимо)


 # Spam
@admin_router.callback_query(F.data.startswith('complete_'))
async def complete_support(callback_query: types.CallbackQuery, session: AsyncSession):
    # Извлекаем user_id и issue_description из callback_data
    _, user_id, issue_description = callback_query.data.split('_', 2)

    # Преобразуем user_id в integer
    user_id = int(user_id)

    # Выполняем функцию resolve_ticket, чтобы пометить задачу как решенную
    success = await resolve_ticket(session, user_id, issue_description)

    if success:
        await callback_query.message.answer("Задача успешно решена.")
    else:
        await callback_query.message.answer("Задача не найдена или не требует решения.")





"""ЧС"""
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
async def black_list(message: types.Message):
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
async def admin_panel(message: types.Message):
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

# Удаление Администратора
@admin_router.callback_query(F.data.startswith('removeAdmin_'))
async def handle_remove_admin(callback_query: types.CallbackQuery,state: FSMContext):
    """Хэндлер для удаления администратора."""
    await remove_admin(callback_query,state)

@admin_router.message(AdminStates.waiting_dell_for_admin_id)
async def process_admin_id_message(message: types.Message, state: FSMContext):
    """Обрабатывает введенный ID администратора."""
    await process_remove_admin_id(message, state)


# Список Администраторов
@admin_router.callback_query(F.data.startswith('listAdmins_'))
async def handle_list_admins(callback_query: types.CallbackQuery):
    """Хэндлер для удаления администратора."""
    await list_admins(callback_query)