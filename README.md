# h1bot

Telegram-бот поддержки H1Cloud. Отвечает по базе знаний (`kb/`, `manual.md`) через LLM.

Прод: `2.26.100.80:/opt/h1bot`, systemd-сервис `h1bot.service`.

## Запуск

```bash
python3 -m venv venv && venv/bin/pip install -r requirements.txt
cp .env.example .env   # заполнить значения
venv/bin/python bot.py
```

`state.json` — рабочие данные бота (в git не хранится).
