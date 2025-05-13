from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type
from .model import SheetModel


class BaseSheetDB(ABC):
    @abstractmethod
    def insert(self, model: SheetModel): ...

    @abstractmethod
    def insert_many(self, models: List[SheetModel]): ...

    @abstractmethod
    def get_all(
        self, model: Type[SheetModel], filters: Optional[Dict[str, Any]] = None
    ): ...

    @abstractmethod
    def get_one(self, model: Type[SheetModel], filters: Dict[str, Any]): ...

    @abstractmethod
    def update(
        self,
        model: Type[SheetModel],
        filters: Dict[str, Any],
        update_data: Dict[str, Any],
    ): ...

    @abstractmethod
    def delete(self, model: Type[SheetModel], filters: Dict[str, Any]): ...

    @abstractmethod
    def delete_all(self, model: Type[SheetModel]): ...
