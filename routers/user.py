from aiogram import Router, Bot, F
from aiogram.types import Message
from aiogram.filters import Command

from config import settings
from database import db
from models import User
from utils import format_user_card

router = Router()

WELCOME_MESSAGE = """👋 Добро пожаловать в поддержку BOVPN!

Опишите вашу проблему или задайте вопрос — мы ответим как можно скорее.

Вы можете отправлять:
• Текстовые сообщения
• Фото и скриншоты
• Документы и файлы
• Голосовые сообщения"""


@router.message(Command("start"), F.from_user.id != settings.admin_id)
async def cmd_start(message: Message):
    await message.answer(WELCOME_MESSAGE)


async def forward_to_admin(message: Message, bot: Bot, db_user: User):
    if db_user.is_blocked:
        await message.answer("Вы заблокированы в поддержке.")
        return

    ticket = await db.get_or_create_ticket(db_user.id)
    stats = await db.get_user_stats(db_user.id)

    info_card = format_user_card(db_user, ticket, stats)

    await bot.send_message(settings.admin_id, info_card)

    forwarded = await message.forward(settings.admin_id)

    await db.save_message(
        ticket_id=ticket.id,
        user_id=db_user.id,
        user_message_id=message.message_id,
        admin_message_id=forwarded.message_id,
        direction="incoming",
    )


@router.message(F.from_user.id != settings.admin_id, F.text)
async def handle_user_text(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)


@router.message(F.from_user.id != settings.admin_id, F.photo)
async def handle_user_photo(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)


@router.message(F.from_user.id != settings.admin_id, F.document)
async def handle_user_document(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)


@router.message(F.from_user.id != settings.admin_id, F.voice)
async def handle_user_voice(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)


@router.message(F.from_user.id != settings.admin_id, F.video)
async def handle_user_video(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)


@router.message(F.from_user.id != settings.admin_id, F.video_note)
async def handle_user_video_note(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)


@router.message(F.from_user.id != settings.admin_id, F.sticker)
async def handle_user_sticker(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)


@router.message(F.from_user.id != settings.admin_id, F.animation)
async def handle_user_animation(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)


@router.message(F.from_user.id != settings.admin_id, F.location)
async def handle_user_location(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)


@router.message(F.from_user.id != settings.admin_id, F.contact)
async def handle_user_contact(message: Message, bot: Bot, db_user: User):
    await forward_to_admin(message, bot, db_user)
