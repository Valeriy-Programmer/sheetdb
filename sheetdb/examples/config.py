import os
from dotenv import load_dotenv

# Загружаем .env файл
load_dotenv()

# Получаем значения из переменных окружения
SERVICE_ACCOUNT_FILE = os.getenv("SERVICE_ACCOUNT_FILE")
GOOGLE_SCOPES = os.getenv("GOOGLE_SCOPES")

# Преобразуем scopes в список (они в env через запятую)
if GOOGLE_SCOPES:
    GOOGLE_SCOPES = [scope.strip() for scope in GOOGLE_SCOPES.split(",")]
else:
    GOOGLE_SCOPES = []
