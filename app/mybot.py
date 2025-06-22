import asyncio
import logging
import mysql.connector
import random
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart, Command
from aiogram.enums import ParseMode

API_TOKEN = '5370836512:AAGYIQmlyaHRrdZ3kmUHTqfsaWXLnDjrZJo'  # 🔐 Замени на свой токен

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

sessions = {}

QUOTES = [
    "Действуй! Даже если страшно.",
    "Ты справишься — я верю.",
    "Одна задача за раз!",
    "Маленький шаг — тоже движение.",
]

# DB функции
def db_conn():
    return mysql.connector.connect(
        host='db',
        user='root',
        password='root',
        database='lab1'
    )

def get_tasks():
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("SELECT id, text FROM items")
    tasks = cursor.fetchall()
    conn.close()
    return tasks

def add_task(text):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("INSERT INTO items (text) VALUES (%s)", (text,))
    conn.commit()
    conn.close()

def delete_task(task_id):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE id = %s", (task_id,))
    conn.commit()
    conn.close()

def update_task(task_id, new_text):
    conn = db_conn()
    cursor = conn.cursor()
    cursor.execute("UPDATE items SET text = %s WHERE id = %s", (new_text, task_id))
    conn.commit()
    conn.close()

# Главное меню
def get_main_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Список задач"), KeyboardButton(text="➕ Добавить задачу")],
            [KeyboardButton(text="💬 Цитата"), KeyboardButton(text="📤 Переслать список")]
        ],
        resize_keyboard=True
    )

# /start
@dp.message(CommandStart())
async def start(message: types.Message):
    sessions[message.chat.id] = {"step": "login"}
    await message.answer("Введите логин:")

# /quote
@dp.message(Command("quote"))
async def quote(message: types.Message):
    await message.answer(random.choice(QUOTES))

# /add (альтернатива кнопке)
@dp.message(Command("add"))
async def add(message: types.Message):
    chat_id = message.chat.id
    session = sessions.get(chat_id, {})
    if not session.get("authenticated"):
        await message.answer("⛔ Сначала авторизуйтесь через /start")
        return
    session["step"] = "add_task"
    await message.answer("Введите текст новой задачи:")

# /forward
@dp.message(Command("forward"))
async def forward(message: types.Message):
    chat_id = message.chat.id
    session = sessions.get(chat_id, {})
    if not session.get("authenticated"):
        await message.answer("⛔ Сначала авторизуйтесь через /start")
        return
    args = message.text.split()
    if len(args) < 2:
        await message.answer("Использование: /forward <user_id>")
        return
    user_id = int(args[1])
    tasks = get_tasks()
    text = "\n".join([f"{t[0]}: {t[1]}" for t in tasks])
    try:
        await bot.send_message(chat_id=user_id, text=f"📋 Список задач:\n{text}")
        await message.answer("✅ Список отправлен.")
    except Exception as e:
        await message.answer(f"Ошибка: {e}")

# Обработка обычных сообщений
@dp.message(F.text)
async def handle_text(message: types.Message):
    chat_id = message.chat.id
    session = sessions.get(chat_id, {})

    # ⛔ Проверка авторизации
    if not session.get("authenticated") and session.get("step") not in ["login", "password"]:
        await message.answer("⛔ Сначала авторизуйтесь через /start")
        return

    # Авторизация
    if session.get("step") == "login":
        session["login"] = message.text.strip()
        session["step"] = "password"
        await message.answer("Введите пароль:")
        return

    if session.get("step") == "password":
        session["password"] = message.text.strip()
        if session["login"] == "admin" and session["password"] == "admin":
            session["authenticated"] = True
            session["step"] = "choose_task"
            await message.answer("✅ Успешный вход!", reply_markup=get_main_menu())
        else:
            await message.answer("❌ Неверный логин или пароль. Попробуйте снова: /start")
            sessions.pop(chat_id, None)
        return

    # Добавление новой задачи
    if session.get("step") == "add_task":
        task_text = message.text.strip()
        add_task(task_text)
        await message.answer("✅ Задача добавлена!", reply_markup=get_main_menu())
        session["step"] = "choose_task"
        return

    # Редактирование задачи
    if session.get("step") == "edit_task":
        task_id = session.get("edit_id")
        update_task(task_id, message.text.strip())
        await message.answer("✅ Задача обновлена.", reply_markup=get_main_menu())
        session["step"] = "choose_task"
        return

    # Обработка кнопок меню
    if message.text == "📋 Список задач":
        await show_tasks_menu(message)
    elif message.text == "➕ Добавить задачу":
        session["step"] = "add_task"
        await message.answer("Введите текст новой задачи:")
    elif message.text == "💬 Цитата":
        await message.answer(random.choice(QUOTES))
    elif message.text == "📤 Переслать список":
        await message.answer("Используйте команду: /forward <user_id>")

# Callback-кнопки (редактирование и удаление)
@dp.callback_query()
async def task_chosen(callback: types.CallbackQuery):
    chat_id = callback.message.chat.id
    session = sessions.get(chat_id, {})

    # ⛔ Проверка авторизации
    if not session.get("authenticated"):
        await callback.message.answer("⛔ Сначала авторизуйтесь через /start")
        return

    data = callback.data

    if data.startswith("delete_"):
        task_id = int(data.split("_")[1])
        delete_task(task_id)
        await callback.message.answer("🗑 Задача удалена.")
        await show_tasks_menu(callback.message)
    elif data.startswith("edit_"):
        task_id = int(data.split("_")[1])
        session["step"] = "edit_task"
        session["edit_id"] = task_id
        await callback.message.answer("✏️ Введите новый текст задачи:")

# Показ задач с кнопками
async def show_tasks_menu(message):
    chat_id = message.chat.id
    session = sessions.get(chat_id, {})

    # ⛔ Проверка авторизации
    if not session.get("authenticated"):
        await message.answer("⛔ Сначала авторизуйтесь через /start")
        return

    session["step"] = "choose_task"
    tasks = get_tasks()
    if not tasks:
        await message.answer("📭 Список задач пуст.")
        return

    for task_id, text in tasks:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="✏️ Редактировать", callback_data=f"edit_{task_id}"),
                    InlineKeyboardButton(text="🗑 Удалить", callback_data=f"delete_{task_id}")
                ]
            ]
        )
        await message.answer(f"<b>{text}</b>", reply_markup=keyboard, parse_mode=ParseMode.HTML)

# Запуск
if __name__ == '__main__':
    asyncio.run(dp.start_polling(bot))
