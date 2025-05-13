from pydantic import BaseModel, PrivateAttr, model_validator
from typing import ClassVar, List, Dict, Union


class SheetModel(BaseModel):
    sheet_name: ClassVar[str]  # Имя листа на уровне класса
    _sheet_name: str = PrivateAttr(default="")  # Храним отдельно для экземпляра

    # Атрибуты экземпляра
    _field_map: Dict[str, str] = PrivateAttr(default_factory=dict)
    _key_fields: Union[str, List[str]] = PrivateAttr(default="id")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if not self._field_map:
            self._field_map = {}
        if not isinstance(self._key_fields, list):
            self._key_fields = [self._key_fields]
        # Присваиваем sheet_name экземпляра значением атрибута класса
        self._sheet_name = self.sheet_name

    @model_validator(mode="before")
    @classmethod
    def validate_field_map_and_key_fields(cls, values):
        # Ничего не валидируем
        return values

    def get_sheet_name(self) -> str:
        return self._sheet_name  # Возвращаем значение для экземпляра

    @classmethod
    def get_class_sheet_name(cls) -> str:
        return cls.sheet_name

    def get_key_fields(self) -> List[str]:
        return (
            self._key_fields
            if isinstance(self._key_fields, list)
            else [self._key_fields]
        )

    def get_field_map(self) -> Dict[str, str]:
        return self._field_map

    @classmethod
    def generate_field_map(cls) -> Dict[str, str]:
        """
        Генерирует маппинг полей модели: {"название_столбца": "имя_поля_модели"}.
        Использует get_field_map() для получения маппинга полей.
        """
        field_map = (
            cls.get_field_map()
        )  # Используем get_field_map для получения маппинга
        return {v: k for k, v in field_map.items()}  # Переворачиваем маппинг

    class Config:
        from_attributes = True
