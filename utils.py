from models import User, Ticket, UserStats


def format_user_card(user: User, ticket: Ticket, stats: UserStats) -> str:
    username_str = f"@{user.username}" if user.username else "нет"
    name_parts = [user.first_name or "", user.last_name or ""]
    full_name = " ".join(p for p in name_parts if p) or "Неизвестно"

    created_at_str = user.created_at.strftime("%Y-%m-%d") if user.created_at else "—"

    return (
        f"📨 Новое сообщение\n\n"
        f"👤 Имя: {full_name} ({username_str})\n"
        f"🆔 ID: {user.id}\n"
        f"📊 Сообщений: {stats.message_count} | Тикетов: {stats.ticket_count}\n"
        f"🕐 Первый контакт: {created_at_str}\n"
        f"📝 Тикет #{ticket.id} ({ticket.status})\n"
        f"───────────────────"
    )


def format_user_info(user: User, stats: UserStats) -> str:
    username_str = f"@{user.username}" if user.username else "нет"
    name_parts = [user.first_name or "", user.last_name or ""]
    full_name = " ".join(p for p in name_parts if p) or "Неизвестно"

    created_at_str = user.created_at.strftime("%Y-%m-%d %H:%M") if user.created_at else "—"
    last_message_str = user.last_message_at.strftime("%Y-%m-%d %H:%M") if user.last_message_at else "—"
    blocked_str = "🚫 Да" if user.is_blocked else "✅ Нет"

    return (
        f"👤 Информация о пользователе\n\n"
        f"🆔 ID: {user.id}\n"
        f"📛 Имя: {full_name}\n"
        f"🔗 Username: {username_str}\n"
        f"📊 Сообщений: {stats.message_count}\n"
        f"🎫 Тикетов: {stats.ticket_count}\n"
        f"🕐 Регистрация: {created_at_str}\n"
        f"💬 Последнее сообщение: {last_message_str}\n"
        f"🔒 Заблокирован: {blocked_str}"
    )


def format_stats(stats) -> str:
    avg_response = f"{stats.avg_response_time_minutes} мин" if stats.avg_response_time_minutes else "—"

    lines = [
        "📊 Статистика бота\n",
        f"👥 Всего пользователей: {stats.total_users}",
        f"🟢 Активных сегодня: {stats.active_today}",
        f"📬 Открытых тикетов: {stats.open_tickets}",
        f"✅ Закрытых тикетов: {stats.closed_tickets}",
        f"⏱ Среднее время ответа: {avg_response}",
    ]

    if stats.messages_last_7_days:
        lines.append("\n📈 Сообщений за последние 7 дней:")
        for date, count in stats.messages_last_7_days:
            bar = "█" * min(count // 5, 20)
            lines.append(f"  {date}: {bar} {count}")

    return "\n".join(lines)
