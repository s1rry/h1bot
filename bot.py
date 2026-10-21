"""Telegram-бот для тикетов H1Cloud: уведомления и ответы из Telegram.

Работает от сессии сотрудника (cookie из my.h1cloud.net). Пишет только владельцу (OWNER_TG_ID).
"""
import asyncio
import html
import json
import logging
import os
import math
import re
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.exceptions import TelegramBadRequest
from aiogram.filters import Command
from aiogram.types import (BotCommandScopeChat, MenuButtonDefault, BufferedInputFile, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup, InlineKeyboardButton as Btn,
                           InlineKeyboardMarkup, Message)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]
OWNER_TG_ID = int(os.environ["OWNER_TG_ID"])
H1_COOKIE = os.environ["H1_COOKIE"]
H1_BASE = os.getenv("H1_BASE", "https://my.h1cloud.net")
POLL_SEC = int(os.getenv("POLL_SEC", "10"))  # один запрос очереди за проход
POLL_FAST_SEC = int(os.getenv("POLL_FAST_SEC", "4"))  # чаще, пока включено автовзятие
FAST_PAUSE_SEC = 3600  # после блокировки кабинетом час опрашиваем в обычном темпе
NOTIFY_NEW = os.getenv("NOTIFY_NEW", "1") == "1"
STATE_FILE = Path(os.getenv("STATE_FILE", "state.json"))
REMIND_MIN = int(os.getenv("REMIND_MIN", "20"))

log = logging.getLogger("h1bot")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)

bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher()

# ---------- состояние ----------

def load_state() -> dict:
    try:
        s = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    except (json.JSONDecodeError, OSError):
        log.warning("state.json повреждён, начинаю с пустого состояния")
        s = {}
    s.setdefault("last_msg", {})
    s.setdefault("seen_new", [])
    s.setdefault("tg2ticket", {})
    s.setdefault("initialized", False)
    s.setdefault("notify_new", NOTIFY_NEW)
    s.setdefault("paused", False)
    return s


MSK_TZ = timezone(timedelta(hours=3))
state = load_state()
drafts: dict[int, str] = {}           # tid -> текст ИИ-черновика / шаблона
pending_confirm: dict[str, float] = {}  # действие -> время первого нажатия


def save_state() -> None:
    state["seen_new"] = state["seen_new"][-2000:]
    if len(state["tg2ticket"]) > 5000:
        state["tg2ticket"] = dict(list(state["tg2ticket"].items())[-3000:])
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False))
    os.replace(tmp, STATE_FILE)


def confirmed(key: str) -> bool:
    """Двойное нажатие за 10 секунд — для опасных действий."""
    now = time.time()
    if now - pending_confirm.get(key, 0) < 10:
        pending_confirm.pop(key, None)
        return True
    pending_confirm[key] = now
    return False


# ---------- API H1Cloud ----------

class SessionExpired(Exception):
    pass


class Blocked(Exception):
    """Кабинет не пускает: 403/429 или вместо JSON пришла страница проверки."""
    def __init__(self, msg: str, retry_after: int = 0):
        super().__init__(msg)
        self.retry_after = retry_after


h1 = httpx.AsyncClient(
    base_url=H1_BASE,
    headers={"Cookie": H1_COOKIE, "Accept": "application/json", "User-Agent": "h1-support-tg/1.1"},
    timeout=60,
)


async def api(method: str, path: str, body: dict | None = None) -> dict:
    r = await h1.request(method, path, json=body)
    if r.status_code == 401:
        raise SessionExpired(path)
    try:
        data = r.json()
    except ValueError:
        data = None
    if r.status_code in (403, 429) or (data is None and r.status_code < 500):
        err = (data or {}).get("error") if isinstance(data, dict) else None
        if r.status_code == 403 and isinstance(data, dict) and err not in ("challenge_required", None):
            raise RuntimeError(f"403: {str(err)[:200]}")  # обычный запрет действия, не антибот
        try:
            ra = int(r.headers.get("retry-after", "0"))
        except ValueError:
            ra = 0
        raise Blocked(f"{r.status_code} {err or 'не JSON'}", ra)
    if r.status_code >= 400:
        msg = (data or {}).get("error") or (data or {}).get("message") or r.text if isinstance(data, dict) else r.text
        raise RuntimeError(f"{r.status_code}: {str(msg)[:200]}")
    return data


QUEUE_META: dict = {}  # stale_count, stale_hours, fresh_minutes, half_rate_active из последнего опроса


async def queue_raw(mine: bool) -> dict:
    q = "status=open&mine=1" if mine else "status=open"
    return await api("GET", f"/api/staff/desk/queue?{q}")


def is_priority(i: dict) -> bool:
    return (i.get("pay_mult") or 1) > 1 or (i.get("boost") or 0) > 0


def is_free(i: dict) -> bool:
    return not i.get("assigned_to") and i.get("status") == "open"


def age_hours(i: dict) -> float:
    from datetime import datetime
    try:
        created = datetime.fromisoformat((i.get("created_at") or "").replace("Z", "+00:00"))
        if created.tzinfo is None:  # кабинет отдаёт время по Москве без зоны
            from datetime import timedelta, timezone
            created = created.replace(tzinfo=timezone(timedelta(hours=3)))
        return (datetime.now(created.tzinfo) - created).total_seconds() / 3600
    except Exception:
        return 0.0


def dept_ok(i: dict) -> bool:
    allowed = state.get("depts")
    return not allowed or i.get("department") in allowed


async def queue(mine: bool) -> list[dict]:
    q = "status=open&mine=1" if mine else "status=open"
    return (await api("GET", f"/api/staff/desk/queue?{q}")).get("items", [])


async def ticket(tid: int) -> dict:
    return await api("GET", f"/api/staff/desk/requests/{tid}")


async def act(tid: int, action: str, body: dict | None = None) -> dict:
    return await api("POST", f"/api/staff/desk/requests/{tid}/{action}", body or {})


async def send_reply(tid: int, text: str, internal: bool = False) -> None:
    await act(tid, "message", {"body": text, "internal": internal})


async def upload_file(tid: int, data: bytes, filename: str, caption: str = "") -> None:
    r = await h1.post(f"/api/staff/desk/requests/{tid}/attach",
                      files={"file": (filename, data)}, data={"caption": caption} if caption else None)
    if r.status_code == 401:
        raise SessionExpired("attach")
    if r.status_code >= 400:
        raise RuntimeError(f"{r.status_code}: {r.text[:200]}")


async def download(url: str) -> bytes:
    full = abs_url(url)
    if httpx.URL(full).host != httpx.URL(H1_BASE).host:
        async with httpx.AsyncClient(timeout=60) as ext:  # чужой хост — без cookie сотрудника
            r = await ext.get(full)
            r.raise_for_status()
            return r.content
    r = await h1.get(full)
    r.raise_for_status()
    return r.content


QUICK_GROUPS = [
    ("💬 Общие", {
        "g1": ("⏳ Проверяем, 30 мин", "Проверяем ваш вопрос. Вернёмся с ответом в этом тикете в течение 30 минут."),
        "g2": ("📋 Запрос данных", "Чтобы проверить проблему, пришлите, пожалуйста: скриншот или текст ошибки, устройство и приложение, с которых вы подключаетесь, и через какой интернет (домашний или мобильный, какой оператор)."),
        "g3": ("🔄 Статус, час", "Мы продолжаем работу по вашему обращению. Следующее обновление — в течение часа."),
        "g4": ("❓ Вопрос актуален?", "Подскажите, пожалуйста, вопрос ещё актуален? Если да, пришлите скриншот ошибки, и мы проверим."),
        "g5": ("🔚 Остались вопросы?", "Подскажите, пожалуйста, остались ли у вас вопросы по этому обращению? Если нет, мы его закроем. Если в дальнейшем появятся новые вопросы, создайте, пожалуйста, новое обращение — мы с радостью поможем."),
        "g6": ("✅ Закрытие", "Рады, что всё заработало. Если появятся вопросы, обращайтесь — мы всегда на связи."),
    }),
    ("🔑 Доступ и панель", {
        "a1": ("🔑 Данные сервера", "Адрес, логин и пароль панели вашего сервера находятся в личном кабинете: «Мои серверы» → сервер → блок «Панель управления» → кнопка «Данные». Логин и пароль из «Данных аккаунта» на главной для VPN-панели не подходят."),
        "a2": ("🔐 Пароль 3x-ui в консоли", "Сейчас после переустановки сервера кнопка «Данные панели 3x-ui» может показывать неверный пароль, мы знаем об этой проблеме. Актуальный пароль можно посмотреть в консоли сервера: откройте сервер в панели управления и нажмите «Рестарт», при запуске пароль появится в консоли."),
        "a3": ("🌐 Адрес /panel (H1)", "Чтобы открыть панель, используйте адрес из кнопки «Данные» в карточке сервера. Он начинается с http:// и заканчивается на /panel. Без /panel открывается служебная страница."),
        "a4": ("✨ Настроить автоматически", "Подключения можно создать автоматически: в личном кабинете у сервера нажмите «Настроить автоматически» и отметьте VLESS TCP Reality, gRPC Reality и xHTTP Reality. Система сама создаст подключения на свободных портах и проверит их. Затем добавьте клиентов в новые подключения и заново импортируйте подписку в приложение."),
        "a5": ("🖥 SSH только у VPS", "Доступа по SSH на VPN-серверах и серверах для ботов нет: они работают с готовой панелью, все настройки делаются через веб-панель сервера. Если нужен полный доступ к серверу (root по SSH, установка любого ПО), закажите VPS или VDS в личном кабинете, раздел «Купить VPS», — после выдачи вы получите IP-адрес и данные для входа."),
    }),
    ("🌍 Блокировки и сеть", {
        "n1": ("🌐 Чекер", "Выключите, пожалуйста, VPN, откройте https://h1cloud.net/check, запустите проверку и пришлите сюда готовый текст с результатом внизу страницы."),
        "n2": ("🛡 Блокировка ТСПУ", "Если IP сервера попадает под блокировку ТСПУ, система сама обнаруживает это и восстанавливает доступ, обычно примерно за 15 минут. Чтобы после восстановления всё работало без перенастройки, подключайтесь по домену сервера (вида xxN.h1cloud.net), а не по IP."),
        "n3": ("🚚 Предложить перенос", "Сервер недоступен из вашей сети. Мы можем перенести его в другую локацию, для вас это бесплатно. Тариф и срок сохранятся, адрес сервера изменится. Обратите внимание: после переноса все данные панели управления будут удалены (включая пользователей, инбаунды и настройки), сервер потребуется настроить заново. Подтвердите, пожалуйста, согласие и желаемую локацию."),
        "n6": ("🔁 Перенос сам (локация доступна)", "По результатам вашей проверки текущая локация сервера доступна из вашей сети. Если вы всё же хотите сменить локацию, это можно сделать самостоятельно: личный кабинет → «Мои серверы» → сервер → «Перенести локацию». Стоимость — 50 ₽, тариф и срок сохранятся. Обратите внимание: после переноса все данные панели управления будут удалены (включая пользователей, инбаунды и настройки), сервер потребуется настроить заново. IP-адрес и адрес сервера тоже изменятся."),
        "n4": ("🔁 Смена IP VPS", "Чтобы восстановить доступ, смените IP-адрес VPS в настройках сервера в личном кабинете. Стоимость смены — 250 ₽. После смены подключайтесь по новому адресу, он появится в карточке сервера. Если IP был заблокирован сразу при выдаче сервера, сообщите нам — проверим и сменим его бесплатно."),
        "n5": ("📶 Дома не работает", "Некоторые домашние провайдеры ограничивают отдельные типы подключений. Попробуйте добавить подключение с другим транспортом: в личном кабинете у сервера нажмите «Настроить автоматически» и отметьте gRPC Reality и xHTTP Reality, затем заново импортируйте подписку в приложение."),
    }),
    ("💳 Оплата и возвраты", {
        "p1": ("🧾 Запрос по оплате", "Чтобы проверить платёж, пришлите, пожалуйста, чек об оплате (сумма, дата и время) и скриншот ошибки, если она была. Уточните также, не вернулись ли деньги обратно на карту."),
        "p2": ("📨 Возврат на рассмотрение", "Передадим ваш запрос на рассмотрение. Решение по возврату принимается после проверки ситуации, о результате сообщим в этом тикете."),
        "p3": ("📄 Возврат п. 7.10", "Мы рассмотрели ваш запрос. Согласно п. 7.10 пользовательского соглашения возврат денежных средств производится на внутренний баланс аккаунта, вывод на банковскую карту не осуществляется. Средства на балансе можно использовать для оплаты любых услуг H1Cloud. С условиями можно ознакомиться здесь: https://my.h1cloud.net/static/docs/terms.html"),
        "p5": ("🎰 Не хватает денег", "Если на продление или покупку не хватает небольшой суммы, загляните в личный кабинет в раздел «Бонусы и защита»: там раз в сутки можно бесплатно прокрутить рулетку с выигрышем на баланс. Также за отзыв о H1Cloud в группе @h1cloudreviews бот пришлёт промокод на скидку 10%."),
        "p4": ("🗑 Удаление сервера", "При удалении VPN-сервера деньги за оставшийся срок возвращаются на баланс. В некоторых случаях зачисление может занять до 2–3 дней."),
    }),
    ("⚙️ Настройка", {
        "s1": ("🔒 HTTPS-подписка", "Для https-подписки нужен свой домен. У регистратора домена создайте для поддомена CNAME-запись на домен вашей ноды (вида xxN.h1cloud.net, его видно в адресе панели). Затем в панели откройте «Домены» → «Добавить домен», выберите назначение «Подписка» и включите «Выдать SSL-сертификат»."),
        "s2": ("📱 LTE-доступ", "Для работы на мобильном интернете при ограничениях операторов есть LTE-доступ: карточка сервера → «Подключить LTE-доступ». Стоимость: 500 ₽ за подключение и 2 ₽ за каждый ГБ трафика в месяц. Перед покупкой его можно бесплатно проверить у своего оператора: бот @h1freevpnbot выдаст тестовый ключ."),
        "s3": ("🔄 Сменить панель", "Сменить панель на уже купленном сервере нельзя. Чтобы получить другую панель, удалите текущий сервер (деньги за оставшийся срок вернутся на баланс) и купите новый, выбрав нужную панель в поле «Панель управления» при оформлении заказа."),
        "s4": ("🛒 Где купить VPS", "VPS можно купить в личном кабинете: раздел «Купить VPS». Купленный VPS будет внизу этой же страницы, в блоке «Мои VPS»."),
        "s5": ("🛠 Настройка не входит", "Настройка вашей панели, домена, DNS и программ на сервере выходит за рамки поддержки, но мы подскажем, какие параметры сервера для этого нужны, и проверим неполадки на нашей стороне. Если нужна полная настройка администраторами, при покупке сервера можно выбрать услугу «Настройка под ключ» — 1000 ₽ разово. К уже купленному серверу её подключить нельзя, только при новой покупке."),
    }),
]
QUICK_GROUPS.append(("🧭 Сложные ситуации", {
    "c1": ("😠 Грубость", "Мы понимаем ваше недовольство. Уже проверяем причину и сообщим результат в этом тикете в течение 30 минут."),
    "c2": ("⚠️ Угрозы, конфликт", "Мы зафиксировали ваше обращение и передали его администратору. Ответ поступит в этом тикете."),
    "c3": ("👥 Пишет третье лицо", "Мы можем предоставить эти данные только владельцу услуги — через личный кабинет или тикет из его аккаунта."),
    "c4": ("🔑 Прислал пароль", "Смените, пожалуйста, пароль в панели управления самостоятельно — мы не запрашиваем и не храним пароли клиентов в переписке."),
    "c5": ("🎁 Компенсация", "Индивидуальные компенсации в рамках поддержки не предусмотрены. Компенсации за массовые сбои начисляются автоматически всем затронутым клиентам и объявляются в нашем канале @h1cloud."),
    "c6": ("🕓 Нет сроков", "Точных сроков восстановления пока нет. Мы следим за ситуацией и сообщим новости в этом тикете, следующее обновление — в течение часа."),
    "c7": ("🏢 Дата-центры", "Информацию о дата-центрах и инфраструктуре мы не раскрываем. Каждая локация размещена в отдельном дата-центре."),
    "c8": ("🤖 Написать бота", "Разработка и запуск кода клиента выходят за рамки поддержки. Мы подскажем, какие параметры сервера для этого нужны. Настройку администрацией можно заказать как услугу «Настройка под ключ» при покупке сервера."),
    "c9": ("📡 Ping и tracert", "Чтобы проверить сеть, выключите, пожалуйста, VPN и выполните на компьютере (Win+R → cmd) команды: ping IP-сервера и tracert IP-сервера (IP без порта). Пришлите результат скриншотом или текстом."),
    "c10": ("🖐 Пинг есть, интернета нет", "Попробуйте, пожалуйста, в настройках подключения в панели сменить отпечаток (fingerprint) на edge, сохранить и заново импортировать подписку в приложение."),
    "c11": ("📜 Правила сервиса", "С правилами работы сервиса можно ознакомиться в пользовательском соглашении: https://my.h1cloud.net/static/docs/terms.html"),
}))
QUICK = {k: v for _, g in QUICK_GROUPS for k, v in g.items()}

# подсказки быстрых фраз по словам в сообщении клиента: (регулярка, ключи фраз)
HINTS = [
    (r"проверка локаций", ["n3", "n6"]),
    (r"пинг есть|интернета нет|нет интернета|сайты не (откр|груз)", ["c10"]),
    (r"парол|логин|не пуска|unauthori[sz]ed|данные для входа", ["a1", "a2"]),
    (r"vpn-api|\"service\"", ["a3"]),
    (r"\bssh\b|\broot\b|mtproxy", ["a5"]),
    (r"перенес|перенос|перенест|друг\w* локац|смен\w* локац", ["n1", "n6"]),
    (r"дом(а|ашн)|wi-?fi|вай-?фай|ростелеком", ["n5"]),
    (r"(vps|впс|vds|вдс).{0,40}((смен\w*|помен\w*) ip|ip.{0,15}(бан|заблок))|((смен\w*|помен\w*) ip|ip.{0,15}(бан|заблок)).{0,40}(vps|впс|vds|вдс)", ["n4"]),
    (r"\blte\b|\bлте\b|\bбс\b|белы\w* спис|лте-доступ", ["s2"]),
    (r"не работ|не подключ|n/a|н/д|не гру|недоступ|не открыва|не пингу", ["n1", "g2"]),
    (r"возврат|верн\w* (деньг|средств)|на карту", ["p2", "p3"]),
    (r"оплат|зачисл|платеж|платёж|пополн|\bчек\b", ["p1"]),
    (r"не хватает|рулетк", ["p5"]),
    (r"удал(?!.{0,40}(vps|впс|vds|вдс))", ["p4"]),
    (r"https.?подписк|cleartext|свой домен|домен.{0,20}(подписк|ssl)|ssl|сертификат", ["s1"]),
    (r"(смен|помен|друг)\w* панел", ["s3"]),
    (r"куп\w* (vps|впс|вдс|vds)", ["s4"]),
    (r"компенс", ["c5"]),
    (r"(напис|сдела|настро|запуст)\w* (мне )?бот|код бота", ["c8"]),
    (r"дата.?центр|\bдц\b", ["c7"]),
    (r"медленн|скорост|пинг (больш|высок)|\bлаг", ["c9"]),
    (r"спасибо|заработал|всё работает|все работает|разобрал", ["g5", "g6"]),
]


def hint_keys(text: str, limit: int = 3) -> list[str]:
    low = (text or "").lower()
    keys: list[str] = []
    for pattern, ks in HINTS:
        if re.search(pattern, low):
            keys += [k for k in ks if k not in keys]
        if len(keys) >= limit:
            break
    return keys[:limit]


def with_hints(tid: int, text: str, base: InlineKeyboardMarkup | None = None) -> InlineKeyboardMarkup:
    """Клавиатура тикета + сверху кнопки подходящих быстрых фраз."""
    base = base or kb_ticket(tid)
    rows = [[Btn(text=f"💡 {QUICK[k][0]}", callback_data=f"qs:{tid}:{k}")] for k in hint_keys(text)]
    return InlineKeyboardMarkup(inline_keyboard=rows + base.inline_keyboard)


# ---------- разбор чекера h1cloud.net/check ----------

CHECK_RE = re.compile(r"(Доступно|НЕДОСТУПНО|Недоступно|Не удалось проверить|Заблокирован\w*(?: ТСПУ)?)\s*\((\d+)\)\s*:", re.I)


def parse_checker(text: str) -> dict[str, list[str]] | None:
    """{'ok': [...], 'bad': [...]} из текста «Проверка локаций h1cloud». bad = недоступно, не удалось, ТСПУ."""
    if "проверка локаций" not in (text or "").lower():
        return None
    res: dict[str, list[str]] = {"ok": [], "bad": []}
    heads = list(CHECK_RE.finditer(text))
    for n, h in enumerate(heads):  # группа — от заголовка до следующего заголовка (в одну строку или в несколько)
        rest = text[h.end(): heads[n + 1].start() if n + 1 < len(heads) else len(text)]
        rest = rest.split("\n\n")[0].replace("\n", " ")
        names = [re.sub(r"\s*\(.*?\)\s*$", "", x).strip() for x in rest.split(",")]
        names = [x for x in names if x and x not in ("—", "-", "–") and not x.endswith("…") and len(x) <= 40]
        res["ok" if h.group(1).lower() == "доступно" else "bad"] += names
    return res


LOC_ALIASES = {"россия": "москва"}


def country_of(name: str) -> str:
    """«🇫🇮 Финляндия» и «Финляндия-4 (90 мс)» → «финляндия»."""
    base = re.sub(r"[^А-Яа-яЁёA-Za-z\s-]", "", name or "").strip().lower()
    base = base.split("-")[0].strip()
    return LOC_ALIASES.get(base, base)


def short_loc(name: str) -> str:
    """«Финляндия-4» → «4», «Германия-боты-2» → «боты-2»."""
    return name.split("-", 1)[1] if "-" in name else name


def norm_loc(s: str) -> str:
    return re.sub(r"[\s_]+", "-", (s or "").strip().lower())


async def checker_hint(tid: int, text: str) -> None:
    """Клиент прислал результат чекера: сверяем с локациями его серверов и предлагаем нужный ответ."""
    res = parse_checker(text)
    if not res or not (res["ok"] or res["bad"]):
        return
    lines = [f"🌐 <b>Чекер клиента #{tid}</b>: доступно {len(res['ok'])}, недоступно {len(res['bad'])}"]
    if res["bad"]:
        lines.append("❌ " + esc(", ".join(res["bad"][:15])) + (" …" if len(res["bad"]) > 15 else ""))
    verdict = set()
    try:
        servers = (await api("GET", f"/api/staff/desk/requests/{tid}/client-servers")).get("servers") or []
    except Exception:
        servers = []
    seen_countries: dict[str, str] = {}
    for sv in servers:
        loc = sv.get("location_name") or ""
        country = country_of(loc)
        if country not in seen_countries:
            ok_n = [x for x in res["ok"] if country_of(x) == country]
            bad_n = [x for x in res["bad"] if country_of(x) == country]
            if not ok_n and not bad_n:
                st, v = "❔ нет в чекере, сверить вручную", ""
            elif not bad_n:
                st, v = f"✅ все локации страны доступны ({len(ok_n)}) → перенос сам за 50 ₽", "ok"
            elif not ok_n:
                st, v = f"❌ все локации страны недоступны ({len(bad_n)}) → переносим сами, бесплатно", "bad"
            else:
                st, v = (f"⚠️ часть недоступна: ❌ {esc(', '.join(short_loc(x) for x in bad_n))}; "
                         f"✅ {esc(', '.join(short_loc(x) for x in ok_n))} — сверить ноду сервера"), "mixed"
            seen_countries[country] = st
            verdict.add(v)
        lines.append(f"🖥 {esc(sv.get('name'))} #{sv.get('id')} · нода {esc(sv.get('node_id'))} · 📍 {esc(loc)}: "
                     f"{seen_countries[country]}")
    if not servers:
        lines.append("Серверов клиента не видно (VPS здесь не отображаются) — сверить локацию вручную.")
    keys = (["n3"] if verdict & {"bad", "mixed"} else []) + (["n6"] if verdict & {"ok", "mixed"} else [])
    keys = keys or ["n3", "n6"]
    rows = [[Btn(text=f"💡 {QUICK[k][0]}", callback_data=f"qs:{tid}:{k}")] for k in keys]
    await bot.send_message(OWNER_TG_ID, "\n".join(lines), reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


# ---------- форматирование ----------

def esc(s) -> str:
    return html.escape(str(s or ""))


def abs_url(url: str) -> str:
    return H1_BASE + url if url.startswith("/") else url


def split_service(text: str) -> tuple[str | None, str]:
    """Отделить строку «Услуга: …» от текста клиента."""
    svc, rest = None, []
    for line in (text or "").splitlines():
        if svc is None and line.strip().startswith("Услуга:"):
            parts = [p.strip() for p in line.split(":", 1)[1].split("·")]
            svc = " · ".join(parts[:2])
        elif line.strip():
            rest.append(line.strip())
    return svc, " ".join(rest)


def header(req: dict, first: str | None = None) -> str:
    flags = ""
    if req.get("priority") == "high":
        flags += " 🔥"
    if req.get("status") == "escalated":
        flags += " ⬆️"
    if is_priority(req):
        mult = req.get("pay_mult") or 1
        flags += f" ⚡x{mult:g}" if mult > 1 else " ⚡"
    created = req.get("created_at") or ""
    when = f"{created[8:10]}.{created[5:7]} {created[11:16]}" if len(created) >= 16 else ""
    svc, problem = split_service(first if first is not None else (req.get("preview") or ""))
    if len(problem) > 140:
        problem = problem[:140].rsplit(" ", 1)[0] + "…"
    lines = [f"<b>#{req['id']}</b>{flags} · 👤 {esc(req.get('client_name'))}",
             f"🎯 {esc(req.get('department_name'))}"]
    if svc:
        lines.append(f"🖥 {esc(svc)}")
    if problem:
        lines.append(f"💬 «{esc(problem)}»")
    if when:
        lines.append(f"⏰ {when}")
    return "\n".join(lines)


def ticket_url(tid: int) -> str:
    return f"{H1_BASE}/cabinet"  # прямых ссылок на тикет кабинет не поддерживает


def fmt_msg(m: dict) -> str:
    text = esc(m.get("body"))
    if m.get("attachment_url"):
        text += f"\n📎 <a href=\"{esc(abs_url(m['attachment_url']))}\">{esc(m.get('attachment_name') or 'вложение')}</a>"
    return text


def kb_free(tid: int, expanded: bool = False) -> InlineKeyboardMarkup:
    toggle = (Btn(text="◀️ Назад", callback_data=f"short:{tid}") if expanded
              else Btn(text="📖 Полностью", callback_data=f"full:{tid}"))
    return InlineKeyboardMarkup(inline_keyboard=[
        [Btn(text="✋ Взять + привет", callback_data=f"take:{tid}")],
        [Btn(text="🧠 Разбор", callback_data=f"an:{tid}"), toggle],
        [Btn(text="📜 История", callback_data=f"hist:{tid}"),
         Btn(text="🔗 В кабинете", url=ticket_url(tid))],
    ])


def short_view(req: dict, prefix: str = "", first_msg: str | None = None) -> str:
    return f"{prefix}{header(req, first_msg)}"


async def short_view_full(item: dict, prefix: str = "") -> str:
    """Короткий вид по полному первому сообщению клиента (preview в очереди обрезан кабинетом)."""
    try:
        data = await ticket(item["id"])
        first = next((m.get("body") or "" for m in data.get("messages", [])
                      if m.get("sender_role") == "client" and not m.get("internal")), None)
    except Exception:
        first = None
    return short_view(item, prefix, first)


def full_view(data: dict) -> str:
    req = data["request"]
    msgs = [m for m in data.get("messages", []) if m.get("sender_role") == "client" and not m.get("internal")]
    body = "\n\n".join(f"👤 {esc((m.get('created_at') or '')[11:16])}\n{fmt_msg(m)}" for m in msgs) or esc(req.get("preview"))
    first = msgs[0].get("body") if msgs else None
    text = f"{header(req, first)}\n\n{body}"
    return text if len(text) < 3900 else text[:3850] + "\n\n<i>…обрезано, полностью в «История»</i>"


CONFIRM_ACTIONS = {  # кнопка: (вопрос, эндпоинт кабинета, текст результата)
    "resolve": ("закрыть как решённый", "resolve", "✅ Решено:"),
    "esc": ("передать старшему", "escalate", "⬆️ Передано старшему:"),
    "rel": ("вернуть в очередь", "release", "↩️ Возвращено в очередь:"),
}


def kb_ticket(tid: int, mine: bool = True, more: bool = False) -> InlineKeyboardMarkup:
    """Короткая клавиатура под телефон: 2 ряда по 3, остальное — под «⋯ Ещё»."""
    if not mine:
        return kb_free(tid)
    rows = [
        [Btn(text="🧠 Разбор", callback_data=f"an:{tid}"),
         Btn(text="⚡ Быстро", callback_data=f"quick:{tid}"),
         Btn(text="📋 Шаблоны", callback_data=f"tpls:{tid}")],
        [Btn(text="✅ Решено", callback_data=f"resolve:{tid}"),
         Btn(text="⬆️ Старшему", callback_data=f"esc:{tid}"),
         Btn(text="▴ Скрыть" if more else "⋯ Ещё", callback_data=f"{'less' if more else 'more'}:{tid}")],
    ]
    if more:
        rows += [
            [Btn(text="🤖 ИИ", callback_data=f"ai:{tid}"),
             Btn(text="📜 История", callback_data=f"hist:{tid}"),
             Btn(text="🖥 Серверы", callback_data=f"srv:{tid}")],
            [Btn(text="🔥 Срочно", callback_data=f"prio:{tid}"),
             Btn(text="↩️ Очередь", callback_data=f"rel:{tid}"),
             Btn(text="🔗 Кабинет", url=ticket_url(tid))],
        ]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def kb_draft(tid: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[
        Btn(text="📤 Отправить клиенту", callback_data=f"senddraft:{tid}"),
        Btn(text="📝 Заметкой", callback_data=f"notedraft:{tid}"),
    ]])


def split_html(text: str, size: int = 3900) -> list[str]:
    """Режем по пустым строкам/переводам строки, чтобы не разрывать теги и &-сущности."""
    parts, cur = [], ""
    for line in text.split("\n"):
        while len(line) > size:  # одна гигантская строка — режем по пробелу
            cut = line.rfind(" ", 0, size)
            cut = cut if cut > 0 else size
            parts.append(cur + line[:cut]) if cur else parts.append(line[:cut])
            cur, line = "", line[cut:]
        if len(cur) + len(line) + 1 > size:
            parts.append(cur)
            cur = ""
        cur += (("\n" if cur else "") + line)
    if cur or not parts:
        parts.append(cur)
    return parts


def plain(text: str) -> str:
    return html.unescape(re.sub(r"<[^>]+>", "", text))


WIDE_PAD = "\u2800" * 38  # невидимая строка: расширяет короткое сообщение, чтобы кнопки по 3 в ряд не обрезались


def widen(text: str, kb: InlineKeyboardMarkup | None) -> str:
    """Telegram делает клавиатуру шириной с сообщение: у коротких сообщений подписи кнопок
    обрезаются до «…». Если в клавиатуре есть ряды по 3 кнопки, а текст узкий — дописываем невидимую строку."""
    if not kb or not any(len(r) >= 3 for r in kb.inline_keyboard):
        return text
    if max((len(ln) for ln in plain(text).split("\n")), default=0) >= 38:
        return text
    return f"{text}\n{WIDE_PAD}"


async def send_safe(text: str, kb: InlineKeyboardMarkup | None = None):
    """Отправка с откатом на обычный текст, если Telegram не разобрал HTML."""
    text = widen(text, kb)
    try:
        return await bot.send_message(OWNER_TG_ID, text, disable_web_page_preview=True, reply_markup=kb)
    except TelegramBadRequest as e:
        if "parse" not in str(e).lower() and "entit" not in str(e).lower():
            raise
        return await bot.send_message(OWNER_TG_ID, plain(text)[:4000], parse_mode=None,
                                      disable_web_page_preview=True, reply_markup=kb)


async def send(text: str, tid: int, mine: bool = True, kb: InlineKeyboardMarkup | None = None) -> None:
    chunks = split_html(text)
    for n, chunk in enumerate(chunks):
        last = n == len(chunks) - 1
        sent = await send_safe(chunk, (kb or kb_ticket(tid, mine)) if last else None)
        state["tg2ticket"][str(sent.message_id)] = tid


# ---------- опрос ----------

session_alerted = False


CLAIM_TEXT = ("Здравствуйте. Подскажите, пожалуйста, ошибка ещё актуальна? Чтобы быстрее разобраться "
              "в проблеме, пришлите скриншот ошибки.")
RESPONDER_TEXT = "Мы получили ваше сообщение. Пожалуйста, подождите — мы ответим вам в этом тикете."
RESPONDER_MIN = int(os.getenv("RESPONDER_MIN", "40"))
AUTO_DELAY_SEC = int(os.getenv("AUTO_DELAY_SEC", "2"))
CLAIMING: set[int] = set()  # тикеты, которые ждут автовзятия
BG_TASKS: set = set()  # держим ссылки, чтобы задачи автовзятия не собрал сборщик мусора
free_initialized = False


def remember_claim(tid: int) -> None:
    """По взятым тикетам бот узнаёт свой id в очереди без отдельного запроса."""
    taken = state.setdefault("claimed_any", [])
    taken.append(tid)
    del taken[:-20]
    state.setdefault("claimed_at", {})[str(tid)] = time.time()


def mark_auto(tid, kind: str, upd: str | None = None) -> None:
    """Запомнить, что клиенту ответил бот (а не я) — для списка «Ответил автоматически»."""
    rec = state.setdefault("auto_sent", {}).setdefault(str(tid), {"ts": time.time()})
    rec["kind"], rec["ts"], rec["upd"] = kind, time.time(), upd or "pending"
    # время отправки по МСК (как в кабинете): updated_at раньше этого — ещё старые данные очереди
    rec["sent"] = (datetime.now(MSK_TZ) - timedelta(seconds=5)).strftime("%Y-%m-%dT%H:%M:%S")


def unmark_auto(tid) -> None:
    state.get("auto_sent", {}).pop(str(tid), None)


def track_auto_sent(mine_items: list[dict], all_items: list[dict]) -> None:
    """Убираем из списка тикеты, где после бота ответил сотрудник, или которые ушли с меня / закрылись."""
    sent = state.setdefault("auto_sent", {})
    by_id = {str(i["id"]): i for i in mine_items}
    everywhere = {str(i["id"]): i for i in all_items}
    for tid, rec in list(sent.items()):
        item = by_id.get(tid)
        if not item:
            other = everywhere.get(tid)
            if all_items and (not other or (other.get("assigned_to") and state.get("my_id")
                                            and other.get("assigned_to") != state.get("my_id"))):
                sent.pop(tid)  # тикет закрыт или его забрал другой сотрудник
            continue
        if item.get("last_sender_role") == "client":
            continue  # клиент ответил — всё ещё ждёт меня
        upd = item.get("updated_at") or ""
        if rec.get("upd") == "pending":
            if upd >= rec.get("sent", ""):  # очередь уже знает про ответ бота
                rec["upd"] = upd
        elif rec.get("upd") != upd:
            sent.pop(tid)  # после автоответа в тикете писал сотрудник


def baseline(tid: int, data: dict) -> None:
    """Запомнить, что уже прочитано в тикете, чтобы не прислать его повторно."""
    msgs = [m for m in data.get("messages", []) if not m.get("internal")]
    state["last_msg"][str(tid)] = max((m["id"] for m in msgs), default=-1)
    req = data.get("request") or {}
    if req.get("updated_at"):
        state.setdefault("upd", {})[str(tid)] = req["updated_at"]


async def auto_take(item: dict) -> bool:
    """Автовзятие без кнопки «Взять в работу»: сразу пишем клиенту приветствие —
    тикет закрепляется за тем, кто ответил первым."""
    tid = item["id"]
    text = state.get("claim_text") or CLAIM_TEXT
    try:
        await send_reply(tid, text)
    except Blocked as e:
        log.warning("auto-reply #%s blocked: %s", tid, e)
        return "blocked"
    except Exception as e:
        log.warning("auto-reply #%s failed: %s", tid, e)
        return False
    state.pop("claim_blocks", None)
    remember_claim(tid)
    mark_auto(tid, "приветствие")
    try:
        data = await ticket(tid)
        baseline(tid, data)
        mark_auto(tid, "приветствие", (data.get("request") or {}).get("updated_at"))
        first = next((m.get("body") or "" for m in data.get("messages", [])
                      if m.get("sender_role") == "client" and not m.get("internal")), "")
    except Exception:
        first = None
    await send(f"🤖 <b>Ответил автоматически</b>\n💬 <i>Отправлено: {esc(text)}</i>\n\n{header(item, first)}", tid,
               kb=with_hints(tid, first or item.get("preview") or ""))
    if first and parse_checker(first):
        try:
            await checker_hint(tid, first)
        except Exception:
            log.exception("checker hint #%s failed", tid)
    return True


async def poll_once() -> None:
    global session_alerted
    first_run = not state["initialized"]

    raw = await queue_raw(mine=False)  # единственный регулярный запрос за проход
    items = raw.get("items", [])
    if not state.get("my_id"):
        # свой id: из последнего взятого тикета, иначе раз в 10 минут спрашиваем «мои»
        my = None
        by_id = {i["id"]: i for i in items}
        for t in reversed(state.get("claimed_any", [])):
            if by_id.get(t, {}).get("assigned_to") and time.time() - state.get("claimed_at", {}).get(str(t), 0) < 600:
                my = by_id[t]["assigned_to"]
                break
        if my is None and time.time() - state.get("my_id_checked_at", 0) > 600:
            state["my_id_checked_at"] = time.time()
            ids = {i.get("assigned_to") for i in await queue(mine=True) if i.get("assigned_to")}
            my = ids.pop() if len(ids) == 1 else None
        if my is not None:
            state["my_id"] = my
            state.pop("mine_ids", None)  # свои тикеты теперь видны — запомнить их молча
    my_id = state.get("my_id")
    mine_items = [i for i in items if my_id and i.get("assigned_to") == my_id]
    if "mine_ids" not in state:  # первый запуск этой функции — запомнить молча
        state["mine_ids"] = [i["id"] for i in mine_items]
    known_mine = set(state["mine_ids"])
    claimed_at = state.setdefault("claimed_at", {})
    for t in [t for t, ts in claimed_at.items() if time.time() - ts > 3600]:
        claimed_at.pop(t)  # забываем взятые давнее часа
    state.pop("claimed_by_bot", None)
    assigned_new = {i["id"] for i in mine_items
                    if i["id"] not in known_mine and str(i["id"]) not in claimed_at and not first_run}
    state["mine_ids"] = [i["id"] for i in mine_items]

    for item in mine_items:
        tid = item["id"]
        last_seen = state["last_msg"].get(str(tid), 0)
        upd = state.setdefault("upd", {})
        # открываем тикет только если в нём что-то изменилось и последним писал клиент
        if tid not in assigned_new and last_seen and (
                item.get("last_sender_role") != "client" or upd.get(str(tid)) == item.get("updated_at")):
            upd[str(tid)] = item.get("updated_at")
            continue
        upd[str(tid)] = item.get("updated_at")
        try:
            await handle_mine(item, last_seen, first_run, tid in assigned_new)
        except (SessionExpired, Blocked):
            raise
        except Exception:
            log.exception("ticket #%s failed", tid)
            if not state["last_msg"].get(str(tid)):
                state["last_msg"][str(tid)] = -1  # повторим, только когда тикет изменится

    await mine_reminders(mine_items)
    track_auto_sent(mine_items, items)
    await poll_free(raw)
    state["initialized"] = True
    session_alerted = False
    save_state()


async def handle_mine(item: dict, last_seen: int, first_run: bool, assigned: bool = False) -> None:
    """Новые сообщения клиента в своём тикете. assigned — тикет только что назначили: одно сообщение вместо двух."""
    tid = item["id"]
    data = await ticket(tid)
    msgs = [m for m in data.get("messages", []) if not m.get("internal")]
    if not msgs:
        state["last_msg"][str(tid)] = -1
        return
    new = [m for m in msgs if m["id"] > last_seen and m.get("sender_role") == "client"]
    state["last_msg"][str(tid)] = max(m["id"] for m in msgs)
    # тикет только что взят — его сообщения уже показаны при взятии
    if last_seen == 0 and str(tid) in state.get("claimed_at", {}):
        return
    if first_run or state["paused"]:
        return
    if not new:
        if assigned:
            await send(f"🚨 <b>Тикет назначен на тебя</b>\n\n{header(item)}", tid)
        return
    body = "\n\n".join(fmt_msg(m) for m in new)
    raw_text = "\n".join(m.get("body") or "" for m in new)
    title = "🚨 <b>Тикет назначен на тебя</b>\n\n" if assigned else "💬 "
    await send(f"{title}{header(data['request'])}\n\n{body}", tid, kb=with_hints(tid, raw_text))
    if parse_checker(raw_text):
        try:
            await checker_hint(tid, raw_text)
        except Exception:
            log.exception("checker hint #%s failed", tid)
    for m in new:
        if m.get("is_image") and m.get("attachment_url"):
            try:
                img = await download(m["attachment_url"])
                sent = await bot.send_photo(OWNER_TG_ID, BufferedInputFile(img, m.get("attachment_name") or "img.jpg"),
                                            caption=f"#{tid}", reply_markup=kb_ticket(tid))
                state["tg2ticket"][str(sent.message_id)] = tid
            except Exception:
                log.warning("photo download failed for #%s", tid)


async def mine_reminders(mine_items: list[dict]) -> None:
    # напоминание: клиент ждёт ответа дольше REMIND_MIN минут
    reminded = state.setdefault("reminded", {})
    now = time.time()
    auto_only = state.setdefault("auto_only", {})  # tid -> updated_at после автоответа
    for item in mine_items:
        tid = str(item["id"])
        if item.get("last_sender_role") != "client":
            if auto_only.get(tid) == "pending":
                auto_only[tid] = item.get("updated_at")
                continue  # только что ответил автоответчик
            if auto_only.get(tid) and auto_only[tid] == item.get("updated_at"):
                continue  # последним ответил только автоответчик — клиент всё ещё ждёт
            auto_only.pop(tid, None)
            reminded.pop(tid, None)
            continue
        since = state.setdefault("waiting_since", {}).setdefault(tid, now)
        if now - since >= REMIND_MIN * 60 and reminded.get(tid) != since and not state["paused"]:
            reminded[tid] = since
            await send(f"⏱ <b>Клиент ждёт ответа {int((now - since) // 60)} мин</b>\n\n{header(item)}", item["id"])
        # автоответчик: клиент ждёт дольше RESPONDER_MIN — пишем ему, что сообщение получено
        responded = state.setdefault("responded", {})
        if (state.get("auto_reply") and now - since >= RESPONDER_MIN * 60
                and responded.get(tid) != since and not state["paused"]):
            responded[tid] = since
            text = state.get("auto_reply_text") or RESPONDER_TEXT
            try:
                await send_reply(item["id"], text)
                auto_only[tid] = "pending"
                mark_auto(item["id"], "автоответчик")
                await send(f"💬 <b>Автоответчик</b>: клиент ждал {int((now - since) // 60)} мин, отправлено:\n"
                           f"<i>{esc(text)}</i>\n\n{header(item)}", item["id"])
            except Exception as e:
                log.warning("responder #%s failed: %s", tid, e)
    for item in mine_items:  # после автоответа запоминаем новый updated_at
        if auto_only.get(str(item["id"])) == "pending" and item.get("last_sender_role") != "client":
            auto_only[str(item["id"])] = item.get("updated_at")
    for tid in list(state.get("waiting_since", {})):
        if not any(str(i["id"]) == tid and (i.get("last_sender_role") == "client" or auto_only.get(tid))
                   for i in mine_items):
            state["waiting_since"].pop(tid, None)


async def notify_free(item: dict, prio: bool, note: str = "") -> None:
    tid = item["id"]
    note = f"<i>{esc(note)}</i>\n" if note else ""
    if prio:
        await send(await short_view_full(item, f"⚡ <b>ПРИОРИТЕТНЫЙ тикет — решить первым</b>\n{note}\n"), tid, mine=False)
    elif state["notify_new"]:
        await send(await short_view_full(item, f"⚠️ <b>Клиент ждёт сотрудника</b>\n{note}\n"), tid, mine=False)


async def delayed_claim(item: dict) -> None:
    """Автовзятие через AUTO_DELAY_SEC после того, как увидели тикет."""
    try:
        if AUTO_DELAY_SEC:
            await asyncio.sleep(AUTO_DELAY_SEC)
        if state.get("auto_claim") and not state["paused"]:
            res = await auto_take(item)
            if res == "blocked":
                # кабинет запретил автоответ (429 request_blocked): не обходим, отдаём тикет мне
                now = time.time()
                blocks = [t for t in state.get("claim_blocks", []) if now - t < 3600] + [now]
                state["claim_blocks"] = blocks
                await send(await short_view_full(item, "✋ <b>Возьми вручную</b>\n<i>Кабинет не дал взять тикет "
                                                       "автоматически (429 request_blocked).</i>\n\n"), item["id"], mine=False)
                if len(blocks) >= 2:
                    state["auto_claim"] = False
                    state.pop("claim_blocks", None)
                    save_state()
                    await bot.send_message(OWNER_TG_ID, "⛔ <b>Автовзятие выключено</b>: кабинет дважды за час "
                                           "заблокировал автоответ (429 request_blocked). Включить снова — "
                                           "⚙️ Настройки → 🤖 Взятие.")
            elif res:
                log.info("auto-claim #%s ok", item["id"])
            else:
                await notify_free(item, is_priority(item), "Автоматически ответить не удалось (возможно, тикет уже взял коллега).")
        else:
            await notify_free(item, is_priority(item))
    except Exception:
        log.exception("delayed claim #%s failed", item.get("id"))
    finally:
        CLAIMING.discard(item["id"])


async def poll_free(raw: dict) -> None:
    """Свободная очередь из того же ответа: новые тикеты и автовзятие."""
    global free_initialized
    first_run = not free_initialized
    free_items = [i for i in raw.get("items", []) if is_free(i)]
    meta_prev = dict(QUEUE_META)
    QUEUE_META.update({k: raw.get(k) for k in ("stale_count", "stale_hours", "fresh_minutes", "half_rate_active")})
    for i in raw.get("items", []):
        if i.get("department"):
            state.setdefault("dept_names", {})[i["department"]] = i.get("department_name") or i["department"]

    # половинная ставка: включилась / выключилась
    hr_now, hr_prev = QUEUE_META.get("half_rate_active"), meta_prev.get("half_rate_active")
    if hr_prev is not None and hr_now != hr_prev and not state["paused"]:
        if hr_now:
            await bot.send_message(OWNER_TG_ID, f"⚠️ <b>Включилась половинная ставка</b>: старых обращений "
                                   f"{QUEUE_META.get('stale_count')} (≥30). Бери обращения старше {QUEUE_META.get('stale_hours') or 6} ч.")
        else:
            await bot.send_message(OWNER_TG_ID, f"✅ <b>Половинная ставка снята</b>: старых обращений "
                                   f"{QUEUE_META.get('stale_count')} (<30). Свежие тикеты снова по полной ставке.",
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[[Btn(text="🆓 Свободные", callback_data="m:free")]]))

    prev_free = set(state.get("free_ids", []))
    for item in free_items:
        tid = item["id"]
        prio = is_priority(item)
        if tid in CLAIMING:
            continue
        newly_free = tid not in prev_free  # появился или освободился
        if not newly_free:
            continue
        if not prio and tid in state["seen_new"]:
            continue
        if first_run or state["paused"]:
            state["seen_new"].append(tid)
            continue
        other_dept = not dept_ok(item)
        if other_dept and not prio:
            state["seen_new"].append(tid)
            log.info("free #%s: skip, отдел %s не выбран", tid, item.get("department"))
            continue
        note = "Приоритетный тикет из невыбранного отдела — автоматически не отвечал." if other_dept else ""
        if state.get("auto_claim") and not other_dept:
            # автовзятие включено — берём любой новый тикет, без лимита и при любой ставке
            CLAIMING.add(tid)
            state["seen_new"].append(tid)
            log.info("free #%s: автовзятие через %s с", tid, AUTO_DELAY_SEC)
            task = asyncio.create_task(delayed_claim(item))
            BG_TASKS.add(task)
            task.add_done_callback(BG_TASKS.discard)
            continue
        try:
            await notify_free(item, prio, note)
            state["seen_new"].append(tid)
            log.info("free #%s: уведомление (%s)", tid, note or "без автовзятия")
        except Exception:
            log.exception("free #%s: уведомление не ушло, повторю на следующем проходе", tid)
            prev_free.discard(tid)
            item["_retry"] = True
    state["free_ids"] = [i["id"] for i in free_items if not i.get("_retry")]

    free_initialized = True
    save_state()


async def poller() -> None:
    global session_alerted
    backoff, blocked_alerted = 0, False
    while True:
        try:
            await poll_once()
        except SessionExpired as e:
            log.warning("session expired: %s", e)
            if not session_alerted:
                await bot.send_message(OWNER_TG_ID, "⚠️ Сессия H1Cloud истекла. Пришли новую: <code>/cookie значение</code>")
                session_alerted = True
        except Blocked as e:
            state["fast_off_until"] = time.time() + FAST_PAUSE_SEC
            backoff = min(max(backoff * 2, 60, e.retry_after), 1800)
            log.warning("cabinet blocked us (%s), pause %s s", e, backoff)
            if not blocked_alerted:
                await bot.send_message(OWNER_TG_ID, f"⛔️ Кабинет не пускает бота ({esc(str(e))}). "
                                       f"Опрос замедлен до {backoff // 60} мин, проверь доступ.")
                blocked_alerted = True
            await asyncio.sleep(backoff)
            continue
        except httpx.TransportError as e:
            log.warning("network error, retry next cycle: %s", type(e).__name__)
        except Exception:
            log.exception("poll error")
        else:
            if blocked_alerted:
                await bot.send_message(OWNER_TG_ID, "✅ Доступ к кабинету восстановлен, опрос снова каждые "
                                       f"{POLL_SEC} с.")
            backoff, blocked_alerted = 0, False
        fast = (state.get("auto_claim") and not state.get("paused")
                and time.time() > state.get("fast_off_until", 0))
        await asyncio.sleep(POLL_FAST_SEC if fast else POLL_SEC)


# ---------- команды ----------

owner = F.from_user.id == OWNER_TG_ID


BTN_TICKETS, BTN_SEARCH, BTN_SETTINGS = "📂 Тикеты", "🔎 Поиск", "⚙️ Настройки"
BACK = Btn(text="◀️ Назад", callback_data="m:main")
search_mode: dict[str, str] = {}  # "mode": "nick" | "id"

MENUS = {
    "main": ("<b>Тикеты H1Cloud</b>\nВыбери раздел:", lambda: [
        [Btn(text=BTN_TICKETS, callback_data="m:tickets")],
        [Btn(text=BTN_SEARCH, callback_data="m:search")],
        [Btn(text=BTN_SETTINGS, callback_data="m:settings")],
    ]),
    "tickets": ("📂 <b>Тикеты</b>", lambda: [
        [Btn(text="⏳ Ждут ответа", callback_data="m:waiting"),
         Btn(text="🤖 Ответил бот", callback_data="m:auto_sent")],
        [Btn(text="📂 Все мои", callback_data="m:mine"),
         Btn(text="🆓 Свободные", callback_data="m:free")],
        [Btn(text="⚡ Приоритетные", callback_data="m:free_prio"),
         Btn(text="🕰 Старше 6 ч", callback_data="m:free_old")],
        [Btn(text="📥 Ждут поддержки", callback_data="m:wq_0")],
    ]),
    "search": ("🔎 <b>Поиск</b>\nКак ищем?", lambda: [
        [Btn(text="👤 По нику", callback_data="m:s_nick"),
         Btn(text="#️⃣ По номеру", callback_data="m:s_id")],
    ]),
    "settings": ("⚙️ <b>Настройки</b>\n✅ — включено, ❌ — выключено\n🤖 Взятие — автовзятие новых тикетов с приветствием", lambda: [
        [Btn(text="💰 Заработок", callback_data="m:earn"),
         Btn(text="🎯 Отделы: " + (f"{len(state.get('depts') or [])}" if state.get("depts") else "все"),
             callback_data="m:depts")],
        [Btn(text="🤖 Взятие " + ("✅" if state.get("auto_claim") else "❌"), callback_data="m:autoclaim"),
         Btn(text=f"💬 Автоответ {'✅' if state.get('auto_reply') else '❌'}", callback_data="m:autoreply")],
        [Btn(text="✏️ Приветствие", callback_data="m:editclaim"),
         Btn(text="✏️ Текст ответа", callback_data="m:editreply")],
        [Btn(text="🔔 Новые " + ("✅" if state["notify_new"] else "❌"), callback_data="m:togglenew"),
         Btn(text="⏸ Пауза ✅" if state["paused"] else "⏸ Пауза ❌", callback_data="m:pause")],
    ]),
}


def kb_reply() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(resize_keyboard=True, is_persistent=True, keyboard=[
        [KeyboardButton(text=BTN_TICKETS), KeyboardButton(text=BTN_SEARCH), KeyboardButton(text=BTN_SETTINGS)],
    ])


def menu(name: str) -> tuple[str, InlineKeyboardMarkup]:
    text, rows = MENUS[name]
    return text, InlineKeyboardMarkup(inline_keyboard=rows())


@dp.message(Command("start", "help", "menu"), owner)
async def cmd_menu(msg: Message) -> None:
    search_mode.clear()
    await msg.answer("Кнопки внизу всегда под рукой. Ответить клиенту — reply на сообщение тикета, "
                     "заметка — reply с <code>!</code> в начале.", reply_markup=kb_reply())
    text, kb = menu("main")
    await msg.answer(text, reply_markup=kb)


@dp.message(owner, F.text.in_({BTN_TICKETS, BTN_SEARCH, BTN_SETTINGS}))
async def on_bottom_button(msg: Message) -> None:
    search_mode.clear()
    name = {BTN_TICKETS: "tickets", BTN_SEARCH: "search", BTN_SETTINGS: "settings"}[msg.text]
    text, kb = menu(name)
    # старое меню и нажатие кнопки убираем, чтобы новое меню было последним и не пряталось под клавиатурой
    for mid in (state.pop("last_menu_mid", None), msg.message_id):
        if mid:
            try:
                await bot.delete_message(OWNER_TG_ID, mid)
            except Exception:
                pass
    sent = await msg.answer(text, reply_markup=kb)
    state["last_menu_mid"] = sent.message_id
    save_state()


async def list_mine(only_waiting: bool) -> None:
    items = await queue(mine=True)
    if only_waiting:
        items = [i for i in items if i.get("last_sender_role") == "client"]
    if not items:
        await bot.send_message(OWNER_TG_ID, "Пусто.")
        return
    rows, lines = [], []
    for i in items:
        mark = "🔴" if i.get("last_sender_role") == "client" else "⚪"
        prio = "🔥" if i.get("priority") == "high" else ""
        lines.append(f"{mark}{prio} <b>#{i['id']}</b> · {esc(i.get('client_name'))} · {esc(i.get('department_name'))}")
        rows.append(Btn(text=f"#{i['id']}", callback_data=f"open:{i['id']}"))
    kb = InlineKeyboardMarkup(inline_keyboard=[rows[k:k + 4] for k in range(0, len(rows), 4)])
    await bot.send_message(OWNER_TG_ID, "🔴 ждёт ответа · ⚪ ждём клиента\n\n" + "\n".join(lines), reply_markup=kb)


async def list_auto_sent() -> None:
    """Тикеты, где клиенту писал только бот (приветствие или автоответчик), а я ещё не отвечал."""
    sent = state.get("auto_sent", {})
    if not sent:
        await bot.send_message(OWNER_TG_ID, "🤖 Сейчас нет тикетов, где отвечал только бот.")
        return
    items = {str(i["id"]): i for i in await queue(mine=True)}
    rows, lines = [], []
    for tid, rec in sorted(sent.items(), key=lambda kv: kv[1].get("ts", 0)):
        i = items.get(tid)
        if not i:
            continue
        mins = int((time.time() - rec.get("ts", time.time())) // 60)
        ago = f"{mins} мин" if mins < 60 else f"{mins // 60} ч {mins % 60} мин"
        st = "🔴 клиент ответил" if i.get("last_sender_role") == "client" else "⚪ ждём клиента"
        lines.append(f"<b>#{tid}</b> · {esc(i.get('client_name'))} · {rec.get('kind')} {ago} назад · {st}")
        rows.append(Btn(text=f"#{tid}", callback_data=f"open:{tid}"))
    if not lines:
        await bot.send_message(OWNER_TG_ID, "🤖 Сейчас нет тикетов, где отвечал только бот.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[rows[k:k + 4] for k in range(0, len(rows), 4)])
    await bot.send_message(OWNER_TG_ID, "🤖 <b>Ответил автоматически</b> — ты ещё не писал сам:\n\n" + "\n".join(lines),
                           reply_markup=kb)


async def list_free(mode: str = "all") -> None:
    items = [i for i in await queue(mine=False) if is_free(i) and (is_priority(i) or dept_ok(i))]
    stale_h = QUEUE_META.get("stale_hours") or 6
    if mode == "prio":
        items = [i for i in items if is_priority(i)]
    elif mode == "old":
        items = [i for i in items if age_hours(i) >= stale_h]
    # приоритетные всегда сверху, дальше самые старые
    items.sort(key=lambda i: (not is_priority(i), i.get("created_at") or ""))
    meta = ""
    if QUEUE_META.get("stale_count") is not None:
        meta = (f"\n🕰 Старше {stale_h} ч: {QUEUE_META['stale_count']} · половинная ставка: "
                f"{'<b>ДА</b> (бери старые)' if QUEUE_META.get('half_rate_active') else 'нет'}")
    title = {"all": "🆓 Свободные", "prio": "⚡ Приоритетные", "old": f"🕰 Старше {stale_h} ч"}[mode]
    flt = ", ".join(state.get("dept_names", {}).get(d, d) for d in state.get("depts") or []) or "все отделы"
    await bot.send_message(OWNER_TG_ID, f"<b>{title}</b>: {len(items)} · фильтр: {esc(flt)}{meta}")
    for i in items[:8]:
        await send(await short_view_full(i, "🆓 "), i["id"], mine=False)


WQ_PAGE = 10


async def list_waiting_queue(page: int = 0, edit: Message | None = None) -> None:
    """Очередь «Ждут ответа поддержки»: свободные тикеты, где последним писал клиент. Самые старые сверху."""
    all_items = await queue(mine=False)
    waiting = [i for i in all_items if i.get("last_sender_role") == "client"]
    items = [i for i in waiting if is_free(i) and (is_priority(i) or dept_ok(i))]
    esc_n = sum(1 for i in waiting if i.get("status") == "escalated" and not i.get("assigned_to"))
    items.sort(key=lambda i: (not is_priority(i), i.get("created_at") or ""))
    pages = max(1, -(-len(items) // WQ_PAGE))
    page = max(0, min(page, pages - 1))
    chunk = items[page * WQ_PAGE:(page + 1) * WQ_PAGE]
    lines = []
    for i in chunk:
        h = age_hours(i)
        age = f"{int(h * 60)} мин" if h < 1 else (f"{int(h)} ч" if h < 48 else f"{int(h // 24)} д")
        lines.append(f"{'🔥' if is_priority(i) else '▫️'} <b>#{i['id']}</b> · {esc(i.get('client_name'))} · "
                     f"{esc(i.get('department_name'))} · {age}")
    text = (f"📥 <b>Ждут ответа поддержки</b>: {len(waiting)} в кабинете\n"
            f"Свободных для тебя: <b>{len(items)}</b> · у старших: {esc_n}\n"
            f"Стр. {page + 1}/{pages}, сначала приоритетные и самые старые\n\n" + ("\n".join(lines) or "Пусто 🎉"))
    rows = [[Btn(text=f"#{i['id']}", callback_data=f"fv:{i['id']}") for i in chunk[k:k + 5]] for k in (0, 5)]
    rows = [r for r in rows if r]
    nav = []
    if page > 0:
        nav.append(Btn(text="◀️", callback_data=f"m:wq_{page - 1}"))
    nav.append(Btn(text="🔄", callback_data=f"m:wq_{page}"))
    if page < pages - 1:
        nav.append(Btn(text="▶️", callback_data=f"m:wq_{page + 1}"))
    rows.append(nav)
    kb = InlineKeyboardMarkup(inline_keyboard=rows)
    if edit:
        try:
            await edit.edit_text(text, reply_markup=kb)
            return
        except Exception:
            pass
    await bot.send_message(OWNER_TG_ID, text, reply_markup=kb)


def kb_depts() -> InlineKeyboardMarkup:
    chosen = set(state.get("depts") or [])
    names = state.get("dept_names", {})
    rows = [[Btn(text=("✅ " if d in chosen else "▫️ ") + n, callback_data=f"m:dept_{d}")] for d, n in names.items()]
    rows.append([Btn(text="♻️ Все отделы", callback_data="m:dept__all")])
    rows.append([Btn(text="◀️ Назад", callback_data="m:settings")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


@dp.message(Command("cookie"), owner)
async def cmd_cookie(m: Message) -> None:
    """Новая cookie кабинета прямо из Telegram: /cookie <значение>. Сообщение с ней сразу удаляем."""
    global session_alerted
    val = (m.text or "").split(maxsplit=1)[1].strip() if len((m.text or "").split(maxsplit=1)) > 1 else ""
    try:
        await m.delete()
    except Exception:
        pass
    if not val or "\n" in val:
        await bot.send_message(OWNER_TG_ID, "Формат: <code>/cookie значение_cookie</code> (одной строкой, как в заголовке Cookie).")
        return
    old_val = h1.headers.get("Cookie")
    h1.headers["Cookie"] = val
    try:
        await queue_raw(mine=False)
    except SessionExpired:
        h1.headers["Cookie"] = old_val
        await bot.send_message(OWNER_TG_ID, "❌ Кабинет не принял эту cookie (401). Старая оставлена.")
        return
    except Exception as e:
        log.warning("cookie check: %s", e)
    env = Path(__file__).with_name(".env")
    lines = env.read_text().splitlines() if env.exists() else []
    lines = [l for l in lines if not l.startswith("H1_COOKIE=")] + [f"H1_COOKIE={val}"]
    env.write_text("\n".join(lines) + "\n")
    session_alerted = False
    await bot.send_message(OWNER_TG_ID, "✅ Cookie обновлена, кабинет отвечает. Сообщение с ней удалено.")


@dp.message(Command("mine"), owner)
async def cmd_mine(msg: Message) -> None:
    await list_mine(False)


@dp.message(Command("wait"), owner)
async def cmd_wait(msg: Message) -> None:
    await list_mine(True)


@dp.message(Command("free"), owner)
async def cmd_free(msg: Message) -> None:
    await list_free()


async def show_ticket(tid: int, limit: int = 10) -> None:
    data = await ticket(tid)
    msgs = data.get("messages", [])[-limit:]
    parts = []
    for m in msgs:
        who = {"client": "👤", "staff": "🧑‍💻", "system": "⚙️"}.get(m.get("sender_role"), "•")
        note = " <i>(заметка)</i>" if m.get("internal") else ""
        parts.append(f"{who} <b>{esc(m.get('sender_name'))}</b>{note} · {esc((m.get('created_at') or '')[5:16])}\n{fmt_msg(m)}")
    req = data["request"]
    mine = bool(req.get("assigned_to"))
    await send(header(req) + "\n\n" + "\n\n".join(parts), tid, mine=mine)


async def search_tickets(query: str) -> None:
    q = query.strip().lstrip("@#").lower()
    if len(q) < 2:
        await bot.send_message(OWNER_TG_ID, "Слишком короткий запрос, нужно хотя бы 2 символа.")
        return
    found: dict[int, dict] = {}
    for params in ("status=open", "status=open&mine=1", "status=escalated"):
        for i in (await api("GET", f"/api/staff/desk/queue?{params}")).get("items", []):
            hay = " ".join(str(i.get(k) or "") for k in ("client_name", "user_tgid", "id", "subject", "preview")).lower()
            if q in hay:
                found[i["id"]] = i
    if not found:
        await bot.send_message(OWNER_TG_ID, f"По «{esc(query)}» среди открытых тикетов ничего нет.")
        return
    items = sorted(found.values(), key=lambda i: i.get("created_at") or "")[:10]
    await bot.send_message(OWNER_TG_ID, f"🔎 Найдено: {len(found)}" + (" (показаны первые 10)" if len(found) > 10 else ""))
    for i in items:
        if i.get("assigned_to"):
            who = f"👤 взял: {esc(i.get('assigned_name') or i.get('assigned_to'))}"
            kb = InlineKeyboardMarkup(inline_keyboard=[[Btn(text="📜 Открыть", callback_data=f"open:{i['id']}")]])
        else:
            who = "🆓 свободен"
            kb = kb_ticket(i["id"], mine=False)
        await send(f"{who}\n{await short_view_full(i)}", i["id"], kb=kb)


@dp.message(Command("find"), owner)
async def cmd_find(msg: Message) -> None:
    arg = (msg.text or "").split(maxsplit=1)
    if len(arg) < 2:
        await msg.answer("Формат: /find ник (или часть ника, номер, слово из тикета)")
        return
    await search_tickets(arg[1])


@dp.message(Command("t"), owner)
async def cmd_ticket(msg: Message) -> None:
    arg = (msg.text or "").split(maxsplit=1)
    if len(arg) < 2 or not arg[1].strip().lstrip("#").isdigit():
        await msg.answer("Формат: /t 12345")
        return
    await show_ticket(int(arg[1].strip().lstrip("#")))


# ---------- кнопки ----------

async def show_servers(tid: int) -> None:
    data = await api("GET", f"/api/staff/desk/requests/{tid}/client-servers")
    c = data.get("client") or {}
    head = (f"👤 <b>{esc(c.get('username'))}</b> · баланс {c.get('balance', 0):.2f} ₽"
            f"{' · 🚫 бан' if c.get('banned') else ''}\nбыл: {esc(c.get('last_login'))}")
    servers = data.get("servers") or []
    if not servers:
        await bot.send_message(OWNER_TG_ID, head + "\n\nСерверов нет (VPS здесь не видны).")
        return
    await bot.send_message(OWNER_TG_ID, head)
    for s in servers:
        panel = "3x-ui" if s.get("xui_enabled") else "Remnawave Node" if s.get("remnanode_enabled") else "H1/другое"
        lte = f"\nLTE: {esc(s.get('vpn_bs_plan_name') or s.get('vpn_bs_gb'))}" if s.get("vpn_bs_enabled") else ""
        err = f"\n⚠️ {esc(s.get('vpn_bs_setup_error'))}" if s.get("vpn_bs_setup_error") else ""
        text = (f"🖥 <b>{esc(s.get('name'))}</b> #{s['id']} · {esc(s.get('status'))}\n"
                f"{esc(s.get('tariff_name'))}\n📍 {esc(s.get('location_name'))} · {panel}\n"
                f"осталось {s.get('days_left')} дн. · до {esc((s.get('expiration_date') or '')[:10])}{lte}{err}")
        kb = InlineKeyboardMarkup(inline_keyboard=[[
            Btn(text="🔑 Доступ в панель", callback_data=f"pacc:{s['id']}"),
            Btn(text="🔄 Рестарт", callback_data=f"pwr:{s['id']}:restart"),
        ], [
            Btn(text="▶️ Старт", callback_data=f"pwr:{s['id']}:start"),
            Btn(text="⏹ Стоп", callback_data=f"pwr:{s['id']}:stop"),
        ]])
        await bot.send_message(OWNER_TG_ID, text, reply_markup=kb)


GEMINI_KEY = os.getenv("GEMINI_API_KEY", "")
TONWAVE_KEY = os.getenv("TONWAVE_API_KEY", "")
TONWAVE_URL = os.getenv("TONWAVE_URL", "https://api.tonwave.dev/v1/messages")
TONWAVE_MODEL = os.getenv("TONWAVE_MODEL", "claude-haiku-4-5")
MANUAL_BUDGET = int(os.getenv("MANUAL_BUDGET", "30000"))  # символов мануала в один разбор
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GEMINI_FALLBACKS = ["gemini-3.8-flash", "gemini-flash-latest", "gemini-3.5-flash", "gemini-3.5-flash-lite"]
GEMINI_OUT: dict[str, float] = {}  # модель -> до какого времени её лимит исчерпан (бесплатно 20 запросов в сутки)
MANUAL = Path(os.getenv("MANUAL_FILE", "manual.md"))

ANALYZE_RULES = """Ты помощник сотрудника первой линии поддержки хостинга H1Cloud.
По переписке тикета и данным клиента подготовь разбор и готовый ответ клиенту.

Жёсткие правила:
- Опирайся ТОЛЬКО на мануал ниже. Не выдумывай цены, сроки, лимиты, причины сбоев, функции, команды.
- Если решение есть в мануале (раздел «Типовые случаи», «Из каналов», «Практика…», готовые шаблоны, ответы старших) — отвечай клиенту по существу сам, need_senior=false. Пункт 1.3 про обязательный чат со старшим считай выполненным, если ответ на этот случай уже записан в мануале.
- СОТРУДНИК РЯДОМ: у сотрудника есть доступ к серверу и панели клиента (консоль, h1panel, VPN-панель на 1 час через карточку тикета). Если не уверен в факте, который сотрудник может проверить сам (какая панель и версия, есть ли поле/кнопка, что в консоли, какие порты, работает ли функция на этом сервере), — НЕ отправляй старшему: задай сотруднику короткий вопрос в поле ask_operator (что именно открыть и посмотреть) и поставь need_senior=false. Клиенту в этом случае дай путь/шаги, которые уже известны. Факты в блоке «ПРОВЕРЕНО СОТРУДНИКОМ» — проверенные, доверяй им больше, чем документации.
- need_senior=true только если: нужна проверка или действие администратора (начисление денег, не зачислился платёж, ручной перенос по просьбе, смена IP при бане сразу после выдачи, проверка ноды без видимой причины, возврат денег, блокировка аккаунта или abuse), или в мануале нет ответа на вопрос клиента. Тогда коротко сообщение старшему, а клиенту ответь на всё, что можешь подтвердить, и только по остальному — «уточним и вернёмся в течение 30 минут».
- Ответ клиенту: от имени хостинга («мы»), на «вы», без эмодзи, без жаргона, коротко и по делу, на все вопросы клиента.
- Приветствие «Здравствуйте.» только если сотрудник ещё не отвечал в тикете.
- Никогда не проси пароли, ключи, токены, данные карт. Не признавай вину хостинга без подтверждения. Не обещай сроки решения.
- Не повторяй то, что клиенту уже ответили.
- Отвечай на НОВЫЕ сообщения клиента (блок «НОВЫЕ СООБЩЕНИЯ КЛИЕНТА» — всё, что он написал после последнего ответа сотрудника). Предыдущая переписка — только контекст: не возвращайся к уже решённым вопросам и не поднимай темы, о которых клиент сейчас не спрашивает.

МАНУАЛ:
"""

ANALYZE_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "department": {"type": "STRING", "description": "отдел: abuse/billing/general/technical/vps"},
        "diagnosis": {"type": "STRING", "description": "суть проблемы и вероятная причина, 1-2 предложения"},
        "manual_basis": {"type": "STRING", "description": "на какой раздел мануала опирается ответ, или 'нет в мануале'"},
        "need_senior": {"type": "BOOLEAN"},
        "senior_message": {"type": "STRING", "description": "короткое сообщение старшему в чат, если need_senior"},
        "ask_operator": {"type": "STRING", "description": "вопрос сотруднику: что проверить у клиента самому (панель, версия, поле, консоль); пусто, если не нужно"},
        "customer_reply": {"type": "STRING", "description": "готовый текст ответа клиенту"},
    },
    "required": ["department", "diagnosis", "manual_basis", "need_senior", "customer_reply"],
}


# ---------- выбор нужных разделов мануала ----------

ALWAYS = ("главный принцип", "01. правила", "03. тон", "04. структура", "05. сроки", "07. безопасность", "09. запрещено")
SKIP = ("00. регламент",)


def manual_chunks() -> list[tuple[str, str]]:
    """Мануал на куски: разделы ## / ### и жирные подзаголовки **…** внутри больших разделов."""
    text = MANUAL.read_text() if MANUAL.exists() else ""
    chunks, title, sub, buf = [], "", "", []

    def flush():
        if buf and "".join(buf).strip():
            chunks.append((title + (f" / {sub}" if sub else ""), "\n".join(buf)))
        buf.clear()

    for line in text.split("\n"):
        if line.startswith("## "):
            flush(); title, sub = line[3:].strip(), ""
        elif line.startswith("### ") or (line.startswith("**") and line.rstrip().endswith("**") and len(line) < 120):
            flush(); sub = line.strip("#* ").strip()
        buf.append(line)
    flush()
    return chunks


def stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-zа-яё0-9]{4,}", text.lower())}


def manual_blocks() -> list[tuple[str, str]]:
    """Мануал на пункты: каждый абзац/пункт списка с вложенными строками, с названием раздела."""
    text = MANUAL.read_text() if MANUAL.exists() else ""
    blocks: list[list] = []
    title = sub = ""
    for line in text.split("\n"):
        if line.startswith("## "):
            title, sub = line[3:].strip(), ""
            continue
        if line.startswith("### "):
            sub = line[4:].strip()
            continue
        if not line.strip():
            continue
        head = title + (f" / {sub}" if sub else "")
        if line.startswith((" ", "\t", "|")) and blocks and blocks[-1][0] == head:
            blocks[-1][1].append(line)
            continue
        blocks.append([head, [line]])
    return [(h, "\n".join(ls)) for h, ls in blocks]


def pick_manual(ticket_text: str, budget: int = MANUAL_BUDGET) -> str:
    """Основные правила целиком + пункты мануала, ближе всего к тикету (редкие слова весят больше)."""
    core = [c for c in manual_chunks() if c[0].lower().startswith(ALWAYS)]
    size = sum(len(c[1]) for c in core)
    blocks = [b for b in manual_blocks()
              if not b[0].lower().startswith(ALWAYS) and not b[0].lower().startswith(SKIP)]
    docs = [stems(h + " " + t) for h, t in blocks]
    df: dict[str, int] = {}
    for d in docs:
        for w in d:
            df[w] = df.get(w, 0) + 1
    n = len(blocks) or 1
    want = stems(ticket_text)
    score = [sum(math.log(n / df[w]) for w in want & d) for d in docs]
    chosen = set()
    for i in sorted(range(len(blocks)), key=lambda i: -score[i]):
        if score[i] <= 0 or size + len(blocks[i][1]) > budget:
            continue
        chosen.add(i)
        size += len(blocks[i][1])
    out, last = [c[1] for c in core], None
    for i in sorted(chosen):  # в порядке мануала, с заголовками разделов
        if blocks[i][0] != last:
            out.append(f"\n## {blocks[i][0]}")
            last = blocks[i][0]
        out.append(blocks[i][1])
    return "\n".join(out)


async def analysis_input(tid: int) -> str:
    data = await ticket(tid)
    try:
        cs = await api("GET", f"/api/staff/desk/requests/{tid}/client-servers")
    except Exception:
        cs = {}
    req = data["request"]
    convo = []
    for m in data.get("messages", []):
        role = {"client": "КЛИЕНТ", "staff": "СОТРУДНИК", "system": "СИСТЕМА"}.get(m.get("sender_role"), "?")
        if m.get("internal"):
            role += " (внутренняя заметка)"
        if m.get("is_ai"):
            role = "ИИ-АССИСТЕНТ"
        convo.append(f"[{(m.get('created_at') or '')[:16]}] {role}: {m.get('body') or ''}"
                     + (" [вложение]" if m.get("attachment_url") else ""))
    c = cs.get("client") or {}
    servers = [f"#{s.get('id')} {s.get('name')} · {s.get('tariff_name')} · {s.get('location_name')} · "
               f"{s.get('status')} · осталось {s.get('days_left')} дн. · панель "
               f"{'3x-ui' if s.get('xui_enabled') else 'Remnawave Node' if s.get('remnanode_enabled') else 'H1/другое'}"
               + (f" · LTE {s.get('vpn_bs_gb')} ГБ" if s.get("vpn_bs_enabled") else "")
               for s in cs.get("servers") or []]
    msgs = data.get("messages", [])
    last_staff = max((i for i, m in enumerate(msgs)
                      if m.get("sender_role") == "staff" and not m.get("internal")), default=-1)
    fresh = [f"[{(m.get('created_at') or '')[:16]}] КЛИЕНТ: {m.get('body') or ''}"
             + (" [вложение]" if m.get("attachment_url") else "")
             for m in msgs[last_staff + 1:] if m.get("sender_role") == "client"]
    user_text = (f"Тикет #{tid}, отдел: {req.get('department_name')}, тема: {req.get('subject')}\n"
                 f"Баланс клиента {c.get('balance')} ₽\n"
                 f"Серверы клиента: {'; '.join(servers) or 'нет (VPS в карточке не видны)'}\n\n"
                 "ПРЕДЫДУЩАЯ ПЕРЕПИСКА (контекст):\n" + "\n".join(convo))
    facts = OPERATOR_FACTS.get(tid)
    if facts:
        user_text += "\n\nПРОВЕРЕНО СОТРУДНИКОМ (точные факты):\n" + "\n".join(f"- {f}" for f in facts)
    if fresh:
        user_text += f"\n\n{FRESH_MARK}\n" + "\n".join(fresh)
    return user_text


FRESH_MARK = "НОВЫЕ СООБЩЕНИЯ КЛИЕНТА (ответить на них):"
OPERATOR_FACTS: dict[int, list[str]] = {}  # tid -> что сотрудник проверил сам (ответ на вопрос разбора)


def focus_text(user_text: str) -> str:
    """Текст для подбора мануала: тема + новые сообщения клиента, если они есть."""
    if FRESH_MARK in user_text:
        return user_text.split("\n", 1)[0] + "\n" + user_text.split(FRESH_MARK, 1)[1]
    return user_text


async def claude_analyze(user_text: str) -> dict:
    """Разбор через Claude Haiku (TonWave): только нужные разделы мануала, ответ строго по схеме."""
    schema = json.loads(json.dumps(ANALYZE_SCHEMA).replace('"OBJECT"', '"object"').replace('"STRING"', '"string"')
                        .replace('"BOOLEAN"', '"boolean"'))
    body = {
        "model": TONWAVE_MODEL,
        "max_tokens": 4000,
        "system": ANALYZE_RULES + pick_manual(focus_text(user_text)),
        "tools": [{"name": "analysis", "description": "Разбор тикета и ответ клиенту", "input_schema": schema}],
        "tool_choice": {"type": "tool", "name": "analysis"},
        "messages": [{"role": "user", "content": user_text}],
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(90, connect=10)) as c:
        r = await c.post(TONWAVE_URL, json=body, headers={"x-api-key": TONWAVE_KEY, "anthropic-version": "2023-06-01"})
    if r.status_code >= 400:
        raise RuntimeError(f"TonWave {r.status_code}: {r.text[:200]}")
    d = r.json()
    u = d.get("usage") or {}
    log.info("claude analysis: in %s, out %s tokens", u.get("input_tokens"), u.get("output_tokens"))
    block = next((b for b in d.get("content", []) if b.get("type") == "tool_use"), None)
    data = block.get("input") if block else None
    if isinstance(data, str):  # некоторые прокси отдают аргументы строкой
        try:
            data = json.loads(data)
        except ValueError:
            data = None
    if not isinstance(data, dict) or not (data.get("customer_reply") or "").strip():
        raise RuntimeError(f"Claude вернул пустой разбор (вышло {u.get('output_tokens')} токенов, "
                           f"стоп: {d.get('stop_reason')})")
    return data


KB_DIR = Path(os.getenv("KB_DIR", "kb"))
WEB_RULES = """Ты помощник сотрудника первой линии поддержки хостинга H1Cloud. Первичный разбор по мануалу H1Cloud не нашёл ответа.
Найди решение для клиента так:
1) мануал H1Cloud ниже (главный источник, его ограничения важнее всего остального);
2) документация панелей ниже (3x-ui — docs.sanaei.dev, Remnawave — docs.rw, гайд VLESS);
3) если там нет — поиск в интернете (web_search), не больше 3 запросов.
Особенности H1Cloud важнее любой документации: на VPN-тарифах нет SSH/root и доступа к файлам; порты — только выделенные (вкладка «Сеть»), 443/80 на обычных инбаундах нет; панель на купленном сервере не меняется; ядро Xray меняется только кнопкой «Поменять версию Xray» в кабинете. Цены, сроки, возвраты, компенсации, блокировки аккаунта и правила H1Cloud в интернете не ищи — по ним need_senior=true.
Вопросы «как настроить / где найти / как сделать» в панели (3x-ui, Remnawave, H1) — отвечай сам по документации: конкретный путь в интерфейсе (меню → раздел → поле) и шаги, need_senior=false. Не отправляй такие вопросы старшему только потому, что не уверен в мелочи (версия панели, работает ли функция на нашем сервере): дай путь и одной фразой предупреди о нюансе («если поля нет / не сработает — напишите, проверим»). need_senior=true только когда нужно действие администратора, деньги, блокировка или ответа нет ни в мануале, ни в документации.
СОТРУДНИК РЯДОМ: у сотрудника есть доступ к серверу и панели клиента (консоль, h1panel, VPN-панель на 1 час через карточку тикета). Если не уверен в факте, который сотрудник может проверить сам (какая панель и версия, есть ли поле/кнопка, что в консоли, какие порты, работает ли функция на этом сервере), — НЕ отправляй старшему: задай сотруднику короткий вопрос в поле ask_operator (что именно открыть и посмотреть) и поставь need_senior=false. Клиенту в этом случае дай путь/шаги, которые уже известны. Факты в блоке «ПРОВЕРЕНО СОТРУДНИКОМ» — проверенные, доверяй им больше, чем документации.
Если нашёл решение, применимое у нас, — need_senior=false, в manual_basis укажи источник (URL или «документация 3x-ui/Remnawave»). Если не нашёл или нужно действие администратора — need_senior=true и короткое senior_message.
Решай вопрос из блока «НОВЫЕ СООБЩЕНИЯ КЛИЕНТА», остальная переписка — контекст.
Ответ клиенту: по-русски, на «вы», от имени хостинга, без эмодзи, по шагам, с путями в интерфейсе панели, без markdown (никаких ** и #), названия кнопок в «кавычках».
Верни ТОЛЬКО JSON-объект без пояснений: {"department": "...", "diagnosis": "...", "manual_basis": "...", "need_senior": true/false, "senior_message": "...", "ask_operator": "... или пусто", "customer_reply": "..."}
"""


def kb_chunks() -> list[tuple[str, str]]:
    chunks = []
    for f in sorted(KB_DIR.glob("*.md")) if KB_DIR.exists() else []:
        src, title, buf = "", "", []
        for line in f.read_text().split("\n"):
            if line.startswith("=== SOURCE:") or line.startswith("## "):
                if buf and "".join(buf).strip():
                    chunks.append((src + " " + title, "\n".join(buf)))
                buf = []
                if line.startswith("=== SOURCE:"):
                    src, title = line[11:].strip(), ""
                    continue
                title = line[3:].strip()
            buf.append(line)
        if buf:
            chunks.append((src + " " + title, "\n".join(buf)))
    return chunks


def pick_kb(ticket_text: str, budget: int = 16000) -> str:
    want = stems(ticket_text)
    scored = sorted(kb_chunks(), key=lambda c: -(len(want & stems(c[0] + " " + c[1])) / (len(c[1]) ** 0.3 + 1)))
    out, size = [], 0
    for src, body in scored:
        if size + len(body) > budget:
            continue
        out.append(f"[{src.split()[0] if src else ''}]\n{body[:4000]}")
        size += min(len(body), 4000)
    return "\n\n".join(out)


async def claude_web_analyze(user_text: str, first: dict) -> dict:
    body = {
        "model": TONWAVE_MODEL,
        "max_tokens": 4000,
        "system": WEB_RULES + "\n\nМАНУАЛ H1CLOUD:\n" + pick_manual(focus_text(user_text), 18000)
                  + "\n\nДОКУМЕНТАЦИЯ ПАНЕЛЕЙ:\n" + pick_kb(focus_text(user_text)),
        "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 3}],
        "messages": [{"role": "user", "content": user_text + "\n\nПервичный разбор по мануалу: "
                      + (first.get("diagnosis") or "") + "\nЧто хотели спросить у старшего: "
                      + (first.get("senior_message") or "")}],
    }
    async with httpx.AsyncClient(timeout=httpx.Timeout(150, connect=10)) as c:
        r = await c.post(TONWAVE_URL, json=body, headers={"x-api-key": TONWAVE_KEY, "anthropic-version": "2023-06-01"})
    if r.status_code >= 400:
        raise RuntimeError(f"TonWave {r.status_code}: {r.text[:200]}")
    d = r.json()
    u = d.get("usage") or {}
    log.info("web analysis: in %s, out %s, searches %s", u.get("input_tokens"), u.get("output_tokens"),
             (u.get("server_tool_use") or {}).get("web_search_requests"))
    text = "".join(b.get("text", "") for b in d.get("content", []) if b.get("type") == "text")
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0)) if m else None
    if not isinstance(data, dict) or not (data.get("customer_reply") or "").strip():
        raise RuntimeError("пустой ответ второго этапа")
    data["_web"] = True
    return data


# модель иногда вставляет посреди русского текста токены другого языка (китайские, японские, корейские)
FOREIGN_RE = re.compile(r"[\u3040-\u30ff\u3400-\u4dbf\u4e00-\u9fff\uac00-\ud7af\uf900-\ufaff]+")
TEXT_FIELDS = ("diagnosis", "manual_basis", "senior_message", "ask_operator", "customer_reply")


def has_foreign(data: dict) -> bool:
    return any(FOREIGN_RE.search(str(data.get(k) or "")) for k in TEXT_FIELDS)


def strip_foreign(data: dict) -> dict:
    for k in TEXT_FIELDS:
        if data.get(k):
            data[k] = re.sub(r"  +", " ", FOREIGN_RE.sub("", str(data[k])))
    return data


async def analyze(tid: int, on_web=None) -> dict:
    res = await _analyze(tid, on_web)
    if has_foreign(res):
        log.warning("analysis #%s: иностранные символы в ответе, повторяю", tid)
        try:
            again = await _analyze(tid, None)
            if not has_foreign(again):
                return again
            res = again
        except Exception as e:
            log.warning("retry after foreign chars failed: %r", e)
        res = strip_foreign(res)
        res["diagnosis"] = "⚠️ Модель вставила в текст символы другого языка, они вырезаны — перечитай ответ. " + (res.get("diagnosis") or "")
    return res


async def _analyze(tid: int, on_web=None) -> dict:
    user_text = await analysis_input(tid)
    if TONWAVE_KEY:
        try:
            first = await claude_analyze(user_text)
            if first.get("need_senior") or (first.get("ask_operator") or "").strip():
                try:  # мануал не помог — ищем в документации панелей и в интернете
                    if on_web:
                        await on_web()
                    return await claude_web_analyze(user_text, first)
                except Exception as e:
                    log.warning("web analysis failed, keep manual result: %r", e)
            return first
        except Exception as e:
            log.warning("claude analysis failed, fallback to gemini: %r", e)
            if not GEMINI_KEY:
                raise
    return await gemini_analyze(user_text)


async def gemini_analyze(user_text: str) -> dict:
    body = {
        "systemInstruction": {"parts": [{"text": ANALYZE_RULES + pick_manual(focus_text(user_text), 80000)}]},
        "contents": [{"role": "user", "parts": [{"text": user_text}]}],
        "generationConfig": {"responseMimeType": "application/json", "responseSchema": ANALYZE_SCHEMA},
    }
    models = [GEMINI_MODEL] + [m for m in GEMINI_FALLBACKS if m != GEMINI_MODEL]
    tried = []
    async with httpx.AsyncClient(timeout=httpx.Timeout(45, connect=10)) as g:
        for model in models:
            if GEMINI_OUT.get(model, 0) > time.time():
                tried.append(f"{model}: лимит на сегодня исчерпан")
                continue
            try:
                r = await g.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                                 headers={"x-goog-api-key": GEMINI_KEY}, json=body)
            except httpx.TimeoutException:
                tried.append(f"{model}: не ответила за 45 с")
                log.warning("gemini %s -> timeout", model)
                continue
            if r.status_code == 429:
                err = r.text
                if "PerDay" in err:  # дневной лимит — не дёргаем модель до сброса
                    m = re.search(r'"retryDelay":\s*"(\d+)s"', err)
                    GEMINI_OUT[model] = time.time() + (int(m.group(1)) if m else 3600)
                    tried.append(f"{model}: лимит на сегодня исчерпан")
                else:
                    tried.append(f"{model}: лимит в минуту")
                log.warning("gemini %s -> 429", model)
                continue
            if r.status_code in (500, 503, 404):  # перегрузка или нет модели — пробуем следующую
                tried.append(f"{model}: {'перегружена' if r.status_code == 503 else r.status_code}")
                log.warning("gemini %s -> %s", model, r.status_code)
                continue
            if r.status_code >= 400:
                raise RuntimeError(f"Gemini {r.status_code}: {r.text[:200]}")
            break
        else:
            raise RuntimeError("все бесплатные модели недоступны:\n" + "\n".join(tried))
    parts = r.json()["candidates"][0]["content"]["parts"]
    return json.loads("".join(p.get("text", "") for p in parts if not p.get("thought")))


async def show_analysis(tid: int) -> None:
    if not GEMINI_KEY and not TONWAVE_KEY:
        await bot.send_message(OWNER_TG_ID, "Нет TONWAVE_API_KEY или GEMINI_API_KEY в .env")
        return
    wait = await bot.send_message(OWNER_TG_ID, f"🧠 Разбираю #{tid} по мануалу…")
    running = state.setdefault("analysis_running", {})
    running[str(wait.message_id)] = tid  # если бот перезапустится — сообщим, что разбор прерван
    save_state()
    try:
        async def on_web():
            try:
                await wait.edit_text(f"🧠 #{tid}: в мануале ответа нет — ищу в документации панелей и в интернете (до минуты)…")
            except Exception:
                pass
        a = await analyze(tid, on_web)
    except Exception as e:
        log.warning("analysis #%s failed: %r", tid, e)
        await wait.edit_text(f"🧠 #{tid}: не получилось — {esc(str(e) or type(e).__name__)}")
        return
    finally:
        running.pop(str(wait.message_id), None)
        save_state()
    reply = (a.get("customer_reply") or "").strip()
    drafts[tid] = reply
    lines = [f"🧠 <b>Разбор #{tid}</b>" + ("\n🌐 <i>В мануале ответа не было — найдено в документации панелей / интернете. Проверь особенно внимательно.</i>" if a.get("_web") else ""),
             f"🎯 {esc(a.get('department'))}",
             f"🔍 {esc(a.get('diagnosis'))}",
             f"📖 {esc(a.get('manual_basis'))}"]
    if (a.get("ask_operator") or "").strip():
        lines.append(f"\n❓ <b>Проверь сам:</b>\n{esc(a.get('ask_operator'))}\n"
                     "<i>Ответь reply-ем на этот разбор, начав с «?» — пересоберу разбор с твоими данными.</i>")
    if a.get("need_senior"):
        lines.append(f"\n⬆️ <b>Старшему:</b>\n<code>{esc(a.get('senior_message'))}</code>")
    lines.append(f"\n✉️ <b>Ответ клиенту:</b>\n{esc(reply)}\n\n<i>Проверь перед отправкой. Можно ответить reply-ем со своей правкой.</i>")
    await wait.delete()
    await send("\n".join(lines), tid, kb=kb_draft(tid))


async def show_ai(tid: int) -> None:
    await bot.send_message(OWNER_TG_ID, f"🤖 Готовлю подсказку по #{tid}…")
    d = await act(tid, "ai-suggest")
    reply = (d.get("reply") or "").strip()
    if not reply:
        await bot.send_message(OWNER_TG_ID, "ИИ ничего не предложил.")
        return
    drafts[tid] = reply
    warn = "" if d.get("confident", True) else f"⚠️ ИИ не уверен ({esc(d.get('reason') or 'нет данных')}). Это совет, а не готовый ответ.\n\n"
    opts = d.get("options") or []
    extra = ("\n\n<b>Варианты:</b>\n" + "\n".join(f"• {esc(o)}" for o in opts)) if opts else ""
    await send(f"🤖 <b>#{tid}</b>\n{warn}{esc(reply)}{extra}\n\n<i>Можно ответить reply-ем со своей правкой.</i>",
               tid, kb=kb_draft(tid))


async def show_templates(tid: int) -> None:
    tpls = (await api("GET", "/api/staff/desk/templates")).get("templates", [])
    if not tpls:
        await bot.send_message(OWNER_TG_ID, "Шаблонов нет.")
        return
    rows = [[Btn(text=t["title"][:40], callback_data=f"tpl:{tid}:{t['id']}")] for t in tpls[:20]]
    await bot.send_message(OWNER_TG_ID, f"📋 Шаблоны для #{tid}:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))


async def handle_menu(cb: CallbackQuery, what: str) -> None:
    if what == "mine":
        await list_mine(False)
    elif what == "waiting":
        await list_mine(True)
    elif what == "auto_sent":
        await list_auto_sent()
    elif what == "free_prio":
        await list_free("prio")
    elif what == "free_old":
        await list_free("old")
    elif what == "depts":
        if not state.get("dept_names"):
            await bot.send_message(OWNER_TG_ID, "Список отделов появится после первого опроса очереди (до 30 сек).")
            return
        await cb.message.edit_text("🎯 <b>Какие отделы присылать</b>\nПриоритетные тикеты приходят из любых отделов.",
                                   reply_markup=kb_depts())
    elif what.startswith("dept_"):
        code = what[5:]
        if code == "_all":
            state["depts"] = []
        else:
            cur = set(state.get("depts") or [])
            cur ^= {code}
            state["depts"] = sorted(cur)
        save_state()
        await cb.message.edit_reply_markup(reply_markup=kb_depts())
    elif what == "free":
        await list_free()
    elif what.startswith("wq_"):
        await list_waiting_queue(int(what[3:]), edit=cb.message if cb.message.text and cb.message.text.startswith("📥") else None)
    elif what == "earn":
        e = await api("GET", "/api/staff/support/earnings")
        sync_closed(e)
        s, st, cfg = e.get("summary") or {}, e.get("stats") or {}, e.get("config") or {}

        def rub(v) -> str:
            return f"{float(v or 0):,.2f} ₽".replace(",", " ")

        lines = [
            "💰 <b>Заработок</b>",
            f"Доступно к выводу: <b>{rub(s.get('available'))}</b>",
            f"Ожидает начисления: {rub(s.get('pending'))}",
            f"Выплачено: {rub(s.get('paid'))}",
            "",
            "📊 <b>Статистика</b>",
            f"Решено обращений: <b>{st.get('resolved') or s.get('resolved') or 0}</b>",
            f"Оценки: 👍 {st.get('csat_up') or 0} · 👎 {st.get('csat_down') or 0}"
            + (f" · {st.get('csat_pct')}% довольных" if st.get("csat_pct") is not None else ""),
            f"Переоткрытий: {st.get('reopens') or 0}",
        ]
        lines += closed_stats_lines()
        board = e.get("leaderboard") or []
        me = next((n for n, r in enumerate(board, 1)
                   if r.get("tgid") == OWNER_TG_ID or r.get("is_me") or r.get("me")), None)
        if me:
            lines.append(f"Место в рейтинге: <b>{me}</b> из {len(board)}")
        lines += [
            "",
            f"Мин. вывод: на карту {rub(cfg.get('payout_card_min'))} · на баланс {rub(cfg.get('payout_balance_min'))}"
            + (f" (×{cfg['balance_bonus_mult']} бонус)" if cfg.get("balance_bonus_mult") else ""),
        ]
        await bot.send_message(OWNER_TG_ID, "\n".join(lines))
    elif what in ("editreply", "editclaim"):
        key, default, title = (("auto_reply_text", RESPONDER_TEXT, "автоответчика") if what == "editreply"
                               else ("claim_text", CLAIM_TEXT, "приветствия при взятии"))
        search_mode["mode"] = key
        await cb.message.edit_text(
            f"✏️ <b>Текст {title}</b>\n\nСейчас:\n<i>{esc(state.get(key) or default)}</i>\n\n"
            "Напиши новый текст одним сообщением.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [Btn(text="♻️ Вернуть стандартный", callback_data=f"m:reset_{key}")],
                [Btn(text="◀️ Назад", callback_data="m:settings")]]))
    elif what in ("reset_auto_reply_text", "reset_claim_text"):
        key = what[6:]
        state.pop(key, None)
        save_state()
        search_mode.clear()
        await cb.message.edit_text("✅ Вернул стандартный текст.", reply_markup=menu("settings")[1])
    elif what in ("togglenew", "pause", "autoclaim", "autoreply"):
        key = {"togglenew": "notify_new", "pause": "paused", "autoclaim": "auto_claim", "autoreply": "auto_reply"}[what]
        state[key] = not state.get(key)
        save_state()
        await cb.message.edit_reply_markup(reply_markup=menu("settings")[1])
    elif what in MENUS:
        search_mode.clear()
        text, kb = menu(what)
        await cb.message.edit_text(text, reply_markup=kb)
    elif what in ("s_nick", "s_id"):
        search_mode["mode"] = "nick" if what == "s_nick" else "id"
        prompt = "👤 Напиши ник клиента (можно часть):" if what == "s_nick" else "#️⃣ Напиши номер тикета:"
        await cb.message.edit_text(prompt, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [Btn(text="◀️ Назад", callback_data="m:search")]]))


@dp.callback_query(owner)
async def on_button(cb: CallbackQuery) -> None:
    parts = cb.data.split(":")
    action = parts[0]
    try:
        if action == "m":
            await handle_menu(cb, parts[1])
            await cb.answer()
            return

        if action == "pacc":
            r = await api("POST", "/api/staff/server/panel-access", {"server_id": int(parts[1])})
            url = r.get("panel_url")
            await cb.answer()
            await bot.send_message(OWNER_TG_ID, (f"🔑 <a href=\"{esc(url)}\">Открыть панель</a>\n" if url else "")
                                   + esc(r.get("message") or ""), disable_web_page_preview=True)
            return

        if action == "pwr":
            sid, cmd = int(parts[1]), parts[2]
            if cmd != "start" and not confirmed(cb.data):
                await cb.answer(f"Нажми ещё раз, чтобы {cmd} сервер #{sid}", show_alert=True)
                return
            await api("POST", "/api/staff/server/power", {"server_id": sid, "action": cmd})
            await cb.answer(f"{cmd}: команда отправлена", show_alert=True)
            return

        tid = int(parts[1])
        if action in ("more", "less"):  # развернуть / свернуть кнопки тикета, подсказки 💡 сохраняем
            kb = cb.message.reply_markup.inline_keyboard if cb.message.reply_markup else []
            hints = [r for r in kb if r and (r[0].callback_data or "").startswith("qs:")]
            new_kb = kb_ticket(tid, more=action == "more")
            await cb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=hints + new_kb.inline_keyboard))
            await cb.answer()
            return
        if action == "full":
            data = await ticket(tid)
            await cb.message.edit_text(full_view(data), reply_markup=kb_free(tid, expanded=True),
                                       disable_web_page_preview=True)
            await cb.answer()
        elif action == "short":
            data = await ticket(tid)
            await cb.message.edit_text(await short_view_full(data["request"], "🆓 "), reply_markup=kb_free(tid),
                                       disable_web_page_preview=True)
            await cb.answer()
        elif action in ("hist", "open"):
            await show_ticket(tid)
            await cb.answer()
        elif action == "fv":
            await cb.answer()
            data = await ticket(tid)
            await send(await short_view_full(data["request"], "📥 "), tid, mine=False)
        elif action == "take":
            # взять тикет вручную: первый ответ закрепляет тикет за мной
            text = state.get("claim_text") or CLAIM_TEXT
            try:
                await send_reply(tid, text)
            except Blocked as e:
                await cb.answer(f"Кабинет не дал ответить ({e}). Возьми в кабинете.", show_alert=True)
                return
            except RuntimeError as e:
                await cb.answer(f"Не получилось: {str(e)[:150]}", show_alert=True)
                return
            remember_claim(tid)
            save_state()
            await cb.answer("Взято, приветствие отправлено")
            try:
                await cb.message.edit_reply_markup(reply_markup=None)
            except Exception:
                pass
            await bot.send_message(OWNER_TG_ID, f"✋ <b>#{tid} взят</b>\n💬 <i>Отправлено: {esc(text)}</i>")
            await show_ticket(tid)
        elif action == "claim":
            r = await act(tid, "claim")
            remember_claim(tid)
            save_state()
            await cb.answer(r.get("message") or "Взято", show_alert=bool(r.get("message")))
            await show_ticket(tid)
        elif action == "srv":
            await cb.answer()
            await show_servers(tid)
        elif action == "ai":
            await cb.answer()
            await show_ai(tid)
        elif action == "an":
            await cb.answer()
            await show_analysis(tid)
        elif action == "quick":
            rows = [[Btn(text=name, callback_data=f"qg:{tid}:{n}")] for n, (name, _) in enumerate(QUICK_GROUPS)]
            await cb.answer()
            await bot.send_message(OWNER_TG_ID, f"⚡ Быстрые фразы для #{tid} — выбери тему:",
                                   reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        elif action == "qg":
            name, group = QUICK_GROUPS[int(parts[2])]
            rows = [[Btn(text=title, callback_data=f"qs:{tid}:{key}")] for key, (title, _) in group.items()]
            rows.append([Btn(text="◀️ Назад", callback_data=f"qb:{tid}")])
            await cb.message.edit_text(f"⚡ #{tid} · {name}", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
            await cb.answer()
        elif action == "qb":
            rows = [[Btn(text=name, callback_data=f"qg:{tid}:{n}")] for n, (name, _) in enumerate(QUICK_GROUPS)]
            await cb.message.edit_text(f"⚡ Быстрые фразы для #{tid} — выбери тему:",
                                       reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
            await cb.answer()
        elif action == "qs":
            title, text = QUICK[parts[2]]
            drafts[tid] = text
            await cb.answer()
            await send(f"⚡ <b>#{tid}</b> · {esc(title)}\n\n{esc(text)}", tid, kb=kb_draft(tid))
        elif action == "tpls":
            await cb.answer()
            await show_templates(tid)
        elif action == "tpl":
            tpls = (await api("GET", "/api/staff/desk/templates")).get("templates", [])
            t = next((x for x in tpls if x["id"] == int(parts[2])), None)
            if not t:
                await cb.answer("Шаблон не найден", show_alert=True)
                return
            drafts[tid] = t["body"]
            await cb.answer()
            await send(f"📋 <b>#{tid}</b> · {esc(t['title'])}\n\n{esc(t['body'])}\n\n<i>Можно ответить reply-ем со своей правкой.</i>",
                       tid, kb=kb_draft(tid))
        elif action in ("senddraft", "notedraft"):
            text = drafts.get(tid)
            if not text:
                await cb.answer("Черновик устарел, запроси заново", show_alert=True)
                return
            internal = action == "notedraft"
            if not internal:
                await cb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                    Btn(text="✅ Да, отправить клиенту", callback_data=f"sendok:{tid}"),
                    Btn(text="✖️ Отмена", callback_data=f"sendno:{tid}")]]))
                await cb.answer()
                return
            await send_reply(tid, text, True)
            drafts.pop(tid, None)
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.reply(f"📝 Заметка добавлена в #{tid}")
            await cb.answer()
        elif action == "sendno":
            await cb.message.edit_reply_markup(reply_markup=kb_draft(tid))
            await cb.answer("Отменено")
        elif action == "sendok":
            text = drafts.get(tid)
            if not text:
                await cb.answer("Черновик устарел, выбери фразу заново", show_alert=True)
                return
            try:
                await send_reply(tid, text, False)
                unmark_auto(tid)
            except Exception as e:
                log.exception("send draft #%s", tid)
                await cb.message.reply(f"❌ Не отправлено в #{tid}: {esc(str(e))}")
                await cb.answer()
                return
            drafts.pop(tid, None)
            await cb.message.edit_reply_markup(reply_markup=None)
            await cb.message.reply(widen(f"✅ Отправлено клиенту в #{tid}", kb_ticket(tid)), reply_markup=kb_ticket(tid))
            await cb.answer()
        elif action == "prio":
            data = await ticket(tid)
            new = "normal" if data["request"].get("priority") == "high" else "high"
            await act(tid, "priority", {"priority": new})
            await cb.answer("🔥 Срочный" if new == "high" else "Приоритет обычный", show_alert=True)
        elif action in CONFIRM_ACTIONS:
            question = CONFIRM_ACTIONS[action][0]
            await cb.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                Btn(text=f"✅ Да, {question}", callback_data=f"yes_{action}:{tid}"),
                Btn(text="✖️ Отмена", callback_data=f"no:{tid}")]]))
            await cb.answer()
        elif action == "no":
            await cb.message.edit_reply_markup(reply_markup=kb_ticket(tid))
            await cb.answer("Отменено")
        elif action.startswith("yes_") and action[4:] in CONFIRM_ACTIONS:
            base = action[4:]
            _, endpoint, done = CONFIRM_ACTIONS[base]
            try:
                r = await act(tid, endpoint)
            except Exception as e:
                log.exception("%s #%s", endpoint, tid)
                await cb.message.edit_reply_markup(reply_markup=kb_ticket(tid))
                await cb.message.reply(f"❌ #{tid}: не получилось — {esc(str(e) or type(e).__name__)}")
                await cb.answer()
                return
            await cb.message.edit_reply_markup(reply_markup=None)
            extra = f"\n{esc(r.get('message'))}" if isinstance(r, dict) and r.get("message") else ""
            await cb.message.reply(f"{done} #{tid}{extra}")
            await cb.answer()
        else:
            await cb.answer()
    except SessionExpired:
        await cb.answer("Сессия истекла, обнови cookie", show_alert=True)
    except Exception as e:
        log.exception("button %s", cb.data)
        await cb.answer(f"Ошибка: {str(e)[:180]}", show_alert=True)


# ---------- ответы ----------

@dp.message(owner, F.reply_to_message, F.text)
async def on_reply(msg: Message) -> None:
    tid = state["tg2ticket"].get(str(msg.reply_to_message.message_id))
    if not tid:
        await msg.reply("Не понял, к какому тикету ответ. Отвечай на сообщение с номером тикета.")
        return
    text = msg.text.strip()
    if text.startswith("?"):  # ответ на вопрос разбора — факты от сотрудника, пересобираем разбор
        fact = text[1:].strip()
        if fact:
            OPERATOR_FACTS.setdefault(tid, []).append(fact)
        await msg.reply(f"🧠 Учёл: {esc(fact)}. Пересобираю разбор #{tid}…")
        await show_analysis(tid)
        return
    internal = text.startswith("!")
    if internal:
        text = text[1:].strip()
    try:
        await send_reply(tid, text, internal)
        if not internal:
            unmark_auto(tid)
    except SessionExpired:
        await msg.reply("⚠️ Сессия истекла, ответ НЕ отправлен.")
        return
    except Exception as e:
        await msg.reply(f"❌ Не отправлено: {esc(str(e))}")
        return
    drafts.pop(tid, None)
    await msg.reply(widen(f"{'📝 Заметка' if internal else '✅ Отправлено'} в #{tid}", kb_ticket(tid)), reply_markup=kb_ticket(tid))


@dp.message(owner, F.reply_to_message, F.photo | F.document)
async def on_reply_file(msg: Message) -> None:
    tid = state["tg2ticket"].get(str(msg.reply_to_message.message_id))
    if not tid:
        await msg.reply("Не понял, к какому тикету файл. Отвечай на сообщение тикета.")
        return
    if msg.photo:
        f = msg.photo[-1]
        name = f"screenshot_{f.file_unique_id}.jpg"
    else:
        f = msg.document
        name = f.file_name or "file"
    buf = await bot.download(f)
    try:
        await upload_file(tid, buf.read(), name, (msg.caption or "").strip())
    except Exception as e:
        await msg.reply(f"❌ Файл не отправлен: {esc(str(e))}")
        return
    await msg.reply(widen(f"📎 Файл отправлен в #{tid}", kb_ticket(tid)), reply_markup=kb_ticket(tid))


@dp.message(owner, F.text, ~F.text.startswith("/"))
async def on_plain_text(msg: Message) -> None:
    """Обычный текст без reply = поиск: по номеру, если ждём номер или ввели цифры, иначе по нику."""
    if search_mode.get("mode") in ("auto_reply_text", "claim_text"):
        key = search_mode.pop("mode")
        state[key] = msg.text.strip()
        save_state()
        await msg.answer(f"✅ Сохранил текст:\n<i>{esc(state[key])}</i>", reply_markup=menu("settings")[1])
        return
    text = msg.text.strip().lstrip("#")
    mode = search_mode.get("mode")
    if mode == "id" or (mode is None and text.isdigit()):
        if not text.isdigit():
            await msg.answer("Нужен номер тикета цифрами, например 10886.")
            return
        try:
            await show_ticket(int(text))
        except Exception as e:
            await msg.answer(f"Тикет #{esc(text)} не открылся: {esc(str(e))}")
        return
    await search_tickets(text)


# ---------- статистика закрытых обращений по дням ----------
# API заработка отдаёт только последние 100 начислений, поэтому бот сам копит историю.
# Время в кабинете — МСК без пояса, значит дата created_at[:10] = сутки 00:00–23:59:59 МСК.
EARN_SYNC_SEC = int(os.getenv("EARN_SYNC_SEC", "900"))
MSK = timezone(timedelta(hours=3))


def sync_closed(e: dict) -> None:
    log_ = state.setdefault("closed_log", {})
    for it in e.get("items") or []:
        if it.get("kind") != "resolve" or not it.get("created_at"):
            continue
        log_[str(it["id"])] = [it["created_at"][:10], float(it.get("amount") or 0),
                               "автозакрыт" in (it.get("note") or "")]
    cutoff = (datetime.now(MSK) - timedelta(days=90)).strftime("%Y-%m-%d")
    for k in [k for k, v in log_.items() if v[0] < cutoff]:
        del log_[k]
    if "closed_since" not in state and log_:
        state["closed_since"] = min(v[0] for v in log_.values())
    save_state()


def closed_stats_lines() -> list[str]:
    log_ = state.get("closed_log") or {}
    days: dict[str, list] = {}
    for d, amount, auto in log_.values():
        r = days.setdefault(d, [0, 0, 0.0])
        r[0] += 1
        r[1] += auto
        r[2] += amount
    since = state.get("closed_since", "")
    today = datetime.now(MSK).date()
    wd = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]
    lines = ["", "📅 <b>Закрыто по дням</b> (00:00–23:59 МСК)"]
    week = [0, 0.0]
    for n in range(7):
        day = today - timedelta(days=n)
        key = day.isoformat()
        if key < since:
            break
        c, a, amt = days.get(key, [0, 0, 0.0])
        week[0] += c
        week[1] += amt
        name = "Сегодня" if n == 0 else "Вчера" if n == 1 else f"{day:%d.%m} {wd[day.weekday()]}"
        partial = " (неполный)" if key == since and n > 0 else ""
        lines.append(f"{name}: <b>{c}</b>" + (f" (авто {a})" if a else "") + f" · {amt:,.0f} ₽".replace(",", " ") + partial)
    lines.append(f"За 7 дней: <b>{week[0]}</b> · {week[1]:,.0f} ₽".replace(",", " "))
    full = {d: r for d, r in days.items() if d > since and d < today.isoformat()}
    if full:
        best = max(full.items(), key=lambda kv: kv[1][0])
        lines.append(f"Рекорд: <b>{best[1][0]}</b> ({best[0][8:10]}.{best[0][5:7]})")
    return lines


async def earn_sync_loop() -> None:
    while True:
        try:
            sync_closed(await api("GET", "/api/staff/support/earnings"))
        except Exception as ex:
            log.warning("earnings sync failed: %s", ex)
        await asyncio.sleep(EARN_SYNC_SEC)


async def main() -> None:
    # подсказки команд над полем ввода убраны: всё управление — кнопками
    await bot.delete_my_commands()
    await bot.delete_my_commands(scope=BotCommandScopeChat(chat_id=OWNER_TG_ID))
    await bot.set_chat_menu_button(chat_id=OWNER_TG_ID, menu_button=MenuButtonDefault())
    for mid, tid in list(state.pop("analysis_running", {}).items()):
        try:
            await bot.edit_message_text(f"🧠 #{tid}: разбор прерван перезапуском бота, нажми «Разбор» ещё раз.",
                                        chat_id=OWNER_TG_ID, message_id=int(mid))
        except Exception:
            pass
    save_state()
    asyncio.create_task(poller())
    asyncio.create_task(earn_sync_loop())
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
