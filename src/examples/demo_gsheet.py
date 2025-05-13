import asyncio
from google.oauth2.service_account import Credentials
from typing import ClassVar, Dict
from pydantic import model_validator
from .config import SERVICE_ACCOUNT_FILE, GOOGLE_SCOPES
from src.backends.gsheet import GoogleSheetDB
from src.exceptions import NotFoundError
from src.interfaces.model import SheetModel


# --- 1. Определяем модели ---

# Запуск
# python -m src.examples.demo_gsheet


class User(SheetModel):
    sheet_name: ClassVar[str] = "Users"
    id: int
    name: str
    email: str

    @classmethod
    def get_field_map(cls) -> Dict[str, str]:
        return {
            "id": "User ID",
            "name": "Full Name",
            "email": "Email Address",
        }


class Product(SheetModel):
    sheet_name: ClassVar[str] = "Products"
    id: int
    name: str
    price: float

    @classmethod
    def get_field_map(cls) -> Dict[str, str]:
        return {
            "id": "Product ID",
            "name": "Product Name",
            "price": "Price",
        }

    @model_validator(mode="before")
    @classmethod
    def convert_price(cls, values):
        # Если цена передана как строка с запятой, заменяем ее на точку и конвертируем в float
        if "price" in values:
            price = values["price"]
            if isinstance(price, str):
                values["price"] = float(price.replace(",", "."))
        return values


# --- 2. Подключаемся к Google Sheets ---


def get_creds():
    return Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE,
        scopes=GOOGLE_SCOPES,
    )


# Создаем объект БД
db = GoogleSheetDB(
    creds_fn=get_creds, spreadsheet_id="1w19ILIOK82aZzqkEqUb6at63YKnE76hnRq26T6BG0HE"
)

# --- 3. Работаем с данными ---


async def main():
    # 3.1.1 Добавить пользователя
    user = User(id=1, name="Alice", email="alice@example.com")
    db.insert(user)

    # Создаём список пользователей
    users = [
        User(id=2, name="Bob", email="bob@example.com"),
        User(id=3, name="Charlie", email="charlie@example.com"),
        User(id=1, name="Alice", email="alice@example.com"),
    ]

    # 3.1.2 Добавляем список пользователей
    db.insert_many(users)

    # Лог или проверка
    print(f"Inserted {len(users)} users.")

    # 3.2.1 Добавить продукт
    product = Product(id=1, name="Laptop", price=999.95)
    db.insert(product)

    # 3.3.1 Получаем все продукты
    products = db.get_all(Product)
    print("Все продукты:")
    for product in products:
        print(f"Product: {product.name} ({product.price})")

    # 3.3.2 Получить всех пользователей
    users = db.get_all(User)
    print("Все пользователи:")
    for user in users:
        print(f"User: {user.name} ({user.email})")

    # 3.3.3 Получить пользователей с фильтром
    users = db.get_all(User, filters={"email": "alice@example.com"})
    print("Пользователи с email alice@example.com:")
    for user in users:
        print(f"User: {user.name} ({user.email})")

    # 3.4 Найти одного пользователя по фильтру
    try:
        alice = db.get_one(User, filters={"email": "alice@example.com"})
        print(f"Найден пользователь: {alice.name}")
    except NotFoundError:
        print("Пользователь не найден!")

    # 3.5 Обновить данные пользователя
    try:
        updated_user = db.update(
            User,
            filters={"email": "alice@example.com", "name": "Alice"},
            update_data={
                "name": "Alice Wonderland",
                "email": "alice.wonderland@example.com",
            },
        )
        print(f"Обновленный пользователь: {updated_user.name} ({updated_user.email})")
    except NotFoundError:
        print("Пользователь не найден!")

    # 3.6 Удалить пользователя
    try:
        deleted_user = db.delete(User, filters={"email": "charlie@example.com"})
        print(f"Удаленный пользователь: {deleted_user.name} ({deleted_user.email})")
    except NotFoundError:
        print("Пользователь не найден!")

    # 3.7 Удалить все продукты
    db.delete_all(Product)
    print("Таблица продуктов очищена!")


if __name__ == "__main__":
    asyncio.run(main())
