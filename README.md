# Repoiu
# Deploying the Telegram Deep Voice Bot to Render (free)

این مستند کوتاه نحوهٔ دیپلوی روی Render را توضیح می‌دهد.

1) آماده‌سازی مخزن
- فایل‌های پروژه (bot.py, requirements.txt, Dockerfile و فایل‌های دیگر) را به یک مخزن GitHub پوش کنید.

2) ساخت Dockerfile
- Dockerfile بالا تمام dependencyهای سیستمی لازم (ffmpeg, libsndfile, build-essential, cmake) و نصب پکیج‌های پایتون را انجام می‌دهد.

3) متغیرهای محیطی در Render
- در داشبورد Render، پروژهٔ جدید بسازید:
  - New -> Web Service
  - Connect to GitHub repo
  - Branch: main (یا branch مناسب)
  - Environment: Docker
- در Settings -> Environment -> Add Environment Variable، متغیرها را اضافه کنید:
  - TELEGRAM_TOKEN = <توکن بات>
  - (اختیاری) PITCH_SEMITONES, FORMANT_WARP, MAX_DURATION, OUTPUT_BITRATE

4) نکات مربوط به Polling vs Webhook
- کد فعلی از long-polling استفاده می‌کند (ApplicationBuilder().run_polling()) که نیاز به process دائمی دارد.
- اگر Render در پلان رایگان سرویس را sleep کند، bot متوقف خواهد شد. برای پایداری بیشتر:
  - می‌توانید سرویس را به پلان پولی ارتقاء دهید،
  - یا از سرویس‌هایی مانند Fly.io که معمولاً uptime بهتری برای instanceهای کوچک دارند استفاده کنید،
  - یا webhook راه‌اندازی کنید (نیاز به endpoint HTTPS و فعال بودن سرویس برای دریافت درخواست‌ها).

5) تست محلی با Docker
- برای ساخت و اجرای لوکال:
  docker build -t deepvoice-bot .
  docker run --env TELEGRAM_TOKEN="123:ABC" --env PITCH_SEMITONES="-6" deepvoice-bot

6) راه‌اندازی در Render
- بعد از وصل کردن ریپو و انتخاب Dockerfile، Render image را می‌سازد و اجرا می‌کند.
- لاگ‌ها را از داشبورد Render مشاهده کنید تا مطمئن شوید bot با موفقیت اجرا شده و پیام‌های لاگ مربوط به راه‌اندازی ظاهر می‌شوند.

7) اگر می‌خواهید من فایل fly.toml برای Fly.io یا فایل render.yaml آماده‌تر بسازم، بگید. من می‌تونم همچنین یک Docker Compose محلی یا Systemd unit و یک .service برای اجرا روی VPS تهیه کنم.

تذکر مهم
- برای پردازش صوتی با pyworld ممکن است زمان build طولانی‌تر از حد معمول باشد و به build-tools نیاز باشد (Dockerfile بالا این موارد را فراهم کرده).
- برای عملکرد واقعی و با کیفیت بالاتر، instance با CPU بیشتر و RAM بالاتر کمک خواهد کرد؛ روی پلان رایگان ممکن است محدودیت دیده شود.
