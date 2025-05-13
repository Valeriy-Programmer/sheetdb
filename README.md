-m pip install -e E:\repos_E\python\Libraries\sheetdb
pip install -e git+file:///E:/repos_E/phyton/Libraries/sheetdb
pip install --upgrade git+file:///E:/repos_E/phyton/Libraries/sheetdb#egg=gsheetdb
pip install git+https://github.com/Valeriy-Programmer/sheetdb

sheetdb
Управляйте Google Таблицами как базой данных — удобно, как ORM.

🚀 Установка
bash
Копировать
Редактировать
pip install gspread gspread_asyncio google-auth pydantic
Если хочешь, можешь установить библиотеку прямо из исходников:

bash
Копировать
Редактировать
pip install -e .
🔧 Быстрый старт
Подключите библиотеку:

python
Копировать
Редактировать
from gsheetdb import AsyncGoogleSheetDB, SheetModel
Опишите свою модель:

python
Копировать
Редактировать
class User(SheetModel):
sheet_name = "Users"
**field_map** = {
"id": "User ID",
"name": "Full Name",
"email": "Email Address"
}
id: str
name: str
email: str
Настройте подключение:

python
Копировать
Редактировать
def get_creds():
from google.oauth2.service_account import Credentials
return Credentials.from_service_account_file(
"service_account.json",
scopes=[
"https://www.googleapis.com/auth/spreadsheets",
"https://www.googleapis.com/auth/drive",
]
)

db = AsyncGoogleSheetDB(
creds_fn=get_creds,
spreadsheet_id="ВАШ_SPREADSHEET_ID"
)
Используйте:

python
Копировать
Редактировать
import asyncio

async def main():
user = User(id="1", name="Alice", email="alice@example.com")
await db.insert(user)

    users = await db.get_all(User)
    print(users)

asyncio.run(main())
✨ Основные возможности
insert(model) — добавить запись

get_all(model_class, filters=None, start=0, limit=None) — получить все записи с фильтрацией

get_one(model_class, filters) — получить одну запись

get_one_or_raise(model_class, filters) — получить одну запись или выбросить NotFoundError

delete_all(model_class) — удалить всю таблицу

Удобные ошибки (NotFoundError, ValidationError, ConflictError и другие)

🔥 Примеры
Асинхронный пример: examples/user_product_demo.py

Синхронный пример: examples/user_product_demo_sync.py

🛠 Требования
Python 3.8+

Google Sheets API активирован

Файл сервисного аккаунта (service_account.json)

📄 Лицензия
MIT License
