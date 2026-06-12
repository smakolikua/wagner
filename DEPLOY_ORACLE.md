# Oracle Cloud Always Free Deploy — Fahrtenbuch Bot

Цей варіант запускає бота на Oracle Cloud Always Free VM через Docker Compose.

## 1. Що створити в Oracle

Рекомендований варіант:

- Region: найближчий до Німеччини, якщо доступний.
- Compute: Ampere A1 або маленький Always Free VM.
- OS image: Ubuntu 22.04 або Ubuntu 24.04.
- SSH key: створити або завантажити свій public key.
- Public IPv4: enabled.

Telegram bot працює через polling, тому відкривати HTTP-порт для бота не потрібно.

## 2. Підключення до VM

На локальному комп'ютері:

```bash
ssh ubuntu@YOUR_ORACLE_PUBLIC_IP
```

Якщо Oracle image використовує іншого користувача, спробувати:

```bash
ssh opc@YOUR_ORACLE_PUBLIC_IP
```

## 3. Встановити Docker

На сервері:

```bash
sudo apt update
sudo apt install -y ca-certificates curl git
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER
newgrp docker
docker version
docker compose version
```

## 4. Завантажити код

```bash
git clone https://github.com/smakolikua/wagner.git
cd wagner
```

Якщо використовується інший repo:

```bash
git clone REPO_URL
cd REPO_FOLDER
```

## 5. Налаштувати `.env`

```bash
cp .env.oracle.example .env
nano .env
```

Обов'язково заповнити:

```env
BOT_TOKEN=...
POSTGRES_PASSWORD=strong_random_password
DATABASE_URL=postgresql+asyncpg://fahrt_user:strong_random_password@postgres:5432/fahrtenbuch
ADMIN_TELEGRAM_ID=...
```

Опціонально:

```env
STORAGE_BOT_TOKEN=...
STORAGE_CHAT_ID=...
GOOGLE_MAPS_API_KEY=...
ANTHROPIC_API_KEY=...
SENTRY_DSN=...
```

Важливо: пароль у `POSTGRES_PASSWORD` і в `DATABASE_URL` має бути однаковий.

## 6. Зупинити локального бота

Перед запуском на Oracle не можна тримати локальний polling з тим самим `BOT_TOKEN`.

На локальному Mac:

```bash
pkill -f bot.main
```

## 7. Запуск на Oracle

На Oracle VM у папці repo:

```bash
docker compose -f docker-compose.oracle.yml up -d --build
```

Перевірити:

```bash
docker compose -f docker-compose.oracle.yml ps
docker compose -f docker-compose.oracle.yml logs -f bot
```

Очікувано у логах:

```text
Starting Fahrtenbuch Bot v4...
Mode: POLLING
Bot running. Ctrl+C to stop.
```

## 8. Оновлення коду

Коли будуть нові зміни:

```bash
cd wagner
git pull
docker compose -f docker-compose.oracle.yml up -d --build
```

Міграції виконуються автоматично через сервіс `migrate`.

## 9. Backup бази

Ручний dump PostgreSQL:

```bash
docker compose -f docker-compose.oracle.yml exec postgres pg_dump -U fahrt_user fahrtenbuch > backup_$(date +%Y%m%d_%H%M%S).sql
```

Перевірити backup-файли:

```bash
ls -lh backup_*.sql
```

## 10. Корисні команди

Перезапуск:

```bash
docker compose -f docker-compose.oracle.yml restart bot
```

Зупинка:

```bash
docker compose -f docker-compose.oracle.yml down
```

Логи:

```bash
docker compose -f docker-compose.oracle.yml logs -f bot
```

Статус:

```bash
docker compose -f docker-compose.oracle.yml ps
```

## 11. Якщо бот не відповідає

Перевірити:

- `docker compose -f docker-compose.oracle.yml ps`
- `docker compose -f docker-compose.oracle.yml logs -f bot`
- чи правильно заданий `BOT_TOKEN`
- чи локальний бот зупинений
- чи Oracle VM має outbound internet до `api.telegram.org`
- чи `DATABASE_URL` і `POSTGRES_PASSWORD` мають однаковий пароль

## 12. Вартість

Oracle Always Free може працювати без щомісячної оплати, але Oracle може призупиняти неактивні ресурси або акаунти з довгим простоєм. Для Telegram-бота, який постійно працює, це зазвичай краще, ніж free-плани з sleep mode.
