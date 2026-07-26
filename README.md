# ContentForge

Личный сервис для автогенерации коротких видео: тема/ссылка на референс →
сценарий (Claude) → кадры (Gemini / Nano Banana) → видео из кадра (Veo) →
озвучка (ElevenLabs) → сборка (ffmpeg) → готовый .mp4.

Доступ — по инвайт-коду, ты автоматически админ с безлимитом. Остальные
(знакомые) регистрируются по коду и платят через Stripe-подписку.

## 1. Что нужно получить заранее

| Сервис | Зачем | Где взять ключ |
|---|---|---|
| Anthropic | сценарий | console.anthropic.com |
| Google AI Studio / Vertex | кадры (Nano Banana) + видео (Veo) | aistudio.google.com |
| ElevenLabs | озвучка | elevenlabs.io |
| Stripe | подписка знакомых | dashboard.stripe.com |

⚠️ Veo и часть Gemini image-функций могут требовать биллинг на Google Cloud
и доступны не во всех регионах/аккаунтах. Проверь актуальные лимиты и точные
названия методов SDK в документации Google перед запуском — эти API часто
меняются, и код в `app/pipeline/image_gen.py` / `video_gen.py` — рабочий
каркас, который может понадобиться подправить под текущую версию SDK.

Экономика: каждый ролик стоит тебе денег по API (LLM + картинки + видео +
голос), это не бесплатно. Заложи это в цену подписки для знакомых.

## 2. Настройка

```bash
cp .env.example .env
# впиши все ключи и придумай SECRET_KEY / INVITE_CODE
```

В Stripe Dashboard создай продукт с месячной ценой → скопируй `price_...`
в `STRIPE_PRICE_ID`. Вебхук пока не настраивай — сначала подними сервис.

## 3. Запуск локально (Docker)

```bash
docker compose up -d --build
```

Открой http://localhost:8000, зарегистрируйся первым (по своему же
инвайт-коду) — станешь админом с доступом без подписки.

## 4. Деплой на Railway (сервис работает 24/7, не завязан на твой компьютер)

1. Залей проект в GitHub-репозиторий (можно приватный).
2. На railway.app → **New Project → Deploy from GitHub repo** → выбери репозиторий.
3. В настройках сервиса (**Settings**) укажи:
   - **Root Directory**: `backend` — это важно, т.к. `Dockerfile` и
     `requirements.txt` лежат внутри `backend/`, и Railway должен собирать
     образ именно из этой папки, а не из корня репо.
   - Railway сам найдёт `Dockerfile` и соберёт образ (ffmpeg внутри уже есть).
4. **Variables** → добавь все переменные из `.env.example` (ключи API,
   `SECRET_KEY`, `INVITE_CODE`, Stripe-ключи). `.env`-файл в репозиторий не
   заливай — он в `.gitignore`.
5. **Volumes** → создай volume и примонтируй его на `/app/storage` — иначе
   при каждом передеплое база (SQLite) и сгенерированные видео будут
   стираться, т.к. файловая система контейнера временная.
6. **Settings → Networking → Generate Domain** — получишь публичный
   `https://<проект>.up.railway.app`. Впиши его в переменные:
   - `STRIPE_SUCCESS_URL=https://<проект>.up.railway.app/?checkout=success`
   - `STRIPE_CANCEL_URL=https://<проект>.up.railway.app/?checkout=cancel`
7. В Stripe Dashboard → Developers → Webhooks → Add endpoint:
   `https://<проект>.up.railway.app/billing/webhook`, события те же, что в
   разделе 5 ниже. Секрет — в `STRIPE_WEBHOOK_SECRET` на Railway, после чего
   Railway сам передеплоит сервис с новой переменной.
8. Открой публичный домен — там уже рабочий дашборд, доступный знакомым без
   участия твоего компьютера.

Порт Railway назначает сам через `$PORT` — `Dockerfile` уже под это
подстроен, ничего дополнительно настраивать не нужно.

## 5. Чтобы отдать доступ знакомым и принимать оплату (запуск на своей машине)

Если решишь не деплоить на Railway, а держать сервис на своём компьютере —
локальная машина не видна из интернета напрямую, а Stripe webhook и
знакомые должны достучаться до сервиса. Тогда:

Локальный компьютер не виден из интернета напрямую, а Stripe webhook и
знакомые должны достучаться до сервиса. Проще всего:

**Вариант А — Cloudflare Tunnel (бесплатно, без пробрасывания портов):**
```bash
cloudflared tunnel --url http://localhost:8000
```
Получишь публичный https-адрес — используй его как:
- домен, который даёшь знакомым,
- `STRIPE_SUCCESS_URL` / `STRIPE_CANCEL_URL` в `.env`,
- URL для Stripe webhook: `https://<твой-домен>/billing/webhook`
  (Stripe Dashboard → Developers → Webhooks → Add endpoint,
  события: `checkout.session.completed`, `customer.subscription.updated`,
  `customer.subscription.deleted`, `invoice.payment_failed`).
  Секрет вебхука впиши в `STRIPE_WEBHOOK_SECRET` и перезапусти контейнер.

**Вариант Б** — свой VPS с docker-compose вместо локальной машины, если
хочешь, чтобы сервис работал без включённого компьютера 24/7.

## 5. Как пользоваться

1. Знакомый регистрируется по инвайт-коду.
2. Жмёт «Оформить подписку» → оплачивает картой в Stripe Checkout.
3. После оплаты статус меняется на «активна» (через webhook).
4. Вводит тему (и опционально ссылку на референс) → жмёт «Сгенерировать».
5. Статус обновляется живьём (script → images → video → voice →
   assembling → done), готовое видео — кнопка «Скачать».

## 6. Структура проекта

```
backend/app/
  main.py            — точка входа FastAPI
  config.py           — все настройки из .env
  models.py            — User, Job (SQLite)
  routers/
    auth.py            — регистрация/логин/JWT
    billing.py          — Stripe checkout + webhook
    jobs.py              — запуск и статус генерации
  pipeline/
    script_gen.py         — Claude: тема → сцены
    image_gen.py            — Gemini: сцена → кадр
    video_gen.py              — Veo: кадр → видео-клип
    voice_gen.py                — ElevenLabs: текст → аудио
    assemble.py                   — ffmpeg: сборка финального ролика
    orchestrator.py                 — прогоняет всё по шагам
  static/ + templates/               — простой веб-интерфейс
```

## 7. Дальнейшие доработки (по желанию)

- Субтитры, прожигаемые в кадр (ffmpeg drawtext / .ass)
- Очередь на Redis/Celery, если генераций станет много одновременно
- Пресеты форматов (9:16 / 1:1) и длительности
- Лимит роликов в месяц на тариф
