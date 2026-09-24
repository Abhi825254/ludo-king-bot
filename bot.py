import os
import threading
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7194958748"))

PRICE = "₹49"

# Content file IDs
PREVIEW_VIDEO = None
PAID_VIDEO = None
PAID_FILE_1 = None
PAID_FILE_2 = None
QR_FILE_ID = None

# Temporary payment information
payments = {}


# ---------------- HEALTH SERVER ----------------

app = Flask(__name__)

@app.route("/")
def home():
    return "Ludo King Bot is running!"


def run_server():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


# ---------------- START ----------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    keyboard = [
        [
            InlineKeyboardButton(
                "💳 GET FULL ACCESS ₹49",
                callback_data="buy"
            )
        ],
        [
            InlineKeyboardButton(
                "❌ I DON'T NEED THIS NOW",
                callback_data="cancel"
            )
        ]
    ]

    text = (
        "🎮 Welcome!\n\n"
        "👇 Pehle 30-second preview dekho.\n"
        "Full access price: ₹49"
    )

    if PREVIEW_VIDEO:
        await update.message.reply_video(
            video=PREVIEW_VIDEO,
            caption=text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.message.reply_text(
            "⚠️ Preview video abhi set nahi hai.\n\n" + text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ---------------- BUY ----------------

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ PAYMENT DONE",
                callback_data="payment_done"
            )
        ],
        [
            InlineKeyboardButton(
                "🆘 HELP",
                callback_data="help"
            )
        ]
    ]

    caption = (
        "💳 FULL ACCESS\n\n"
        "💰 Price: ₹49\n\n"
        "1️⃣ QR code scan karo\n"
        "2️⃣ ₹49 payment karo\n"
        "3️⃣ Payment ke baad PAYMENT DONE dabao\n"
        "4️⃣ Screenshot + UTR submit karo\n\n"
        "⏳ Payment manually verify ki jayegi."
    )

    if QR_FILE_ID:
        await query.message.reply_photo(
            photo=QR_FILE_ID,
            caption=caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await query.message.reply_text(
            "⚠️ QR abhi set nahi hai.\n\n" + caption,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


# ---------------- HELP ----------------

async def help_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    await query.message.reply_text(
        "🆘 HELP\n\n"
        "Payment ya access se related problem ho to admin ko Telegram par message kare."
    )


# ---------------- PAYMENT DONE ----------------

async def payment_done(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    payments[query.from_user.id] = {
        "screenshot": None,
        "utr": None
    }

    context.user_data["payment_step"] = "screenshot"

    await query.message.reply_text(
        "📸 PAYMENT SCREENSHOT BHEJO\n\n"
        "Payment complete hone ka screenshot yahan upload karo."
    )


# ---------------- PHOTO ----------------

async def receive_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("payment_step") != "screenshot":
        return

    user_id = update.effective_user.id

    photo = update.message.photo[-1]
    payments.setdefault(user_id, {})
    payments[user_id]["screenshot"] = photo.file_id

    context.user_data["payment_step"] = "utr"

    await update.message.reply_text(
        "✅ Screenshot received.\n\n"
        "Ab apna **UTR / Transaction ID** bhejo."
    )


# ---------------- UTR ----------------

async def receive_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get("payment_step") != "utr":
        return

    user_id = update.effective_user.id
    utr = update.message.text.strip()

    payments.setdefault(user_id, {})
    payments[user_id]["utr"] = utr

    context.user_data["payment_step"] = "waiting"

    user = update.effective_user

    keyboard = [
        [
            InlineKeyboardButton(
                "✅ APPROVE",
                callback_data=f"approve_{user_id}"
            ),
            InlineKeyboardButton(
                "❌ REJECT",
                callback_data=f"reject_{user_id}"
            )
        ]
    ]

    admin_text = (
        "💰 NEW PAYMENT REQUEST\n\n"
        f"👤 Name: {user.full_name}\n"
        f"🆔 User ID: {user_id}\n"
        f"🔗 Username: @{user.username if user.username else 'N/A'}\n"
        f"💵 Amount: {PRICE}\n"
        f"🔢 UTR: {utr}"
    )

    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    screenshot = payments[user_id].get("screenshot")

    if screenshot:
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=screenshot,
            caption=f"📸 Payment Screenshot\nUser ID: {user_id}"
        )

    await update.message.reply_text(
        "⏳ PAYMENT SUBMITTED\n\n"
        "Aapka payment request admin ke paas chala gaya hai.\n"
        "Manual verification ke baad full content automatically milega."
    )


# ---------------- APPROVE / REJECT ----------------

async def admin_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    if query.from_user.id != ADMIN_ID:
        await query.answer("Not authorized.", show_alert=True)
        return

    await query.answer()

    data = query.data

    if data.startswith("approve_"):
        user_id = int(data.split("_")[1])

        if not PAID_VIDEO or not PAID_FILE_1 or not PAID_FILE_2:
            await query.message.reply_text(
                "⚠️ Paid content abhi set nahi hai."
            )
            return

        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=(
                    "🎉 PAYMENT APPROVED!\n\n"
                    "✅ Full access unlocked.\n"
                    "👇 Aapka paid content:"
                )
            )

            await context.bot.send_video(
                chat_id=user_id,
                video=PAID_VIDEO,
                caption="🎬 Paid Video"
            )

            await context.bot.send_document(
                chat_id=user_id,
                document=PAID_FILE_1,
                caption="📁 File 1"
            )

            await context.bot.send_document(
                chat_id=user_id,
                document=PAID_FILE_2,
                caption="📁 File 2"
            )

            await query.message.edit_text(
                query.message.text + "\n\n✅ APPROVED & CONTENT SENT"
            )

        except Exception as e:
            await query.message.reply_text(
                f"⚠️ Delivery error: {e}"
            )

    elif data.startswith("reject_"):
        user_id = int(data.split("_")[1])

        await context.bot.send_message(
            chat_id=user_id,
            text=(
                "❌ PAYMENT REJECTED\n\n"
                "Payment verify nahi ho paya.\n"
                "Agar aapko lagta hai payment successful hai, HELP se contact kare."
            )
        )

        await query.message.edit_text(
            query.message.text + "\n\n❌ REJECTED"
        )


# ---------------- ADMIN CONTENT SETUP ----------------

async def set_preview(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PREVIEW_VIDEO

    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.reply_to_message and update.message.reply_to_message.video:
        PREVIEW_VIDEO = update.message.reply_to_message.video.file_id
        await update.message.reply_text("✅ Preview video saved!")
    else:
        await update.message.reply_text(
            "Pehle video bhejo, phir us video ko reply karke /setpreview bhejo."
        )


async def set_paid_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PAID_VIDEO

    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.reply_to_message and update.message.reply_to_message.video:
        PAID_VIDEO = update.message.reply_to_message.video.file_id
        await update.message.reply_text("✅ Paid video saved!")
    else:
        await update.message.reply_text(
            "Paid video ko reply karke /setpaidvideo bhejo."
        )


async def set_file1(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PAID_FILE_1

    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.reply_to_message and update.message.reply_to_message.document:
        PAID_FILE_1 = update.message.reply_to_message.document.file_id
        await update.message.reply_text("✅ File 1 saved!")
    else:
        await update.message.reply_text(
            "File 1 ko reply karke /setfile1 bhejo."
        )


async def set_file2(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global PAID_FILE_2

    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.reply_to_message and update.message.reply_to_message.document:
        PAID_FILE_2 = update.message.reply_to_message.document.file_id
        await update.message.reply_text("✅ File 2 saved!")
    else:
        await update.message.reply_text(
            "File 2 ko reply karke /setfile2 bhejo."
        )


async def set_qr(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global QR_FILE_ID

    if update.effective_user.id != ADMIN_ID:
        return

    if update.message.reply_to_message and update.message.reply_to_message.photo:
        QR_FILE_ID = update.message.reply_to_message.photo[-1].file_id
        await update.message.reply_text("✅ QR saved!")
    else:
        await update.message.reply_text(
            "QR photo ko reply karke /setqr bhejo."
        )


# ---------------- MAIN ----------------

def main():
    if not BOT_TOKEN:
        raise ValueError("BOT_TOKEN environment variable missing")

    threading.Thread(target=run_server, daemon=True).start()

    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))

    application.add_handler(
        CallbackQueryHandler(buy, pattern="^buy$")
    )

    application.add_handler(
        CallbackQueryHandler(payment_done, pattern="^payment_done$")
    )

    application.add_handler(
        CallbackQueryHandler(help_button, pattern="^help$")
    )

    application.add_handler(
        CallbackQueryHandler(admin_action, pattern="^(approve|reject)_")
    )

    application.add_handler(
        CommandHandler("setpreview", set_preview)
    )

    application.add_handler(
        CommandHandler("setpaidvideo", set_paid_video)
    )

    application.add_handler(
        CommandHandler("setfile1", set_file1)
    )

    application.add_handler(
        CommandHandler("setfile2", set_file2)
    )

    application.add_handler(
        CommandHandler("setqr", set_qr)
    )

    application.add_handler(
        MessageHandler(filters.PHOTO, receive_photo)
    )

    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, receive_text)
    )

    print("Bot started...")
    application.run_polling()


if __name__ == "__main__":
    main()
