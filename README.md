
# Описание проекта
Данный проект предоставляет ML-сервис с подсистемой биллинга, который осуществляет предсказания на основе ML-моделей и списывает кредиты с личного счета пользователя за успешное выполнение предсказания. 

Легенда: на далекой-далекой Нибиру случилась катастрофа: гигансткий космический корабль НИНАТИК с нибирянцами потерпел крушение, врезавшись в гигансткий астероид, и только 80% экипажа выжило. К сожалению, такие события нередки, поэтому 
нибирянцам важно оценивать риски такой поездки. Для этого разработали сложную программу на квантовом компьютере: сервис, куда нибирянец может
ввести свои данные и получить вероятность выживания. Сервис предоставляется по подписке, которую можно выбирать самому - чем
дороже подписка, тем точнее прогноз.

# Структура 

# Auth + ML Service — API документация и инструкция (Markdown)

## Обзор

- Бэкенд: FastAPI
- БД: SQLite (создаётся автоматически при старте)
- Аутентификация:
  - Логин — HTTP Basic (email+password) → выдается JWT
  - Доступ к защищённым эндпоинтам — Authorization: Bearer <JWT>
- Тарифы (план): basic | pro | premium
- Кредиты: списываются за /predict согласно тарифу (баланс хранится в `balance_cents`, 1 = 1 кредит)
- История транзакций: логируются пополнения (type=topup, сумма > 0) и списания за предсказания (type=predict, сумма < 0)

---

## Быстрый старт

1) Установите зависимости:
```bash
pip install fastapi uvicorn "python-jose[cryptography]" "passlib[bcrypt]" scikit-learn joblib numpy
```

2) Запустите сервер:
```bash
uvicorn main:app --reload
```

3) (Опционально) Настройте переменные окружения (см. ниже).

---

## Переменные окружения (настройки)

- SECRET_KEY — секрет для JWT (строка)
- ACCESS_TOKEN_EXPIRE_MINUTES — время жизни токена в минутах (по умолчанию 60)
- DB_PATH — путь к SQLite (например, ./data/app.db)
- MODEL_BASIC_PATH — путь к модели basic (по умолчанию ./models/basic.pkl)
- MODEL_PRO_PATH — путь к модели pro (по умолчанию ./models/pro.pkl)
- MODEL_PREMIUM_PATH — путь к модели premium (по умолчанию ./models/premium.pkl)
- PRICE_BASIC_INFER_CREDITS — цена инференса для basic (по умолчанию 1)
- PRICE_PRO_INFER_CREDITS — цена инференса для pro (по умолчанию 5)
- PRICE_PREMIUM_INFER_CREDITS — цена инференса для premium (по умолчанию 20)
- TOPUP_DEFAULT_AMOUNT_CENTS — пополнение по умолчанию (по умолчанию 100)

---

## Модели данных (DTO)

- User
  - id: int
  - email: string
  - is_admin: bool
  - balance_cents: int
  - created_at: string (UTC)
  - plan: string ("basic" | "pro" | "premium")

- Transaction
  - id: int
  - type: string ("topup" | "predict")
  - amount_cents: int (пополнение > 0, списание < 0)
  - balance_after: int
  - metadata: object | null
  - created_at: string (UTC)

- PredictResponse
  - result: any
  - charged_credits: int
  - balance_credits: int
  - plan: string

---

## Эндпоинты

### 1) Регистрация
POST /register

Request body (JSON):
```json
{
  "email": "user@example.com",
  "password": "secret"
}
```

Response:
- 201: User
- 400: {"detail": "User with this email already exists"}

Пример:
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret"}'
```

---

### 2) Логин (HTTP Basic → JWT)
POST /login

Headers:
- Authorization: Basic base64(email:password)

Response:
- 200: {"access_token":"...","token_type":"bearer"}
- 401: {"detail":"Incorrect email or password"}

Пример:
```bash
curl -X POST -u user@example.com:secret http://localhost:8000/login
```

---

### 3) Профиль текущего пользователя
GET /me

Headers:
- Authorization: Bearer <JWT>

Response:
- 200: User
- 401: {"detail":"Could not validate credentials"}

Пример:
```bash
curl http://localhost:8000/me \
  -H "Authorization: Bearer <JWT>"
```

---

### 4) Пополнение баланса
POST /topup

Headers:
- Authorization: Bearer <JWT>

Request body (опционально):
```json
{
  "amount_cents": 250
}
```
Если тело не передано — используется TOPUP_DEFAULT_AMOUNT_CENTS.

Response:
- 200: User (с обновлённым балансом)
- 400: {"detail":"Amount must be positive"} и др.
- 401: not authenticated

Примеры:
```bash
# Пополнение по умолчанию
curl -X POST http://localhost:8000/topup \
  -H "Authorization: Bearer <JWT>"

# Пополнение на 500 кредитов
curl -X POST http://localhost:8000/topup \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"amount_cents":500}'
```

---

### 5) Смена тарифа (плана)
POST /plan

Headers:
- Authorization: Bearer <JWT>

Request body:
```json
{
  "plan": "pro"
}
```
Допустимые значения: "basic" | "pro" | "premium"

Response:
- 200: User (с обновлённым plan)
- 400: {"detail":"Invalid plan"}
- 401: not authenticated

Пример:
```bash
curl -X POST http://localhost:8000/plan \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"plan":"premium"}'
```

---

### 6) Предсказание (асинхронный инференс под капотом)
POST /predict

Headers:
- Authorization: Bearer <JWT>

Request body:
```json
{
  "features": [1, 35]
}
```
Где features = [Sex, Age]; Sex: female=0, male=1; Age: неотрицательное число.

Response:
- 200: PredictResponse
- 400: {"detail":"Unsupported plan"} и др.
- 401: not authenticated
- 402: {"detail":"Insufficient funds"}

Пример:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"features":[1,35]}'
```

---

### 7) История транзакций
GET /transactions?limit=50&offset=0

Headers:
- Authorization: Bearer <JWT>

Query:
- limit: 1..500 (по умолчанию 50)
- offset: >= 0 (по умолчанию 0)

Response:
- 200: [Transaction]
- 401: not authenticated

Пример:
```bash
curl "http://localhost:8000/transactions?limit=50&offset=0" \
  -H "Authorization: Bearer <JWT>"
```

---

## Гайд по использованию

1) Зарегистрируйтесь:
```bash
curl -X POST http://localhost:8000/register \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"secret"}'
```

2) Войдите по HTTP Basic и получите JWT:
```bash
curl -X POST -u user@example.com:secret http://localhost:8000/login
```

3) Пополните баланс (кредиты):
```bash
curl -X POST http://localhost:8000/topup \
  -H "Authorization: Bearer <JWT>"
```

4) (Опционально) смените тариф:
```bash
curl -X POST http://localhost:8000/plan \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"plan":"pro"}'
```

5) Выполните предсказание:
```bash
curl -X POST http://localhost:8000/predict \
  -H "Authorization: Bearer <JWT>" \
  -H "Content-Type: application/json" \
  -d '{"features":[1, 30]}'
```

6) Посмотрите историю транзакций:
```bash
curl "http://localhost:8000/transactions?limit=50&offset=0" \
  -H "Authorization: Bearer <JWT>"
```

---

## Ошибки и статусы

- 400 Bad Request — неправильные параметры (например, неверный plan, non-positive amount)
- 401 Unauthorized — нет/невалидный JWT
- 402 Payment Required — недостаточно кредитов для /predict
- Формат ошибок: `{"detail":"..."}`

---

## Заметки

- ML модели:
  - Локально подгружаются (scikit-learn, joblib) лениво; при отсутствии файла используется заглушка.
  - Позже можно заменить провайдер на HTTP (async) без изменения бизнес-логики.

- CORS:
  - Если открываете тестовый index.html как file://, включите CORS в FastAPI или отдавайте страницу статикой с того же origin, чтобы избежать CORS-проблем.

- Безопасность:
  - Поменяйте SECRET_KEY в проде.
  - Ограничьте allow_origins в CORS для продакшена.


## Демо пользовательского интерфейса