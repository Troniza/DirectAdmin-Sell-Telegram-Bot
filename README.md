# ربات تلگرام فروش هاست

این ربات برای فروش خودکار هاست از طریق تلگرام طراحی شده است و با DirectAdmin یکپارچه می‌شود.

## نصب و راه‌اندازی

1. ابتدا پکیج‌های مورد نیاز را نصب کنید:
```bash
pip install -r requirements.txt
```

2. فایل `.env.example` را به `.env` تغییر نام دهید و اطلاعات مورد نیاز را در آن وارد کنید:
- `TELEGRAM_TOKEN`: توکن ربات تلگرام خود را از @BotFather دریافت کنید
- `DA_URL`: آدرس پنل DirectAdmin
- `DA_USERNAME`: نام کاربری DirectAdmin
- `DA_PASSWORD`: رمز عبور DirectAdmin

3. ربات را اجرا کنید:
```bash
python bot.py
```

## قابلیت‌ها

- نمایش پلن‌های هاستینگ
- امکان خرید آنلاین
- پشتیبانی از طریق تلگرام
- مدیریت خودکار ایجاد هاست در DirectAdmin

## نکات امنیتی

- حتماً فایل `.env` را در `.gitignore` قرار دهید
- از رمزهای عبور قوی استفاده کنید
- دسترسی‌های DirectAdmin را محدود کنید
