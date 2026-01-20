from aiogram import Router, Bot, F
from aiogram.types import Message, ReactionType, ReactionTypeEmoji
from aiogram.filters import Command

from config import settings
from database import db
from utils import format_user_info, format_stats

router = Router()


# Filter: only admin messages
router.message.filter(F.from_user.id == settings.admin_id)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    stats = await db.get_stats()
    await message.answer(format_stats(stats))


@router.message(Command("user"))
async def cmd_user(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /user <id>")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return

    user = await db.get_user(user_id)
    if not user:
        await message.answer("Пользователь не найден")
        return

    stats = await db.get_user_stats(user_id)
    await message.answer(format_user_info(user, stats))


@router.message(Command("block"))
async def cmd_block(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /block <id>")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return

    success = await db.block_user(user_id)
    if success:
        await message.answer(f"Пользователь {user_id} заблокирован")
    else:
        await message.answer("Пользователь не найден")


@router.message(Command("unblock"))
async def cmd_unblock(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /unblock <id>")
        return

    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("ID должен быть числом")
        return

    success = await db.unblock_user(user_id)
    if success:
        await message.answer(f"Пользователь {user_id} разблокирован")
    else:
        await message.answer("Пользователь не найден")


@router.message(Command("close"))
async def cmd_close(message: Message, bot: Bot):
    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя командой /close")
        return

    # Find ticket by replied message
    ticket = await db.get_ticket_by_admin_message(message.reply_to_message.message_id)
    if not ticket:
        await message.answer("Тикет не найден")
        return

    if ticket.status == "closed":
        await message.answer(f"Тикет #{ticket.id} уже закрыт")
        return

    await db.close_ticket(ticket.id)
    await message.answer(f"Тикет #{ticket.id} закрыт")

    # Notify user
    user = await db.get_user(ticket.user_id)
    if user:
        try:
            await bot.send_message(
                ticket.user_id,
                f"Ваше обращение #{ticket.id} закрыто. Напишите снова, если нужна помощь.",
            )
        except Exception:
            pass


@router.message(Command("quick"))
async def cmd_quick(message: Message):
    args = message.text.split(maxsplit=2)

    if len(args) == 1:
        replies = await db.get_quick_replies()
        if not replies:
            await message.answer("Быстрые ответы не настроены. Добавьте: /quick add <shortcut> <text>")
            return

        text = "📝 Быстрые ответы:\n\n"
        for reply in replies:
            text += f"• /{reply.shortcut} — {reply.text[:50]}{'...' if len(reply.text) > 50 else ''}\n"
        await message.answer(text)
        return

    # /quick add <shortcut> <text>
    if args[1] == "add":
        if len(args) < 3:
            await message.answer("Использование: /quick add <shortcut> <text>")
            return

        parts = args[2].split(maxsplit=1)
        if len(parts) < 2:
            await message.answer("Использование: /quick add <shortcut> <text>")
            return

        shortcut, text = parts
        await db.add_quick_reply(shortcut, text)
        await message.answer(f"Быстрый ответ '{shortcut}' сохранён")
        return

    # /quick del <shortcut>
    if args[1] == "del":
        if len(args) < 3:
            await message.answer("Использование: /quick del <shortcut>")
            return

        shortcut = args[2].split()[0]
        success = await db.delete_quick_reply(shortcut)
        if success:
            await message.answer(f"Быстрый ответ '{shortcut}' удалён")
        else:
            await message.answer(f"Быстрый ответ '{shortcut}' не найден")
        return

    await message.answer("Использование:\n/quick — список\n/quick add <shortcut> <text>\n/quick del <shortcut>")


@router.message(Command("q"))
async def cmd_q(message: Message, bot: Bot):
    if not message.reply_to_message:
        await message.answer("Ответьте на сообщение пользователя командой /q <shortcut>")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Использование: /q <shortcut>")
        return

    shortcut = args[1].strip()
    reply = await db.get_quick_reply(shortcut)
    if not reply:
        await message.answer(f"Быстрый ответ '{shortcut}' не найден")
        return

    # Find user by replied message
    msg = await db.get_message_by_admin_id(message.reply_to_message.message_id)
    if not msg:
        await message.answer("Сообщение не найдено в базе")
        return

    # Send quick reply to user
    try:
        sent = await bot.send_message(msg.user_id, reply.text)
        await message.answer(f"✅ Отправлено")

        # Save outgoing message
        ticket = await db.get_open_ticket(msg.user_id)
        if ticket:
            await db.save_message(
                ticket_id=ticket.id,
                user_id=msg.user_id,
                user_message_id=sent.message_id,
                admin_message_id=None,
                direction="outgoing",
            )
    except Exception as e:
        await message.answer(f"Ошибка отправки: {e}")


@router.message(F.reply_to_message)
async def handle_admin_reply(message: Message, bot: Bot):
    # Find the original message by admin_message_id
    original = await db.get_message_by_admin_id(message.reply_to_message.message_id)
    if not original:
        return

    user_id = original.user_id

    # Check if user is blocked
    user = await db.get_user(user_id)
    if not user:
        await message.answer("Пользователь не найден")
        return

    # Send reply to user
    try:
        if message.text:
            sent = await bot.send_message(user_id, message.text)
        elif message.photo:
            sent = await bot.send_photo(
                user_id,
                message.photo[-1].file_id,
                caption=message.caption,
            )
        elif message.document:
            sent = await bot.send_document(
                user_id,
                message.document.file_id,
                caption=message.caption,
            )
        elif message.voice:
            sent = await bot.send_voice(user_id, message.voice.file_id)
        elif message.video:
            sent = await bot.send_video(
                user_id,
                message.video.file_id,
                caption=message.caption,
            )
        elif message.sticker:
            sent = await bot.send_sticker(user_id, message.sticker.file_id)
        elif message.animation:
            sent = await bot.send_animation(
                user_id,
                message.animation.file_id,
                caption=message.caption,
            )
        else:
            await message.answer("Этот тип сообщения не поддерживается")
            return

        # Save outgoing message
        ticket = await db.get_open_ticket(user_id)
        if ticket:
            await db.save_message(
                ticket_id=ticket.id,
                user_id=user_id,
                user_message_id=sent.message_id,
                admin_message_id=None,
                direction="outgoing",
            )

        await message.react(reaction=[ReactionTypeEmoji(emoji="🕊")])

    except Exception as e:
        await message.answer(f"Ошибка отправки: {e}")
