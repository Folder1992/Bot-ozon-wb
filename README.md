
# Marketplace Parsing Bot (Ozon + Wildberries) — v1.7.4 (fixed)

Готовая сборка под ваши правки:
- Playwright **async** + persistent context (куки сохраняются, меньше антибота).
- Мини-стелс без внешних зависимостей (иниц. скрипты).
- Парсинг **через JSON‑LD** со страницы (и фоллбек по DOM).
- Красивый пост: Название, ⭐Оценка, 💸Цена, 📝Описание, ссылка под спойлером.
- Отправка всех фото (до лимита) медиагруппой.

## Установка

```bash
python -m venv .venv
. .venv/Scripts/activate  # Windows PowerShell
pip install -r requirements.txt
python -m playwright install
```

Создайте `.env` по примеру из `.env.example` и укажите **BOT_TOKEN**.

## Запуск
```bash
python -m bot.main
```

## Переменные окружения (.env)

```
BOT_TOKEN=123456:ABC...      # токен Telegram-бота
SHOW_BROWSER=1               # 1 — показывать браузер, 0 — скрыть
SLOW_MO=250                  # задержка действий браузера, мс
DEBUG_DIR=debug              # куда сохранять скрины
MAX_IMAGES=10                # максимум картинок в посте
```

## Примечание
Если Ozon покажет страницу «Доступ ограничен» — бот сделает до трёх попыток.
Для лучшей стабильности используйте резидентный RU‑прокси на уровне системы/сети.
