import asyncpg
from datetime import datetime, timedelta

from config import settings
from models import User, Ticket, Message, QuickReply, UserStats, Stats


class Database:
    def __init__(self):
        self.pool: asyncpg.Pool | None = None

    async def connect(self):
        self.pool = await asyncpg.create_pool(
            host=settings.db_host,
            port=settings.db_port,
            user=settings.db_user,
            password=settings.db_password,
            database=settings.db_name,
            min_size=2,
            max_size=10,
        )

    async def disconnect(self):
        if self.pool:
            await self.pool.close()

    async def init_tables(self):
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id BIGINT PRIMARY KEY,
                    username VARCHAR(255),
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    is_blocked BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT NOW(),
                    last_message_at TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS tickets (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT REFERENCES users(id),
                    status VARCHAR(20) DEFAULT 'open',
                    created_at TIMESTAMP DEFAULT NOW(),
                    closed_at TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS messages (
                    id SERIAL PRIMARY KEY,
                    ticket_id INT REFERENCES tickets(id),
                    user_id BIGINT REFERENCES users(id),
                    user_message_id BIGINT,
                    admin_message_id BIGINT,
                    direction VARCHAR(10),
                    created_at TIMESTAMP DEFAULT NOW()
                );

                CREATE TABLE IF NOT EXISTS quick_replies (
                    id SERIAL PRIMARY KEY,
                    shortcut VARCHAR(50) UNIQUE,
                    text TEXT
                );

                CREATE INDEX IF NOT EXISTS idx_messages_admin_message_id ON messages(admin_message_id);
                CREATE INDEX IF NOT EXISTS idx_messages_ticket_id ON messages(ticket_id);
                CREATE INDEX IF NOT EXISTS idx_tickets_user_id ON tickets(user_id);
            """)

    # User operations
    async def get_user(self, user_id: int) -> User | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM users WHERE id = $1", user_id
            )
            return User(**dict(row)) if row else None

    async def upsert_user(
        self,
        user_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO users (id, username, first_name, last_name, last_message_at)
                VALUES ($1, $2, $3, $4, NOW())
                ON CONFLICT (id) DO UPDATE SET
                    username = EXCLUDED.username,
                    first_name = EXCLUDED.first_name,
                    last_name = EXCLUDED.last_name,
                    last_message_at = NOW()
                RETURNING *
                """,
                user_id,
                username,
                first_name,
                last_name,
            )
            return User(**dict(row))

    async def block_user(self, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET is_blocked = TRUE WHERE id = $1", user_id
            )
            return result == "UPDATE 1"

    async def unblock_user(self, user_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE users SET is_blocked = FALSE WHERE id = $1", user_id
            )
            return result == "UPDATE 1"

    async def get_user_stats(self, user_id: int) -> UserStats:
        async with self.pool.acquire() as conn:
            message_count = await conn.fetchval(
                "SELECT COUNT(*) FROM messages WHERE user_id = $1", user_id
            )
            ticket_count = await conn.fetchval(
                "SELECT COUNT(*) FROM tickets WHERE user_id = $1", user_id
            )
            return UserStats(
                message_count=message_count or 0,
                ticket_count=ticket_count or 0,
            )

    # Ticket operations
    async def get_open_ticket(self, user_id: int) -> Ticket | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM tickets WHERE user_id = $1 AND status = 'open' ORDER BY created_at DESC LIMIT 1",
                user_id,
            )
            return Ticket(**dict(row)) if row else None

    async def create_ticket(self, user_id: int) -> Ticket:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "INSERT INTO tickets (user_id) VALUES ($1) RETURNING *", user_id
            )
            return Ticket(**dict(row))

    async def close_ticket(self, ticket_id: int) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "UPDATE tickets SET status = 'closed', closed_at = NOW() WHERE id = $1",
                ticket_id,
            )
            return result == "UPDATE 1"

    async def get_or_create_ticket(self, user_id: int) -> Ticket:
        ticket = await self.get_open_ticket(user_id)
        if not ticket:
            ticket = await self.create_ticket(user_id)
        return ticket

    # Message operations
    async def save_message(
        self,
        ticket_id: int,
        user_id: int,
        user_message_id: int | None,
        admin_message_id: int | None,
        direction: str,
    ) -> Message:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO messages (ticket_id, user_id, user_message_id, admin_message_id, direction)
                VALUES ($1, $2, $3, $4, $5)
                RETURNING *
                """,
                ticket_id,
                user_id,
                user_message_id,
                admin_message_id,
                direction,
            )
            return Message(**dict(row))

    async def get_message_by_admin_id(self, admin_message_id: int) -> Message | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM messages WHERE admin_message_id = $1", admin_message_id
            )
            return Message(**dict(row)) if row else None

    async def get_ticket_by_admin_message(self, admin_message_id: int) -> Ticket | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT t.* FROM tickets t
                JOIN messages m ON m.ticket_id = t.id
                WHERE m.admin_message_id = $1
                """,
                admin_message_id,
            )
            return Ticket(**dict(row)) if row else None

    # Quick replies
    async def get_quick_replies(self) -> list[QuickReply]:
        async with self.pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM quick_replies ORDER BY shortcut")
            return [QuickReply(**dict(row)) for row in rows]

    async def get_quick_reply(self, shortcut: str) -> QuickReply | None:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM quick_replies WHERE shortcut = $1", shortcut
            )
            return QuickReply(**dict(row)) if row else None

    async def add_quick_reply(self, shortcut: str, text: str) -> QuickReply:
        async with self.pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                INSERT INTO quick_replies (shortcut, text)
                VALUES ($1, $2)
                ON CONFLICT (shortcut) DO UPDATE SET text = EXCLUDED.text
                RETURNING *
                """,
                shortcut,
                text,
            )
            return QuickReply(**dict(row))

    async def delete_quick_reply(self, shortcut: str) -> bool:
        async with self.pool.acquire() as conn:
            result = await conn.execute(
                "DELETE FROM quick_replies WHERE shortcut = $1", shortcut
            )
            return result == "DELETE 1"

    # Statistics
    async def get_stats(self) -> Stats:
        async with self.pool.acquire() as conn:
            total_users = await conn.fetchval("SELECT COUNT(*) FROM users")

            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            active_today = await conn.fetchval(
                "SELECT COUNT(*) FROM users WHERE last_message_at >= $1", today
            )

            open_tickets = await conn.fetchval(
                "SELECT COUNT(*) FROM tickets WHERE status = 'open'"
            )
            closed_tickets = await conn.fetchval(
                "SELECT COUNT(*) FROM tickets WHERE status = 'closed'"
            )

            # Average response time (time between incoming and outgoing messages)
            avg_response = await conn.fetchval(
                """
                SELECT AVG(EXTRACT(EPOCH FROM (outgoing.created_at - incoming.created_at)) / 60)
                FROM messages incoming
                JOIN messages outgoing ON incoming.ticket_id = outgoing.ticket_id
                    AND outgoing.direction = 'outgoing'
                    AND outgoing.created_at > incoming.created_at
                WHERE incoming.direction = 'incoming'
                    AND incoming.created_at >= NOW() - INTERVAL '7 days'
                """
            )

            # Messages per day for last 7 days
            rows = await conn.fetch(
                """
                SELECT DATE(created_at) as date, COUNT(*) as count
                FROM messages
                WHERE created_at >= NOW() - INTERVAL '7 days'
                GROUP BY DATE(created_at)
                ORDER BY date
                """
            )
            messages_last_7_days = [(str(row["date"]), row["count"]) for row in rows]

            return Stats(
                total_users=total_users or 0,
                active_today=active_today or 0,
                open_tickets=open_tickets or 0,
                closed_tickets=closed_tickets or 0,
                avg_response_time_minutes=round(avg_response, 1) if avg_response else None,
                messages_last_7_days=messages_last_7_days,
            )


db = Database()
