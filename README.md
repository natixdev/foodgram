# Foodgram

[![Main foodgram workflow](https://github.com/easymat/foodgram/actions/workflows/main.yml/badge.svg)](https://github.com/easymat/foodgram/actions/workflows/main.yml)

## Описание проекта

Проект **Foodgram** — это веб-приложение для публикации рецептов, создания списков покупок и подписки на любимых авторов.

- **Публикация рецептов** с фотографиями, ингредиентами и тегами
- **Добавление в избранное** - сохраняйте понравившиеся рецепты
- **Создание списка покупок** - автоматическая генерация на основе выбранных рецептов
- **Подписка на авторов** - следите за новыми рецептами любимых кулинаров
- **Фильтрация по тегам** - завтрак, обед, ужин и другим категориям

API построен на Django REST Framework.
SPA на React.
Настроена оркестрация контейнеров Docker и CI/CD пайплайн на GitHub Actions.


## Использованные технологии

- Python (3.12) | `https://www.python.org/` — основной язык

### Основные фреймворки:
- Django (5.1.1) | `https://docs.djangoproject.com/` — основной бэкенд-фреймворк
- Django REST Framework (3.15.2) | `https://www.django-rest-framework.org/` — создание REST API

### Основные библиотеки:
- DRF Authtoken | `https://www.django-rest-framework.org/api-guide/authentication/#tokenauthentication` — аутентификация на основе токенов
- Djoser (2.3.3) | `https://djoser.readthedocs.io/` — добавляет готовые эндпоинты для управление пользователями
- React | `https://legacy.reactjs.org/docs/getting-started.html` — построение пользовательского интерфейса

### СУБД
- PostgreSQL | `https://www.postgresql.org/docs/current/`
- SQLite3 | `https://www.sqlite.org/docs.html`

### Управление проектом на сервере
- Docker | `https://docs.docker.com/` — Контейнеризация, оркестрация контейнеров
- Nginx | `https://nginx.org/en/docs/` —  обратный прокси-сервер, обрабатывает статические и медиа файлы
- GitHub Actions | `https://docs.github.com/en/actions` — CI/CD пайплайн
- Gunicorn | `https://docs.gunicorn.org/en/stable/` — WSGI сервер


## Установка и запуск

### Как заполнить .env
```
POSTGRES_DB=название_бд
POSTGRES_USER=имя_пользователя
POSTGRES_PASSWORD=ваш_надеждый_пароль
DB_HOST=db
DB_PORT=5432
DB_SQLITE=True

SECRET_KEY='ваш_секретный_ключ'
DEBUG=True
ALLOWED_HOSTS='localhost, 127.0.0.1, ваш_ip, ваше_доменное_имя'
```

### Локальная разработка (без Docker)

1. Клонируйте репозиторий:
```bash
git clone https:/https://github.com/easymat/foodgram_final
cd foodgram_final
```

2. Создайте и активируйте виртуальное окружение:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # для Linux/MacOS
source venv/Scripts/activate     # для Windows
```

3. Установите зависимости:
```bash
pip install -r requirements.txt
```

4. Примените миграции:
```bash
python manage.py migrate
```

5. Создайте суперпользователя (опционально):
```bash
python manage.py createsuperuser
```

6. В корне проекта создайте файл .env и внесите в него необходимую информацию:
```bash
cd ..
touch .env
nano .env
```

7. Запустите сервер:
```bash
python manage.py runserver
```

API будет доступно по адресу: `http://127.0.0.1:9000/api/`

8. Запустите SPA:
```bash
cd ..
cd frontend
npm i
npm run start
```

SPA будет доступно по адресу: `http://127.0.0.1:3000/`


### Запуск в Docker-контейнерах

1. Установите Docker Compose на сервер
```bash
sudo apt update
sudo apt install curl
curl -fSL https://get.docker.com -o get-docker.sh
sudo sh ./get-docker.sh
sudo apt install docker-compose-plugin
```

2. Создайте папку проекта, файл .env и внесите в него необходимую информацию:
```bash
sudo mkdir foodgram
cd foodgram
sudo touch .env
sudo nano .env
```

3. Создайте файл docker-compose.production.yml и скопируйте в него содержимое файла docker-compose.production.yml:
```bash
sudo touch docker-compose.production.yml
sudo nano docker-compose.production.yml
```

4. Запустите  Docker Compose в режиме демона:
```bash
sudo docker compose -f docker-compose.production.yml up -d
```

5. Соберите статику:
```bash
sudo docker compose -f docker-compose.production.yml exec backend python manage.py collectstatic
sudo docker compose -f docker-compose.production.yml exec backend cp -r /app/collected_static/. /backend_static/static/
```

6. Примените миграции:
```bash
sudo docker compose -f docker-compose.production.yml exec backend python manage.py migrate
```


## Автор
Хуснутдинова Наталья | [ссылка на github](https://github.com/easymat)
