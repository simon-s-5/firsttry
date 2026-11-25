# Подсчёт токенов Claude

Небольшая CLI-утилита, которая считает входные токены запроса **до** его отправки в Claude.
Она вызывает бесплатный эндпоинт `POST /v1/messages/count_tokens` через официальный Python SDK.

## Установка

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...   # или профиль `ant auth login`
```

## Примеры

```bash
# Простой текст + системная подсказка
python token_counter.py "Hello, Claude" -s "You are a scientist"

# Файлы: текст, изображения (jpg/png/gif/webp) и PDF отправляются в base64
python token_counter.py -f notes.md -f photo.jpg "Describe this image"
python token_counter.py -f document.pdf "Please summarize this document."

# Из stdin
cat prompt.txt | python token_counter.py --stdin

# Сравнение моделей (модели начиная с Claude Opus 4.7 используют новый токенизатор, ~+30%)
python token_counter.py -f prompt.txt -m claude-sonnet-4-6 -m claude-opus-5-5
```

Модель по умолчанию — `claude-opus-5-5`. При сравнении первая модель служит базой, а для остальных показывается разница в процентах.

## Ограничения эндпоинта

- Результат — **оценка**; фактическое число токенов при создании сообщения может немного отличаться.
- Серверные инструменты (кроме инструмента-советника), MCP-коннектор и источники `url`/`file` возвращают `invalid_request_error`, поэтому утилита всегда отправляет файлы в base64.
- Эндпоинт бесплатен, но ограничен по RPM в зависимости от уровня использования. Эти лимиты не зависят от лимитов создания сообщений.

## Тесты

```bash
pytest
```
