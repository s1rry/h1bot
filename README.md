# h1bot

Telegram-бот для сотрудника поддержки **H1Cloud**: присылает уведомления о новых
тикетах из кабинета `my.h1cloud.net`, позволяет отвечать на них прямо из Telegram
и предлагает черновики ответов через ИИ по базе знаний (`manual.md`, `kb/`).

> **Важно.** Бот работает от имени сотрудника поддержки H1Cloud — через cookie его
> сессии в кабинете. Без доступа к кабинету поддержки H1Cloud бот бесполезен.
> Бот отвечает только одному человеку — владельцу (`OWNER_TG_ID`).

---

## 1. Что понадобится

| Что | Где взять | Обязательно |
|---|---|---|
| Свой Telegram-бот (токен) | @BotFather | да |
| Свой Telegram ID | @userinfobot | да |
| Cookie сессии сотрудника | браузер, кабинет `my.h1cloud.net` | да |
| Ключ Gemini **или** Tonwave | Google AI Studio / Tonwave | нет (без него — без ИИ-ответов) |
| Компьютер или сервер с Python **3.11+** | — | да |

Бот должен работать постоянно, поэтому лучше всего — недорогой сервер (VPS) с
Ubuntu. Для пробы подойдёт и свой компьютер, но бот работает, только пока он включён.

---

## 2. Получить данные

### 2.1. Токен бота — `BOT_TOKEN`
1. Откройте в Telegram **@BotFather** → `/newbot`.
2. Придумайте имя и username (должен заканчиваться на `bot`).
3. BotFather пришлёт токен вида `1234567890:AAH...` — это `BOT_TOKEN`.

### 2.2. Свой Telegram ID — `OWNER_TG_ID`
1. Откройте **@userinfobot** → `/start`.
2. Он пришлёт ваш `Id` (только цифры) — это `OWNER_TG_ID`.

### 2.3. Cookie сессии — `H1_COOKIE`
1. Войдите в кабинет **https://my.h1cloud.net** своим аккаунтом сотрудника.
2. Откройте инструменты разработчика: **F12** (на Mac — `Cmd+Option+I`).
3. Вкладка **Network (Сеть)** → обновите страницу (`F5`).
4. Кликните по любому запросу к `my.h1cloud.net` → раздел **Request Headers**.
5. Найдите строку **`Cookie:`** и скопируйте **всё её значение целиком**
   (длинная строка вида `name1=...; name2=...`).
6. Это и есть `H1_COOKIE`. Никому её не пересылайте — по ней можно войти в ваш кабинет.

Cookie со временем истекает. Бот сам напишет «⚠️ Сессия H1Cloud истекла» —
тогда повторите шаги выше и отправьте боту: `/cookie новое_значение`
(сообщение с cookie бот сразу удалит). Перезапускать бота не нужно.

### 2.4. Ключ ИИ (по желанию)
- **Gemini:** https://aistudio.google.com/apikey → *Create API key* → `GEMINI_API_KEY`.
- **Tonwave** (Claude через прокси): ключ в кабинете Tonwave → `TONWAVE_API_KEY`.

Достаточно одного. Без ключей бот работает, но не предлагает черновики ответов.

---

## 3. Установка

### Вариант А — сервер Ubuntu (рекомендуется, работает 24/7)

Подключитесь к серверу (`ssh root@IP_сервера`) и выполните по очереди:

```bash
apt update && apt install -y git python3 python3-venv
git clone https://github.com/<владелец>/h1bot.git /opt/h1bot
cd /opt/h1bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt
cp .env.example .env
nano .env
```

В редакторе впишите значения из раздела 2 (минимум `BOT_TOKEN`, `OWNER_TG_ID`,
`H1_COOKIE`), сохраните: `Ctrl+O`, `Enter`, выйти: `Ctrl+X`.

Запуск как службы (сам поднимется после перезагрузки сервера):

```bash
cp h1bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now h1bot
systemctl status h1bot
```

В статусе должно быть `active (running)`. Логи: `journalctl -u h1bot -f`.

> Если клонируете не в `/opt/h1bot`, поправьте пути `WorkingDirectory` и `ExecStart`
> в `h1bot.service`.

### Вариант Б — свой компьютер (Mac / Linux / Windows)

Нужен Python 3.11+ (https://www.python.org/downloads/).

```bash
git clone https://github.com/<владелец>/h1bot.git
cd h1bot
python3 -m venv venv
venv/bin/pip install -r requirements.txt     # Windows: venv\Scripts\pip install -r requirements.txt
cp .env.example .env                         # Windows: copy .env.example .env
```

Заполните `.env` в любом текстовом редакторе и запустите:

```bash
venv/bin/python bot.py                       # Windows: venv\Scripts\python bot.py
```

Окно терминала должно оставаться открытым — пока оно открыто, бот работает.

---

## 4. Проверка

1. Напишите своему боту в Telegram `/start` — появится меню с кнопками.
2. Если бот молчит — проверьте `OWNER_TG_ID`: бот отвечает только этому ID.

## 5. Команды

| Команда | Что делает |
|---|---|
| `/start`, `/menu` | главное меню |
| `/mine` | мои тикеты |
| `/wait` | тикеты, ждущие ответа |
| `/free` | свободные (не взятые) тикеты |
| `/find текст` | поиск по нику, номеру или слову из тикета |
| `/t 12345` | открыть тикет по номеру |
| `/cookie значение` | обновить истёкшую cookie без перезапуска |

## 6. Настройки `.env`

| Переменная | По умолчанию | Описание |
|---|---|---|
| `BOT_TOKEN` | — | токен бота (обязательно) |
| `OWNER_TG_ID` | — | ваш Telegram ID (обязательно) |
| `H1_COOKIE` | — | cookie сессии кабинета (обязательно) |
| `POLL_SEC` | `10` | как часто проверять тикеты, сек |
| `POLL_FAST_SEC` | `4` | частота при включённом автовзятии, сек |
| `NOTIFY_NEW` | `1` | уведомлять о новых тикетах (`0` — нет) |
| `AUTO_DELAY_SEC` | `2` | пауза перед автодействием, сек |
| `GEMINI_API_KEY` / `GEMINI_MODEL` | — | ИИ через Gemini |
| `TONWAVE_API_KEY` / `TONWAVE_MODEL` | — | ИИ через Tonwave |

Слишком частый опрос (`POLL_SEC` меньше 5) может вызвать временную блокировку кабинетом.

## 7. Частые проблемы

| Симптом | Решение |
|---|---|
| Бот не отвечает на `/start` | неверный `OWNER_TG_ID` или `BOT_TOKEN`; смотрите логи |
| «Сессия H1Cloud истекла» | новая cookie через `/cookie значение` (раздел 2.3) |
| `KeyError: 'BOT_TOKEN'` при запуске | не заполнен или не найден `.env` (должен лежать рядом с `bot.py`) |
| Нет ИИ-черновиков | не задан `GEMINI_API_KEY` или `TONWAVE_API_KEY` |

## Файлы

- `bot.py` — бот
- `manual.md`, `kb/` — база знаний для ИИ-ответов
- `h1bot.service` — systemd-служба
- `state.json` — рабочие данные бота, создаётся сам (в git не хранится)
