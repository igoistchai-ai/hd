import os
import secrets
import sqlite3
import string
from datetime import datetime, timezone

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

DB_PATH = os.getenv("DB_PATH", "bot.db")
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = os.getenv("ADMIN_ID", "").strip()

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("""CREATE TABLE IF NOT EXISTS keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id INTEGER NOT NULL,
        username TEXT,
        access_key TEXT UNIQUE NOT NULL,
        robux INTEGER DEFAULT 0,
        nickname TEXT DEFAULT 'Player',
        created_at TEXT NOT NULL,
        active INTEGER DEFAULT 1
    )""")
    conn.commit()
    return conn

def admin(update):
    return ADMIN_ID and str(update.effective_user.id) == ADMIN_ID

def make_key():
    a = string.ascii_uppercase + string.digits
    return "CC-" + "-".join("".join(secrets.choice(a) for _ in range(7)) for _ in range(3))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    row = db().execute("SELECT access_key,robux,nickname FROM keys WHERE telegram_id=? AND active=1 ORDER BY id DESC LIMIT 1",(update.effective_user.id,)).fetchone()
    if row:
        await update.message.reply_text(f"Hello!\\n\\nYour access key:\\n`{row['access_key']}`\\n\\nProfile: {row['nickname']}\\nBalance: {row['robux']:,} Robux",parse_mode="Markdown")
    else:
        await update.message.reply_text("Hello!\\n\\nYou don't have an access key yet. Ask the administrator to issue one.")

async def mykey(update, context):
    await start(update, context)

async def key_cmd(update, context):
    if not admin(update):
        await update.message.reply_text("Нет доступа.")
        return
    if len(context.args) < 1:
        await update.message.reply_text("/key TELEGRAM_ID [ROBUX] [NICKNAME]")
        return
    try: tid=int(context.args[0])
    except: await update.message.reply_text("Telegram ID должен быть числом."); return
    try: robux=max(0,int(context.args[1])) if len(context.args)>1 else 0
    except: await update.message.reply_text("Robux должен быть числом."); return
    nickname=" ".join(context.args[2:])[:32] if len(context.args)>2 else "Player"
    key=make_key()
    conn=db()
    conn.execute("UPDATE keys SET active=0 WHERE telegram_id=?",(tid,))
    conn.execute("INSERT INTO keys(telegram_id,username,access_key,robux,nickname,created_at,active) VALUES(?,?,?,?,?,?,1)",(tid,"",key,robux,nickname,datetime.now(timezone.utc).isoformat()))
    conn.commit(); conn.close()
    await update.message.reply_text(f"Ключ создан:\\n\\nID: `{tid}`\\nProfile: `{nickname}`\\nRobux: `{robux:,}`\\n\\nAccess key:\\n`{key}`",parse_mode="Markdown")
    try:
        await context.bot.send_message(tid,f"Hello!\\n\\nUr access key:\\n`{key}`\\n\\nProfile: {nickname}\\nBalance: {robux:,} Robux",parse_mode="Markdown")
    except:
        await update.message.reply_text("Ключ сохранён. Автоматическая отправка не удалась — пользователь должен сначала открыть бота и нажать Start.")

async def users_cmd(update, context):
    if not admin(update): await update.message.reply_text("Нет доступа."); return
    conn=db(); rows=conn.execute("SELECT telegram_id,access_key,robux,nickname FROM keys WHERE active=1 ORDER BY id DESC LIMIT 30").fetchall(); conn.close()
    if not rows: await update.message.reply_text("Активных ключей нет."); return
    await update.message.reply_text("\n\n".join([f"ID: {r['telegram_id']}\\nKey: {r['access_key']}\\nProfile: {r['nickname']}\\nRobux: {r['robux']:,}" for r in rows]))

async def revoke(update, context):
    if not admin(update): await update.message.reply_text("Нет доступа."); return
    if not context.args: await update.message.reply_text("/revoke TELEGRAM_ID"); return
    tid=int(context.args[0]); conn=db(); cur=conn.execute("UPDATE keys SET active=0 WHERE telegram_id=?",(tid,)); conn.commit(); conn.close()
    await update.message.reply_text("Ключ отключён." if cur.rowcount else "Ключ не найден.")

def run_bot():
    if not BOT_TOKEN:
        return
    db()
    app=Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start",start))
    app.add_handler(CommandHandler("mykey",mykey))
    app.add_handler(CommandHandler("key",key_cmd))
    app.add_handler(CommandHandler("users",users_cmd))
    app.add_handler(CommandHandler("revoke",revoke))
    print("Telegram bot started.",flush=True)
    app.run_polling(drop_pending_updates=True)
