# Деплой DeepGaze API на Timeweb App Platform

## Что нужно

- Аккаунт на [timeweb.cloud](https://timeweb.cloud)
- Git-репозиторий (GitHub / GitLab)

---

## Шаг 1: Создай Git-репозиторий

Создай **новый репозиторий** на GitHub и загрузи в него 3 файла из папки `deepgaze_api/`:

```
deepgaze_api/
├── app.py              ← Flask-сервер
├── requirements.txt    ← зависимости Python
└── Procfile            ← команда запуска
```

Загрузи через GitHub UI (Add file → Upload files) или через git:

```bash
git init
git add app.py requirements.txt Procfile
git commit -m "DeepGaze API"
git remote add origin https://github.com/YOUR_USER/deepgaze-api.git
git push -u origin main
```

---

## Шаг 2: Создай приложение на Timeweb

1. Зайди в **Timeweb Cloud** → **App Platform** → **Создать приложение**
2. Выбери **Python** шаблон
3. Подключи свой GitHub-репозиторий
4. Настройки:
   - **Тариф**: минимум **4 ГБ RAM** (модель DeepGaze тяжёлая)
   - **Команда запуска**: оставь как в Procfile (автоопределится)
   - **Порт**: `5000` (или `$PORT` — Timeweb задаёт автоматически)

---

## Шаг 3: Дождись деплоя

- Сборка займёт **5–10 минут** (скачивание PyTorch ~800 МБ)
- Первый запрос после деплоя будет медленным (загрузка модели ~30 сек)
- Дальше — по 5–15 сек на изображение

---

## Шаг 4: Подключи к Lovable-фронтенду

1. Скопируй URL приложения из Timeweb (например `https://your-app.timeweb.cloud`)
2. В приложении нажми ⚙️ (шестерёнку)
3. Вставь URL в поле **«URL API сервера»**
4. Загрузи картинку и нажми **«Анализировать»**

---

## Проверка работы

Открой в браузере:
```
https://your-app.timeweb.cloud/health
```
Должен вернуть: `{"status": "ok"}`

---

## Возможные проблемы

| Проблема | Решение |
|----------|---------|
| Out of memory | Выбери тариф с 4+ ГБ RAM |
| Timeout при сборке | `requirements.txt` с CPU-версией PyTorch уже настроен |
| CORS ошибка | Уже решено — `flask-cors` включён |
| Долгий первый запрос | Нормально — модель грузится в память |

---

## Стоимость

Ориентировочно **~500–800 ₽/мес** за тариф с 4 ГБ RAM на Timeweb App Platform.
