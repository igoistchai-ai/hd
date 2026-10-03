import os
import sqlite3
import secrets
import string
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()
DB_PATH = os.getenv("DB_PATH", "bot.db")


def get_db():
    conn = sqlite3.connect(DB_PATH, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL,
            username TEXT DEFAULT '',
            access_key TEXT UNIQUE NOT NULL,
            robux INTEGER NOT NULL DEFAULT 0,
            nickname TEXT NOT NULL DEFAULT 'Player',
            created_at TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1
        )
    """)
    conn.commit()
    return conn


def remember_user(update: Update):
    user = update.effective_user
    conn = get_db()
    conn.execute(
        """
        INSERT INTO users (telegram_id, username)
        VALUES (?, ?)
        ON CONFLICT(telegram_id)
        DO UPDATE SET username = excluded.username
        """,
        (user.id, (user.username or "").lower().lstrip("@")),
    )
    conn.commit()
    conn.close()


def admin(update: Update):
    return bool(ADMIN_ID) and str(update.effective_user.id) == ADMIN_ID


def make_key():
    alphabet = string.ascii_uppercase + string.digits
    return "CC-" + "-".join(
        "".join(secrets.choice(alphabet) for _ in range(7))
        for _ in range(3)
    )


def find_user(value):
    value = value.strip().lstrip("@").lower()
    conn = get_db()

    if value.isdigit():
        row = conn.execute(
            "SELECT telegram_id, username FROM users WHERE telegram_id=?",
            (int(value),),
        ).fetchone()
        conn.close()
        return dict(row) if row else {
            "telegram_id": int(value),
            "username": ""
        }

    row = conn.execute(
        "SELECT telegram_id, username FROM users "
        "WHERE lower(username)=? LIMIT 1",
        (value,),
    ).fetchone()

    if not row:
        row = conn.execute(
            "SELECT telegram_id, username FROM keys "
            "WHERE lower(username)=? ORDER BY id DESC LIMIT 1",
            (value,),
        ).fetchone()

    conn.close()
    return dict(row) if row else None


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remember_user(update)

    conn = get_db()
    row = conn.execute(
        """
        SELECT access_key, nickname, robux
        FROM keys
        WHERE telegram_id=? AND active=1
        ORDER BY id DESC
        LIMIT 1
        """,
        (update.effective_user.id,),
    ).fetchone()
    conn.close()

    if not row:
        await update.message.reply_text(
            "Hello!\n\n"
            "Ur access key is not assigned yet.\n"
            "Ask the administrator for a key."
        )
        return

    await update.message.reply_text(
        "Hello!\n\n"
        "Ur access key:\n"
        f"`{row['access_key']}`\n\n"
        f"Profile: {row['nickname']}\n"
        f"Balance: {row['robux']:,} Robux",
        parse_mode="Markdown",
    )


async def mykey(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    remember_user(update)
    user = update.effective_user
    await update.message.reply_text(
        f"Telegram ID: `{user.id}`\n"
        f"Username: `@{user.username or 'none'}`",
        parse_mode="Markdown",
    )


async def create_key(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin(update):
        await update.message.reply_text("Нет доступа.")
        return

    if not context.args:
        await update.message.reply_text(
            "Использование:\n"
            "/key @username 31000 nickname\n\n"
            "Или:\n"
            "/key TELEGRAM_ID 31000 nickname"
        )
        return

    target = find_user(context.args[0])
    if not target:
        await update.message.reply_text(
            "Пользователь не найден.\n"
            "Пусть пользователь сначала нажмёт /start."
        )
        return

    try:
        robux = int(context.args[1]) if len(context.args) > 1 else 0
        if robux < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "Количество Robux должно быть положительным числом."
        )
        return

    nickname = (
        " ".join(context.args[2:]).strip()[:32]
        if len(context.args) > 2
        else "Player"
    )

    key = make_key()

    conn = get_db()

    conn.execute(
        "UPDATE keys SET active=0 WHERE telegram_id=?",
        (int(target["telegram_id"]),),
    )

    conn.execute(
        """
        INSERT INTO keys (
            telegram_id,
            username,
            access_key,
            robux,
            nickname,
            created_at,
            active
        )
        VALUES (?, ?, ?, ?, ?, ?, 1)
        """,
        (
            int(target["telegram_id"]),
            target.get("username", ""),
            key,
            robux,
            nickname,
            datetime.now(timezone.utc).isoformat(),
        ),
    )

    conn.commit()
    conn.close()

    await update.message.reply_text(
        "Ключ создан.\n\n"
        f"ID: `{target['telegram_id']}`\n"
        f"Profile: `{nickname}`\n"
        f"Robux: `{robux:,}`\n\n"
        "Access key:\n"
        f"`{key}`",
        parse_mode="Markdown",
    )

    try:
        await context.bot.send_message(
            chat_id=int(target["telegram_id"]),
            text=(
                "Hello!\n\n"
                "Ur access key:\n"
                f"`{key}`\n\n"
                f"Profile: {nickname}\n"
                f"Balance: {robux:,} Robux"
            ),
            parse_mode="Markdown",
        )
    except Exception as exc:
        print(f"DM error: {exc}", flush=True)


async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin(update):
        await update.message.reply_text("Нет доступа.")
        return

    conn = get_db()
    rows = conn.execute(
        """
        SELECT telegram_id, username, access_key, robux, nickname
        FROM keys
        WHERE active=1
        ORDER BY id DESC
        LIMIT 30
        """
    ).fetchall()
    conn.close()

    if not rows:
        await update.message.reply_text("Активных ключей нет.")
        return

    result = []
    for row in rows:
        result.append(
            f"ID: {row['telegram_id']}\n"
            f"@{row['username'] or 'unknown'}\n"
            f"{row['nickname']} • {row['robux']:,} Robux\n"
            f"{row['access_key']}"
        )

    await update.message.reply_text("\n\n".join(result))


async def revoke(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not admin(update):
        await update.message.reply_text("Нет доступа.")
        return

    if not context.args:
        await update.message.reply_text("/revoke @username")
        return

    target = find_user(context.args[0])
    if not target:
        await update.message.reply_text("Пользователь не найден.")
        return

    conn = get_db()
    cur = conn.execute(
        "UPDATE keys SET active=0 WHERE telegram_id=?",
        (int(target["telegram_id"]),),
    )
    conn.commit()
    conn.close()

    await update.message.reply_text(
        "Ключ отключён." if cur.rowcount else "Активный ключ не найден."
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is not set")

    get_db().close()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mykey", mykey))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("key", create_key))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("revoke", revoke))

    print("Telegram bot started.", flush=True)

    # Do NOT put this inside threading.Thread().
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
