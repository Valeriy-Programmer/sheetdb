import csv
import os
from typing import Any, Dict, List, Optional, Type
from sheetdb.logger_utils import get_logger
from sheetdb.interfaces.base import BaseSheetDB
from sheetdb.interfaces.model import SheetModel
from sheetdb.exceptions import NotFoundError

logger = get_logger("csvdb")

cache_headers: Dict[str, List[str]] = {}

# Константы для CSV
CSV_DELIMITER = ";"
CSV_QUOTING = csv.QUOTE_MINIMAL  # Обрамляет ячейки в кавычки, если нужно


class CsvDB(BaseSheetDB):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def _get_headers(self) -> List[str]:
        if self.file_path in cache_headers:
            return cache_headers[self.file_path]

        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=CSV_DELIMITER, quoting=CSV_QUOTING)
            headers = next(reader, [])
            cache_headers[self.file_path] = headers
            return headers

    def _write_rows(self, headers: List[str], rows: List[List[Any]]):
        with open(self.file_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=CSV_DELIMITER, quoting=CSV_QUOTING)
            writer.writerow(headers)
            writer.writerows(rows)

    def _append_row(self, row: List[Any]):
        with open(self.file_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, delimiter=CSV_DELIMITER, quoting=CSV_QUOTING)
            writer.writerow(row)

    def insert(self, model: SheetModel):
        self.insert_many([model])

    def insert_many(self, models: List[SheetModel]):
        if not models:
            return

        field_map = models[0].get_field_map()
        mapped_rows = [
            {field_map.get(k, k): v for k, v in model.model_dump().items()}
            for model in models
        ]

        headers = self._get_headers()
        if not headers:
            headers = list(mapped_rows[0].keys())
            cache_headers[self.file_path] = headers
            logger.info(f"Created new CSV with headers: {headers}")
            self._write_rows(headers, [])

        for row in mapped_rows:
            values = [row.get(h, "") for h in headers]
            self._append_row(values)

        logger.info(f"Inserted {len(mapped_rows)} row(s) into CSV")

    def get_all(
        self, model: Type[SheetModel], filters: Optional[Dict[str, Any]] = None
    ):
        if not os.path.exists(self.file_path):
            return []

        with open(self.file_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f, delimiter=CSV_DELIMITER, quoting=CSV_QUOTING)
            field_map = model.generate_field_map()
            data = []

            for row in reader:
                mapped_data = {field_map.get(k, k): v for k, v in row.items()}
                try:
                    item = model(**mapped_data)
                except Exception as e:
                    logger.error(f"Failed to parse row {row}: {e}")
                    continue

                if filters:
                    if all(getattr(item, k, None) == v for k, v in filters.items()):
                        data.append(item)
                else:
                    data.append(item)

            return data

    def get_one(self, model: Type[SheetModel], filters: Dict[str, str]):
        data = self.get_all(model)
        for item in data:
            if all(getattr(item, k, None) == v for k, v in filters.items()):
                return item
        raise NotFoundError(f"Record not found for filters: {filters}")

    def update(
        self,
        model: Type[SheetModel],
        filters: Dict[str, str],
        update_data: Dict[str, str],
    ):
        data = self.get_all(model)
        updated = False

        for item in data:
            if all(getattr(item, k, None) == v for k, v in filters.items()):
                for k, v in update_data.items():
                    setattr(item, k, v)
                updated = True
                break

        if not updated:
            raise NotFoundError(f"Record not found for filters: {filters}")

        headers = self._get_headers()
        rows = [
            [getattr(item, model.generate_field_map().get(h, h), "") for h in headers]
            for item in data
        ]
        self._write_rows(headers, rows)
        logger.info("Updated record in CSV")
        return item

    def delete(self, model: Type[SheetModel], filters: Dict[str, str]):
        data = self.get_all(model)
        new_data = []
        deleted_item = None

        for item in data:
            if all(getattr(item, k, None) == v for k, v in filters.items()):
                deleted_item = item
                continue
            new_data.append(item)

        if not deleted_item:
            raise NotFoundError(f"Record not found for filters: {filters}")

        headers = self._get_headers()
        rows = [
            [getattr(item, model.generate_field_map().get(h, h), "") for h in headers]
            for item in new_data
        ]
        self._write_rows(headers, rows)
        logger.info("Deleted record in CSV")
        return deleted_item

    def delete_all(self, model: Type[SheetModel]):
        headers = self._get_headers()
        if headers:
            self._write_rows(headers, [])
            logger.info("Cleared all records in CSV")
