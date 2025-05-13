from typing import Optional


class SheetDBError(Exception):
    """Base class for all GSheetDB-related errors."""

    default_code = "gsheetdb_error"

    def __init__(self, detail: str, code: Optional[str] = None):
        self.detail = detail
        self.code = code or self.default_code
        super().__init__(self.__str__())

    def __str__(self):
        return f"[{self.code}] {self.detail}"


class NotFoundError(SheetDBError):
    """Raised when an entity is not found in the sheet."""

    default_code = "not_found"


class ValidationError(SheetDBError):
    """Raised when provided data is invalid."""

    default_code = "validation_error"


class SheetAccessError(SheetDBError):
    """Raised when there is a problem accessing the sheet."""

    default_code = "sheet_access_error"


class ConflictError(SheetDBError):
    """Raised when a conflicting entry already exists."""

    default_code = "conflict_error"


# Использование
# raise ValidationError("Price must be a number.")


# Как использовать их в будущем
# Пример: ValidationError

# python
# Копировать
# Редактировать
# if not isinstance(data["price"], (int, float)):
#     raise ValidationError(detail="Price must be a number.")
# Пример: SheetAccessError

# python
# Копировать
# Редактировать
# try:
#     ws = await client.worksheet(sheet_name)
# except SomeGSpreadError as e:
#     raise SheetAccessError(detail=f"Cannot access sheet '{sheet_name}': {str(e)}")
# Пример: ConflictError

# python
# Копировать
# Редактировать
# existing = await self.get_one(UserModel, {"email": new_user.email})
# if existing:
#     raise ConflictError(detail=f"User with email {new_user.email} already exists.")
