from aiogram import types
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import os
from dotenv import load_dotenv


load_dotenv()  # Загрузка переменных окружения

ADMIN_LIST = list(map(int, os.getenv("ADMIN_LIST", "").split(',')))


# Состояния для FSM
# Обработчик для получения ID администратора
class AdminStates(StatesGroup):
    waiting_for_admin_id = State()
    waiting_dell_for_admin_id = State()

async def add_admin(callback_query: types.CallbackQuery, state: FSMContext):
    """Запрашивает ID нового администратора."""
    if callback_query.from_user.id not in ADMIN_LIST:
        await callback_query.answer("У вас нет прав для выполнения этой команды.")
        return

    await callback_query.message.answer("Пожалуйста, отправьте ID пользователя, которого вы хотите добавить в администраторы.")
    # Переходим в состояние ожидания ввода ID
    await state.set_state(AdminStates.waiting_for_admin_id)


async def process_admin_id(message: types.Message, state: FSMContext):
    """Обрабатывает введенный ID администратора и добавляет его."""
    if message.from_user.id not in ADMIN_LIST:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return  # Прерываем выполнение, но состояние не сбрасываем.

    try:
        new_admin_id = int(message.text)

        # Проверка, что ID состоит из 8-12 цифр
        if len(str(new_admin_id)) < 8 or len(str(new_admin_id)) > 12:
            await message.answer("ID должен быть числом длиной от 8 до 12 цифр.")
            return  # Прерываем выполнение, но состояние не сбрасываем

        if new_admin_id in ADMIN_LIST:
            await message.answer("Этот пользователь уже является администратором.")
        else:
            ADMIN_LIST.append(new_admin_id)
            update_env_admin_list()
            await message.answer(f"Пользователь {new_admin_id} добавлен в список администраторов.")

    except ValueError:
        await message.answer("Пожалуйста, укажите действительный ID пользователя, или введите 'отмена'")
        return  # Прерываем выполнение в случае ошибки, но состояние не сбрасываем

    await state.clear()  # Завершаем состояние только после успешной обработки


async def remove_admin(callback_query: types.CallbackQuery, state: FSMContext):
    """Запрашивает ID пользователя для удаления."""
    if callback_query.from_user.id not in ADMIN_LIST:
        await callback_query.answer("У вас нет прав для выполнения этой команды.")
        return

    await callback_query.message.answer("Пожалуйста, отправьте ID пользователя, которого вы хотите удалить из администраторов.")
    # Переходим в состояние ожидания ввода ID
    await state.set_state(AdminStates.waiting_dell_for_admin_id)

# Обработчик для получения ID администратора и удаления его
async def process_remove_admin_id(message: types.Message, state: FSMContext):
    """Обрабатывает введенный ID администратора и удаляет его."""
    if message.from_user.id not in ADMIN_LIST:
        await message.answer("У вас нет прав для выполнения этой команды.")
        return  # Прерываем выполнение, но состояние не сбрасываем.

    try:
        admin_id_to_remove = int(message.text)

        # Проверка, что ID состоит из 8-12 цифр
        if len(str(admin_id_to_remove)) < 8 or len(str(admin_id_to_remove)) > 12:
            await message.answer("ID должен быть числом длиной от 8 до 12 цифр.")
            return  # Прерываем выполнение, но состояние не сбрасываем

        if admin_id_to_remove not in ADMIN_LIST:
            await message.answer("Этот пользователь не является администратором.")
        else:
            ADMIN_LIST.remove(admin_id_to_remove)
            update_env_admin_list()
            await message.answer(f"Пользователь {admin_id_to_remove} удален из списка администраторов.")

    except ValueError:
        await message.answer("Пожалуйста, укажите действительный ID пользователя, или введите 'отмена'")
        return  # Прерываем выполнение в случае ошибки, но состояние не сбрасываем

    await state.clear()  # Завершаем состояние только после успешной обработки



async def list_admins(callback_query: types.CallbackQuery):
    """Выводит список администраторов."""
    if callback_query.from_user.id not in ADMIN_LIST:
        await callback_query.answer("У вас нет прав для выполнения этой команды.")
        return

    if not ADMIN_LIST:
        await callback_query.answer("Список администраторов пуст.")
    else:
        admin_list_str = "\n".join(map(str, ADMIN_LIST))
        await callback_query.message.answer(f"<b>Список администраторов:</b>\n{admin_list_str}",parse_mode="HTML")


def update_env_admin_list():
    """Обновляет файл .env с новым списком администраторов."""
    with open(".env", "r") as file:
        lines = file.readlines()

    with open(".env", "w") as file:
        for line in lines:
            if line.startswith("ADMIN_LIST"):
                file.write(f"ADMIN_LIST={','.join(map(str, ADMIN_LIST))}\n")
            else:
                file.write(line)
