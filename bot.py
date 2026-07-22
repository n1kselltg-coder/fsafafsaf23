import asyncio
import logging
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

BOT_TOKEN = "8215795192:AAEOZqO-dJSAob8aMgTFkKdwUps6PYcOXYc"
BOT_USERNAME = "chat_happy_robot"

CHANNEL_ID = -1003439175709   # Канал с обязательной подпиской
CHAT_ID = -1004311337325      # Чат где проверяем

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

def get_start_keyboard():
    add_to_channel_link = f"https://t.me/{BOT_USERNAME}?startchannel&admin=post_messages+delete_messages+invite_users"
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="➕ Добавить в канал",
            url=add_to_channel_link
        )],
        [InlineKeyboardButton(
            text="📢 Наш канал",
            url="https://t.me/+fPv5nnUrWLxjYzIy"
        )]
    ])
    return keyboard

def get_warning_keyboard():
    """Клавиатура с кнопкой Blog для предупреждения"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="Mory Blog",
            url="https://t.me/+fPv5nnUrWLxjYzIy"
        )]
    ])
    return keyboard

@dp.message(Command("start"))
async def start_command(message: types.Message):
    logger.info(f"📝 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) использовал /start")
    await message.answer(
        "🤖 Привет! Я бот для проверки подписки.\n\n"
        "Нажмите кнопку ниже, чтобы добавить меня в ваш канал:",
        reply_markup=get_start_keyboard()
    )

@dp.message(F.chat.id == CHAT_ID)
async def check_subscription(message: types.Message):
    # Пропускаем системные сообщения
    if message.from_user is None:
        logger.info(f"⏭️ Пропускаем системное сообщение (from_user is None)")
        return
    
    # Пропускаем сообщения от ботов
    if message.from_user.is_bot:
        logger.info(f"⏭️ Пропускаем сообщение от бота: {message.from_user.username}")
        return
    
    # Пропускаем сообщения от каналов (sender_chat)
    if message.sender_chat is not None:
        logger.info(f"⏭️ Пропускаем сообщение от канала: {message.sender_chat.title} (ID: {message.sender_chat.id})")
        return
    
    # Дополнительная проверка: пропускаем forward_from_chat (пересланные из канала)
    if message.forward_from_chat is not None:
        logger.info(f"⏭️ Пропускаем пересланное сообщение из канала: {message.forward_from_chat.title}")
        return
    
    # Дополнительная проверка: is_automatic_forward (автоматическая пересылка из канала в комментарии)
    if message.is_automatic_forward:
        logger.info(f"⏭️ Пропускаем автоматически пересланное сообщение из канала")
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    user_fullname = message.from_user.full_name
    
    logger.info(f"🔍 Проверка подписки: @{username} ({user_fullname}, ID: {user_id})")
    
    try:
        # Проверяем подписку на канал
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        
        # Если пользователь не подписан (left или kicked)
        if member.status in ("left", "kicked"):
            logger.warning(f"❌ @{username} (ID: {user_id}) не подписан на канал. Статус: {member.status}")
            await delete_and_warn(message, username, user_id)
        else:
            logger.info(f"✅ @{username} (ID: {user_id}) подписан на канал. Статус: {member.status}")
            
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.error(f"⚠️ Ошибка доступа для @{username} (ID: {user_id}): {e}")
        await delete_and_warn(message, username, user_id)
    except Exception as e:
        logger.error(f"💥 Неизвестная ошибка для @{username} (ID: {user_id}): {e}")

async def delete_and_warn(message: types.Message, username: str, user_id: int):
    try:
        # Удаляем сообщение
        await message.delete()
        logger.info(f"🗑️ Сообщение от @{username} (ID: {user_id}) успешно удалено")
        
        # Отправляем предупреждение с кнопкой
        await message.answer(
            "подпишитесь на Mory Blog чтобы продолжить общаться в чате",
            reply_markup=get_warning_keyboard()
        )
        logger.info(f"📢 Предупреждение с кнопкой отправлено для @{username} (ID: {user_id})")
        
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении/отправке для @{username} (ID: {user_id}): {e}")

async def main():
    logger.info("=" * 50)
    logger.info("🤖 Бот запущен и готов к работе")
    logger.info(f"📢 Отслеживаем чат: {CHAT_ID}")
    logger.info(f"📢 Проверяем подписку на канал: {CHANNEL_ID}")
    logger.info("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
