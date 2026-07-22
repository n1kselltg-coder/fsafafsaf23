import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ChatPermissions
from aiogram.exceptions import TelegramForbiddenError, TelegramBadRequest
import re

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

def get_unmute_keyboard(user_id: int):
    """Клавиатура с кнопкой снятия мута"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text="🔓 Снять мут",
            callback_data=f"unmute_{user_id}"
        )]
    ])
    return keyboard

def contains_url(text: str) -> bool:
    """Проверяет содержит ли текст ссылку"""
    url_pattern = re.compile(
        r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
        r'|'
        r'(?:www\.)[a-zA-Z0-9-]+(?:\.[a-zA-Z]{2,})+(?:[/?#]\S*)?'
        r'|'
        r't\.me/\S+'
        r'|'
        r'@\w+'
    )
    return bool(url_pattern.search(text))

def is_iris_message(message: types.Message) -> bool:
    """Проверяет является ли сообщение от Iris"""
    # Проверяем по username бота (если известно)
    if message.from_user.username and message.from_user.username.lower() == 'iris':
        return True
    # Или проверяем по ID бота Iris (нужно узнать точный ID)
    # if message.from_user.id == IRIS_BOT_ID:
    #     return True
    return False

def is_iris_moderation_message(text: str) -> bool:
    """Проверяет содержит ли сообщение информацию о модерации"""
    moderation_keywords = [
        'мут', 'mute', 'замучен', 'muted',
        'бан', 'ban', 'забанен', 'banned',
        'варн', 'warn', 'предупреждение', 'warning',
        'разбан', 'unban', 'разбанен', 'unbanned',
        'размут', 'unmute', 'размучен', 'unmuted'
    ]
    
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in moderation_keywords)

@dp.message(Command("start"))
async def start_command(message: types.Message):
    logger.info(f"📝 Пользователь @{message.from_user.username} (ID: {message.from_user.id}) использовал /start")
    await message.answer(
        "🤖 Привет! Я бот для проверки подписки.\n\n"
        "Нажмите кнопку ниже, чтобы добавить меня в ваш канал:",
        reply_markup=get_start_keyboard()
    )

@dp.callback_query(F.data.startswith("unmute_"))
async def unmute_callback(callback: types.CallbackQuery):
    """Обработчик кнопки снятия мута"""
    user_id = int(callback.data.split("_")[1])
    admin_id = callback.from_user.id
    
    logger.info(f"🔓 Админ @{callback.from_user.username} (ID: {admin_id}) пытается снять мут с пользователя ID: {user_id}")
    
    try:
        # Проверяем, является ли нажавший администратором
        chat_member = await bot.get_chat_member(callback.message.chat.id, admin_id)
        
        if chat_member.status in ("creator", "administrator"):
            # Снимаем мут
            await bot.restrict_chat_member(
                chat_id=callback.message.chat.id,
                user_id=user_id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            
            await callback.answer("✅ Мут снят!", show_alert=True)
            await callback.message.edit_text(
                callback.message.text + "\n\n✅ Мут снят",
                reply_markup=None
            )
            logger.info(f"✅ Мут снят с пользователя ID: {user_id}")
        else:
            await callback.answer("❌ Только администраторы могут снимать мут!", show_alert=True)
            
    except Exception as e:
        logger.error(f"❌ Ошибка при снятии мута: {e}")
        await callback.answer("❌ Ошибка при снятии мута", show_alert=True)

@dp.message(F.chat.id == CHAT_ID)
async def handle_message(message: types.Message):
    """Основной обработчик сообщений в чате"""
    
    # Пропускаем сообщения от каналов и Telegram
    if message.sender_chat or message.from_user.is_bot and message.from_user.username == 'Telegram':
        logger.info(f"⏭️ Пропускаем сообщение от канала/Telegram")
        return
    
    user_id = message.from_user.id
    username = message.from_user.username or "без username"
    user_fullname = message.from_user.full_name
    
    logger.info(f"📨 Сообщение от @{username} ({user_fullname}, ID: {user_id})")
    
    # Проверка 3: Удаление сообщений от Iris о модерации
    if is_iris_message(message) and message.text and is_iris_moderation_message(message.text):
        try:
            await message.delete()
            logger.info(f"🗑️ Удалено сообщение от Iris о модерации: {message.text[:100]}")
            return
        except Exception as e:
            logger.error(f"❌ Ошибка при удалении сообщения от Iris: {e}")
    
    # Проверка 2: Сообщения со ссылками
    if message.text and contains_url(message.text):
        logger.warning(f"🔗 Обнаружена ссылка от @{username} (ID: {user_id})")
        await handle_link_violation(message, username, user_fullname, user_id)
        return
    
    # Проверка 1: Проверка подписки на канал
    await check_subscription_and_warn(message, username, user_fullname, user_id)

async def check_subscription_and_warn(message: types.Message, username: str, user_fullname: str, user_id: int):
    """Проверяет подписку и предупреждает, но НЕ удаляет сообщение"""
    try:
        # Проверяем подписку на канал
        member = await bot.get_chat_member(CHANNEL_ID, user_id)
        
        # Если пользователь не подписан (left или kicked)
        if member.status in ("left", "kicked"):
            logger.warning(f"❌ @{username} (ID: {user_id}) не подписан на канал. Статус: {member.status}")
            
            # Определяем как показывать пользователя
            if username != "без username":
                user_mention = f"@{username}"
            else:
                user_mention = user_fullname
            
            # Отправляем предупреждение, но НЕ удаляем сообщение
            await message.reply(
                f"{user_mention}, подпишитесь на Mory Blog чтобы продолжить общаться в чате",
                reply_markup=get_warning_keyboard()
            )
            logger.info(f"📢 Предупреждение о подписке отправлено для {user_mention} (ID: {user_id})")
        else:
            logger.info(f"✅ @{username} (ID: {user_id}) подписан на канал. Статус: {member.status}")
            
    except (TelegramForbiddenError, TelegramBadRequest) as e:
        logger.error(f"⚠️ Ошибка доступа для @{username} (ID: {user_id}): {e}")
        # Не удаляем сообщение при ошибке проверки
    except Exception as e:
        logger.error(f"💥 Неизвестная ошибка для @{username} (ID: {user_id}): {e}")
        # Не удаляем сообщение при неизвестной ошибке

async def handle_link_violation(message: types.Message, username: str, user_fullname: str, user_id: int):
    """Обрабатывает нарушение: ссылка в сообщении"""
    try:
        # Удаляем сообщение со ссылкой
        await message.delete()
        logger.info(f"🗑️ Сообщение со ссылкой от @{username} (ID: {user_id}) удалено")
        
        # Определяем как показывать пользователя
        if username != "без username":
            user_mention = f"@{username}"
        else:
            user_mention = user_fullname
        
        # Устанавливаем время мута на 3 часа
        until_date = datetime.now() + timedelta(hours=3)
        
        # Мутим пользователя на 3 часа
        await bot.restrict_chat_member(
            chat_id=message.chat.id,
            user_id=user_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False
            ),
            until_date=until_date,
            reason="ссылка"
        )
        
        logger.info(f"🔇 Пользователь @{username} (ID: {user_id}) замучен на 3 часа. Причина: ссылка")
        
        # Форматируем время окончания мута
        mute_end_time = until_date.strftime("%H:%M:%S")
        
        # Отправляем сообщение о муте с кнопкой снятия
        await message.answer(
            f"{user_mention} был замучен\n"
            f"⏰ До: {mute_end_time}\n"
            f"📝 Причина: ссылка",
            reply_markup=get_unmute_keyboard(user_id)
        )
        
    except Exception as e:
        logger.error(f"❌ Ошибка при обработке нарушения для @{username} (ID: {user_id}): {e}")

async def main():
    logger.info("=" * 50)
    logger.info("🤖 Бот запущен и готов к работе")
    logger.info(f"📢 Отслеживаем чат: {CHAT_ID}")
    logger.info(f"📢 Проверяем подписку на канал: {CHANNEL_ID}")
    logger.info(f"🤖 Бот: @{BOT_USERNAME}")
    logger.info("=" * 50)
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
