import os
import logging
from datetime import datetime
import asyncio
import schedule
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters, ConversationHandler
from dotenv import load_dotenv
import jdatetime

from directadmin_handler import DirectAdminHandler
from payment_handler import ZarinpalPayment, PaymentDatabase
from ticket_handler import TicketSystem
from admin_handler import AdminPanel, UserManager
from hosting_handler import HostingManager

# Load environment variables
load_dotenv()

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Initialize handlers
da_handler = DirectAdminHandler(
    url=os.getenv('DA_URL'),
    username=os.getenv('DA_USERNAME'),
    password=os.getenv('DA_PASSWORD')
)

payment_handler = ZarinpalPayment(
    merchant_id=os.getenv('ZARINPAL_MERCHANT_ID'),
    sandbox=os.getenv('ZARINPAL_SANDBOX', 'true').lower() == 'true'
)

payment_db = PaymentDatabase()
ticket_system = TicketSystem()
admin_panel = AdminPanel()
user_manager = UserManager()
hosting_manager = HostingManager(da_handler)

# Conversation states
WAITING_TICKET_SUBJECT, WAITING_TICKET_MESSAGE = range(2)
WAITING_DOMAIN, WAITING_EMAIL = range(2, 4)
WAITING_PAYMENT = 4
WAITING_DB_NAME, WAITING_DB_USER, WAITING_DB_PASS = range(5, 8)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a message when the command /start is issued."""
    user = update.effective_user
    user_manager.register_user(user.id, user.username, user.first_name, user.last_name)

    keyboard = [
        [InlineKeyboardButton("🌐 مشاهده پلن های هاستینگ", callback_data='show_plans')],
        [InlineKeyboardButton("📞 پشتیبانی", callback_data='support')],
        [InlineKeyboardButton("👤 پنل کاربری", callback_data='user_panel')],
    ]

    if admin_panel.is_admin(user.id):
        keyboard.append([InlineKeyboardButton("⚙️ پنل مدیریت", callback_data='admin_panel')])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'به ربات فروش هاستینگ خوش آمدید! 👋\n'
        'لطفاً یکی از گزینه های زیر را انتخاب کنید:',
        reply_markup=reply_markup
    )

async def button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    user_id = update.effective_user.id

    if query.data == 'show_plans':
        plans = admin_panel.get_plans()
        keyboard = []
        for plan_id, plan in plans.items():
            keyboard.append([InlineKeyboardButton(
                f"🌟 {plan['name']} - {plan['price']:,} تومان",
                callback_data=f'select_plan_{plan_id}'
            )])
        keyboard.append([InlineKeyboardButton("🏠 بازگشت به منو اصلی", callback_data='main_menu')])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        message = "📌 پلن های هاستینگ ما:\n\n"
        for plan_id, plan in plans.items():
            message += f"🔹 {plan['name']}:\n"
            message += f"💾 فضا: {plan['quota']//1024}GB\n"
            message += f"🌐 پهنای باند: {plan['bandwidth']//1024}GB\n"
            message += f"💰 قیمت: {plan['price']:,} تومان\n\n"
        
        await query.edit_message_text(text=message, reply_markup=reply_markup)

    elif query.data.startswith('select_plan_'):
        plan_id = query.data.replace('select_plan_', '')
        context.user_data['selected_plan'] = plan_id
        context.user_data['state'] = WAITING_DOMAIN
        
        await query.edit_message_text(
            "🌐 لطفاً دامنه خود را وارد کنید\n"
            "مثال: example.com"
        )

    elif query.data == 'support':
        keyboard = [
            [InlineKeyboardButton("📝 ایجاد تیکت جدید", callback_data='new_ticket')],
            [InlineKeyboardButton("📋 تیکت های من", callback_data='my_tickets')],
            [InlineKeyboardButton("🏠 بازگشت به منو اصلی", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "📮 سیستم پشتیبانی\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )

    elif query.data == 'new_ticket':
        context.user_data['state'] = WAITING_TICKET_SUBJECT
        await query.edit_message_text(
            "📝 لطفاً موضوع تیکت خود را وارد کنید:"
        )

    elif query.data == 'my_tickets':
        tickets = ticket_system.get_user_tickets(user_id)
        if not tickets:
            keyboard = [[InlineKeyboardButton("🏠 بازگشت به منو اصلی", callback_data='main_menu')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "شما هیچ تیکتی ندارید!",
                reply_markup=reply_markup
            )
            return

        message = "📋 تیکت‌های شما:\n\n"
        keyboard = []
        for ticket in tickets:
            status = "🟢" if ticket['status'] == 'open' else "🔴"
            message += f"{status} شماره تیکت: {ticket['ticket_id']}\n"
            message += f"📌 موضوع: {ticket['subject']}\n"
            message += f"📅 تاریخ: {jdatetime.datetime.fromtimestamp(ticket['created_at']).strftime('%Y/%m/%d %H:%M')}\n\n"
            keyboard.append([InlineKeyboardButton(
                f"مشاهده تیکت #{ticket['ticket_id']}",
                callback_data=f'view_ticket_{ticket["ticket_id"]}'
            )])
        
        keyboard.append([InlineKeyboardButton("🏠 بازگشت به منو اصلی", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data.startswith('view_ticket_'):
        ticket_id = int(query.data.replace('view_ticket_', ''))
        ticket = ticket_system.get_ticket(ticket_id)
        if not ticket:
            await query.edit_message_text("تیکت مورد نظر یافت نشد!")
            return

        message = f"🎫 تیکت #{ticket_id}\n"
        message += f"📌 موضوع: {ticket['subject']}\n"
        message += f"📅 تاریخ: {jdatetime.datetime.fromtimestamp(ticket['created_at']).strftime('%Y/%m/%d %H:%M')}\n"
        message += f"📊 وضعیت: {'باز' if ticket['status'] == 'open' else 'بسته'}\n\n"
        message += "💬 پیام‌ها:\n"
        
        for msg in ticket['messages']:
            sender = "👤 شما:" if not msg['is_admin'] else "👨‍💼 پشتیبان:"
            message += f"\n{sender}\n{msg['message']}\n"
            message += f"⏰ {jdatetime.datetime.fromtimestamp(msg['timestamp']).strftime('%Y/%m/%d %H:%M')}\n"

        keyboard = []
        if ticket['status'] == 'open':
            keyboard.append([InlineKeyboardButton("✍️ پاسخ به تیکت", callback_data=f'reply_ticket_{ticket_id}')])
            keyboard.append([InlineKeyboardButton("🔒 بستن تیکت", callback_data=f'close_ticket_{ticket_id}')])
        else:
            keyboard.append([InlineKeyboardButton("🔓 بازگشایی تیکت", callback_data=f'reopen_ticket_{ticket_id}')])
        
        keyboard.append([InlineKeyboardButton("🏠 بازگشت به منو اصلی", callback_data='main_menu')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data == 'user_panel':
        accounts = hosting_manager.get_user_accounts(user_id)
        message = "👤 پنل کاربری\n\n"
        
        if accounts:
            message += "🌐 هاست‌های شما:\n\n"
            for account in accounts:
                status_emoji = "🟢" if account['status'] == 'active' else "🔴"
                message += f"{status_emoji} {account['domain']}\n"
                message += f"👤 نام کاربری: {account['username']}\n"
                message += f"📦 پلن: {account['package']}\n"
                message += f"📅 تاریخ انقضا: {jdatetime.datetime.fromtimestamp(account['expiry_date']).strftime('%Y/%m/%d')}\n\n"

        keyboard = [
            [InlineKeyboardButton("💾 مدیریت دیتابیس‌ها", callback_data='manage_databases')],
            [InlineKeyboardButton("🔄 تمدید هاست", callback_data='renew_hosting')],
            [InlineKeyboardButton("📊 آمار مصرف", callback_data='resource_usage')],
            [InlineKeyboardButton("💾 بکاپ‌گیری", callback_data='create_backup')],
            [InlineKeyboardButton("🏠 بازگشت به منو اصلی", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data == 'admin_panel':
        if not admin_panel.is_admin(user_id):
            await query.edit_message_text("⛔️ شما دسترسی به پنل مدیریت ندارید!")
            return

        keyboard = [
            [InlineKeyboardButton("👥 مدیریت کاربران", callback_data='manage_users')],
            [InlineKeyboardButton("📦 مدیریت پلن‌ها", callback_data='manage_plans')],
            [InlineKeyboardButton("🎫 مدیریت تیکت‌ها", callback_data='manage_tickets')],
            [InlineKeyboardButton("⚙️ تنظیمات", callback_data='admin_settings')],
            [InlineKeyboardButton("🏠 بازگشت به منو اصلی", callback_data='main_menu')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "⚙️ پنل مدیریت\n"
            "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
            reply_markup=reply_markup
        )

async def admin_panel_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin panel actions."""
    query = update.callback_query
    user_id = update.effective_user.id

    if not admin_panel.is_admin(user_id):
        await query.edit_message_text("⛔️ شما دسترسی به پنل مدیریت ندارید!")
        return

    if query.data == 'manage_users':
        users = user_manager.get_all_users()
        message = "👥 لیست کاربران:\n\n"
        keyboard = []
        
        for uid, user in users.items():
            status = "🟢" if user.get('active', True) else "🔴"
            message += f"{status} {user['first_name']}"
            if user.get('username'):
                message += f" (@{user['username']})"
            message += f"\nتاریخ عضویت: {jdatetime.datetime.fromisoformat(user['registered_at']).strftime('%Y/%m/%d')}\n"
            message += f"تعداد هاست‌ها: {len(user.get('hosting_accounts', []))}\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"{'🔴 مسدود' if user.get('active', True) else '🟢 فعال'} کردن {user['first_name']}",
                callback_data=f"{'deactivate' if user.get('active', True) else 'activate'}_user_{uid}"
            )])

        keyboard.append([InlineKeyboardButton("📊 گزارش کاربران", callback_data='users_report')])
        keyboard.append([InlineKeyboardButton("⬅️ بازگشت", callback_data='admin_panel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data == 'manage_plans':
        plans = admin_panel.get_plans()
        message = "📦 پلن‌های هاستینگ:\n\n"
        keyboard = []
        
        for plan_id, plan in plans.items():
            message += f"🔹 {plan['name']}\n"
            message += f"💾 فضا: {plan['quota']//1024}GB\n"
            message += f"🌐 پهنای باند: {plan['bandwidth']//1024}GB\n"
            message += f"💰 قیمت: {plan['price']:,} تومان\n\n"
            
            keyboard.append([
                InlineKeyboardButton(f"✏️ ویرایش {plan['name']}", callback_data=f'edit_plan_{plan_id}'),
                InlineKeyboardButton(f"❌ حذف {plan['name']}", callback_data=f'delete_plan_{plan_id}')
            ])

        keyboard.append([InlineKeyboardButton("➕ افزودن پلن جدید", callback_data='add_plan')])
        keyboard.append([InlineKeyboardButton("⬅️ بازگشت", callback_data='admin_panel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data == 'manage_tickets':
        open_tickets = ticket_system.get_open_tickets()
        message = "🎫 تیکت‌های باز:\n\n"
        keyboard = []
        
        for ticket in open_tickets:
            user = user_manager.get_user(ticket['user_id'])
            message += f"🔹 تیکت #{ticket['ticket_id']}\n"
            message += f"👤 کاربر: {user['first_name']}"
            if user.get('username'):
                message += f" (@{user['username']})"
            message += f"\n📌 موضوع: {ticket['subject']}\n"
            message += f"⏰ تاریخ: {jdatetime.datetime.fromisoformat(ticket['created_at']).strftime('%Y/%m/%d %H:%M')}\n\n"
            
            keyboard.append([InlineKeyboardButton(
                f"پاسخ به تیکت #{ticket['ticket_id']}",
                callback_data=f'reply_admin_ticket_{ticket["ticket_id"]}'
            )])

        keyboard.append([InlineKeyboardButton("📊 گزارش تیکت‌ها", callback_data='tickets_report')])
        keyboard.append([InlineKeyboardButton("⬅️ بازگشت", callback_data='admin_panel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data == 'admin_settings':
        settings = admin_panel.get_settings()
        message = "⚙️ تنظیمات سیستم:\n\n"
        
        message += f"👥 ثبت‌نام: {'فعال' if settings['allow_registration'] else 'غیرفعال'}\n"
        message += f"🔧 حالت تعمیر: {'فعال' if settings['maintenance_mode'] else 'غیرفعال'}\n"
        message += f"💾 بکاپ خودکار: {'فعال' if settings['backup_enabled'] else 'غیرفعال'}\n"
        message += f"🔄 دوره بکاپ: {settings['backup_frequency']}\n"
        
        keyboard = [
            [InlineKeyboardButton(
                f"{'🔴 غیرفعال' if settings['allow_registration'] else '🟢 فعال'} کردن ثبت‌نام",
                callback_data='toggle_registration'
            )],
            [InlineKeyboardButton(
                f"{'🔴 غیرفعال' if settings['maintenance_mode'] else '🟢 فعال'} کردن حالت تعمیر",
                callback_data='toggle_maintenance'
            )],
            [InlineKeyboardButton(
                f"{'🔴 غیرفعال' if settings['backup_enabled'] else '🟢 فعال'} کردن بکاپ خودکار",
                callback_data='toggle_backup'
            )],
            [InlineKeyboardButton("🔄 تغییر دوره بکاپ", callback_data='change_backup_frequency')],
            [InlineKeyboardButton("⬅️ بازگشت", callback_data='admin_panel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data.startswith('deactivate_user_'):
        user_id = query.data.replace('deactivate_user_', '')
        user_manager.deactivate_user(user_id)
        # Suspend all user's hosting accounts
        accounts = hosting_manager.get_user_accounts(user_id)
        for account in accounts:
            hosting_manager.suspend_account(account['username'])
        await query.answer("✅ کاربر با موفقیت مسدود شد!")
        await admin_panel_handler(update, context)

    elif query.data.startswith('activate_user_'):
        user_id = query.data.replace('activate_user_', '')
        user_manager.activate_user(user_id)
        # Reactivate all user's hosting accounts
        accounts = hosting_manager.get_user_accounts(user_id)
        for account in accounts:
            hosting_manager.unsuspend_account(account['username'])
        await query.answer("✅ کاربر با موفقیت فعال شد!")
        await admin_panel_handler(update, context)

    elif query.data == 'users_report':
        users = user_manager.get_all_users()
        active_users = len(user_manager.get_active_users())
        total_accounts = sum(len(user.get('hosting_accounts', [])) for user in users.values())
        
        message = "📊 گزارش کاربران:\n\n"
        message += f"👥 کل کاربران: {len(users)}\n"
        message += f"🟢 کاربران فعال: {active_users}\n"
        message += f"🔴 کاربران غیرفعال: {len(users) - active_users}\n"
        message += f"🌐 کل هاست‌ها: {total_accounts}\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ بازگشت", callback_data='manage_users')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data == 'tickets_report':
        open_tickets = ticket_system.get_open_tickets()
        closed_tickets = ticket_system.get_closed_tickets()
        
        message = "📊 گزارش تیکت‌ها:\n\n"
        message += f"📬 کل تیکت‌ها: {len(open_tickets) + len(closed_tickets)}\n"
        message += f"📨 تیکت‌های باز: {len(open_tickets)}\n"
        message += f"📪 تیکت‌های بسته: {len(closed_tickets)}\n"
        
        keyboard = [[InlineKeyboardButton("⬅️ بازگشت", callback_data='manage_tickets')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(message, reply_markup=reply_markup)

    elif query.data.startswith('reply_admin_ticket_'):
        ticket_id = int(query.data.replace('reply_admin_ticket_', ''))
        context.user_data['replying_to_ticket'] = ticket_id
        await query.edit_message_text(
            "✍️ لطفاً پاسخ خود را وارد کنید:\n"
            "برای لغو، دستور /cancel را وارد کنید."
        )

    elif query.data.startswith('toggle_'):
        setting = query.data.replace('toggle_', '')
        current_settings = admin_panel.get_settings()
        
        if setting == 'registration':
            current_settings['allow_registration'] = not current_settings['allow_registration']
        elif setting == 'maintenance':
            current_settings['maintenance_mode'] = not current_settings['maintenance_mode']
        elif setting == 'backup':
            current_settings['backup_enabled'] = not current_settings['backup_enabled']
        
        admin_panel.update_settings(current_settings)
        await query.answer("✅ تنظیمات با موفقیت بروزرسانی شد!")
        await admin_panel_handler(update, context)

async def handle_admin_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle admin messages."""
    user_id = update.effective_user.id
    if not admin_panel.is_admin(user_id):
        return

    if 'replying_to_ticket' in context.user_data:
        ticket_id = context.user_data['replying_to_ticket']
        ticket_system.add_message(
            ticket_id=ticket_id,
            user_id=user_id,
            message=update.message.text,
            is_admin=True
        )
        
        # Send notification to ticket owner
        ticket = ticket_system.get_ticket(ticket_id)
        if ticket:
            try:
                await context.bot.send_message(
                    chat_id=ticket['user_id'],
                    text=f"📨 پاسخ جدید به تیکت #{ticket_id}:\n\n"
                         f"{update.message.text}\n\n"
                         "برای مشاهده کامل تیکت، به ربات مراجعه کنید."
                )
            except Exception as e:
                print(f"Error sending notification to user: {e}")

        keyboard = [[InlineKeyboardButton("⬅️ بازگشت به تیکت‌ها", callback_data='manage_tickets')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("✅ پاسخ شما با موفقیت ارسال شد!", reply_markup=reply_markup)
        del context.user_data['replying_to_ticket']

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all other messages."""
    user_id = update.effective_user.id
    message_text = update.message.text
    state = context.user_data.get('state')

    if state == WAITING_TICKET_SUBJECT:
        context.user_data['ticket_subject'] = message_text
        context.user_data['state'] = WAITING_TICKET_MESSAGE
        await update.message.reply_text(
            "📝 لطفاً متن تیکت خود را وارد کنید:"
        )

    elif state == WAITING_TICKET_MESSAGE:
        ticket = ticket_system.create_ticket(
            user_id=user_id,
            subject=context.user_data['ticket_subject'],
            message=message_text
        )
        
        # Send notification to support group
        if os.getenv('SUPPORT_GROUP_ID'):
            await context.bot.send_message(
                chat_id=os.getenv('SUPPORT_GROUP_ID'),
                text=f"🎫 تیکت جدید!\n"
                     f"شماره تیکت: {ticket['ticket_id']}\n"
                     f"کاربر: {update.effective_user.username or update.effective_user.first_name}\n"
                     f"موضوع: {ticket['subject']}\n"
                     f"پیام: {message_text}"
            )

        keyboard = [[InlineKeyboardButton("🏠 بازگشت به منو اصلی", callback_data='main_menu')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            f"✅ تیکت شما با موفقیت ثبت شد!\n"
            f"شماره تیکت: {ticket['ticket_id']}\n\n"
            f"پشتیبانان در اسرع وقت به تیکت شما پاسخ خواهند داد.",
            reply_markup=reply_markup
        )
        context.user_data.clear()

    elif state == WAITING_DOMAIN:
        if not message_text.strip():
            await update.message.reply_text("❌ لطفاً دامنه معتبر وارد کنید!")
            return

        context.user_data['domain'] = message_text
        context.user_data['state'] = WAITING_EMAIL
        await update.message.reply_text("📧 لطفاً آدرس ایمیل خود را وارد کنید:")

    elif state == WAITING_EMAIL:
        if not message_text.strip() or '@' not in message_text:
            await update.message.reply_text("❌ لطفاً ایمیل معتبر وارد کنید!")
            return

        plan = admin_panel.get_plans()[context.user_data['selected_plan']]
        payment_amount = plan['price']

        # Create payment request
        payment = payment_handler.request_payment(
            amount=payment_amount,
            description=f"خرید هاست {plan['name']}",
            callback_url=f"https://your-domain.com/verify?user_id={user_id}",
            email=message_text
        )

        if payment['status'] == 'success':
            payment_db.create_payment(
                user_id=user_id,
                amount=payment_amount,
                description=f"خرید هاست {plan['name']}",
                authority=payment['authority']
            )

            keyboard = [
                [InlineKeyboardButton("💳 پرداخت", url=payment['payment_url'])],
                [InlineKeyboardButton("🏠 بازگشت به منو اصلی", callback_data='main_menu')]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text(
                "🔄 در حال انتقال به درگاه پرداخت...\n"
                f"مبلغ قابل پرداخت: {payment_amount:,} تومان",
                reply_markup=reply_markup
            )
        else:
            await update.message.reply_text(
                "❌ خطا در ایجاد لینک پرداخت!\n"
                "لطفاً بعداً تلاش کنید یا با پشتیبانی تماس بگیرید."
            )
        
        context.user_data.clear()

async def admin_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /admin command."""
    user_id = update.effective_user.id
    
    if not admin_panel.is_admin(user_id):
        await update.message.reply_text("⛔️ شما دسترسی به پنل مدیریت ندارید!")
        return

    keyboard = [
        [InlineKeyboardButton("👥 مدیریت کاربران", callback_data='manage_users')],
        [InlineKeyboardButton("📦 مدیریت پلن‌ها", callback_data='manage_plans')],
        [InlineKeyboardButton("🎫 مدیریت تیکت‌ها", callback_data='manage_tickets')],
        [InlineKeyboardButton("⚙️ تنظیمات", callback_data='admin_settings')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎛 به پنل مدیریت خوش آمدید!\n"
        "لطفاً یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=reply_markup
    )

async def scheduled_tasks():
    """Run scheduled tasks."""
    while True:
        # Check for expired accounts
        accounts = hosting_manager.get_all_accounts()
        for account in accounts:
            if account['status'] == 'active':
                expiry_date = datetime.fromisoformat(account['expiry_date'])
                if expiry_date < datetime.now():
                    hosting_manager.suspend_account(account['username'])

        # Create automated backups
        if admin_panel.get_settings()['backup_enabled']:
            accounts = hosting_manager.get_active_accounts()
            for account in accounts:
                hosting_manager.create_backup(account['username'])

        # Clean up old backups
        retention_days = int(admin_panel.get_settings()['backup_retention_days'])
        hosting_manager.cleanup_old_backups(retention_days)

        await asyncio.sleep(86400)  # Run daily

def main():
    """Start the bot."""
    # Create the Application and pass it your bot's token.
    application = Application.builder().token(os.getenv('TELEGRAM_TOKEN')).build()

    # Add conversation handler
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler('start', start),
            CommandHandler('admin', admin_command),
        ],
        states={
            WAITING_TICKET_SUBJECT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            WAITING_TICKET_MESSAGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            WAITING_DOMAIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
            WAITING_EMAIL: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)],
        },
        fallbacks=[CommandHandler('cancel', start)]
    )

    # Add handlers
    application.add_handler(conv_handler)
    application.add_handler(CallbackQueryHandler(button))
    application.add_handler(CallbackQueryHandler(admin_panel_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_message))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start scheduled tasks
    asyncio.create_task(scheduled_tasks())

    # Start the Bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
