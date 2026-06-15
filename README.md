# AI Консилиум — Telegram Bot

Бот который задаёт твой вопрос нескольким AI одновременно.

## Команды

- `/council` — включить режим консилиума (Gemini + DeepSeek отвечают вместе)
- `/solo` — только DeepSeek
- `/clear` — очистить историю

## Деплой на Railway

1. Загрузи эти файлы на GitHub (новый репозиторий)
2. Зайди на railway.app → New Project → Deploy from GitHub
3. Выбери репозиторий
4. Добавь переменные окружения (Variables):
   - `TELEGRAM_TOKEN` = токен от @BotFather
   - `GEMINI_API_KEY` = ключ от aistudio.google.com
   - `DEEPSEEK_API_KEY` = ключ от platform.deepseek.com
5. Deploy!

## Переменные окружения

| Переменная | Где взять |
|---|---|
| TELEGRAM_TOKEN | @BotFather в Telegram |
| GEMINI_API_KEY | aistudio.google.com |
| DEEPSEEK_API_KEY | platform.deepseek.com |
