from typing import Any, List, Type, Dict, Optional
import gspread
from gspread.exceptions import WorksheetNotFound
from src.logger_utils import get_logger
from src.interfaces.base import BaseSheetDB
from src.interfaces.model import SheetModel
from src.exceptions import NotFoundError

logger = get_logger("gsheetdb")

cache_headers: Dict[str, List[str]] = {}


class GoogleSheetDB(BaseSheetDB):
    def __init__(self, creds_fn, spreadsheet_id: str):
        self.creds_fn = creds_fn
        self.spreadsheet_id = spreadsheet_id
        self._client = None

    def _get_client(self):
        if not self._client:
            creds = self.creds_fn()
            self._client = gspread.authorize(creds)
        return self._client

    def _get_worksheet(self, sheet_name: str, headers: List[str] = None):
        client = self._get_client()
        spreadsheet = client.open_by_key(self.spreadsheet_id)

        try:
            return spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound:
            if headers is None:
                raise ValueError(
                    f"Sheet '{sheet_name}' not found and no headers provided."
                )
            ws = spreadsheet.add_worksheet(
                title=sheet_name, rows="100", cols=str(len(headers))
            )
            ws.append_row(headers)
            cache_headers[sheet_name] = headers
            logger.info(f"Created new worksheet: {sheet_name} with headers: {headers}")
            return ws

    def _get_headers(self, ws, sheet_name):
        if sheet_name in cache_headers:
            return cache_headers[sheet_name]
        headers = ws.row_values(1)
        cache_headers[sheet_name] = headers
        return headers

    def insert(self, model: SheetModel):
        self.insert_many([model])

    def insert_many(self, models: List[SheetModel]):
        if not models:
            return

        sheet_name = models[0].get_sheet_name()
        field_map = models[0].get_field_map()
        mapped_rows = [
            {field_map.get(k, k): v for k, v in m.model_dump().items()} for m in models
        ]

        ws = self._get_worksheet(sheet_name, headers=list(mapped_rows[0].keys()))
        headers = self._get_headers(ws, sheet_name)
        values = [[row.get(h, "") for h in headers] for row in mapped_rows]
        ws.append_rows(values)
        logger.info(f"Inserted {len(values)} row(s) into {sheet_name}")

    def get_all(
        self, model: Type[SheetModel], filters: Optional[Dict[str, Any]] = None
    ):
        sheet_name = model.get_class_sheet_name()
        ws = self._get_worksheet(sheet_name)
        headers = self._get_headers(ws, sheet_name)
        rows = ws.get_all_values()

        field_map = model.generate_field_map()
        data = []

        for row in rows[1:]:  # Skip header
            model_data = {
                field_map.get(header, header): value
                for header, value in zip(headers, row)
            }
            try:
                item = model(**model_data)
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

        for idx, item in enumerate(data):
            if all(getattr(item, k, None) == v for k, v in filters.items()):
                for k, v in update_data.items():
                    setattr(item, k, v)

                sheet_name = model.get_class_sheet_name()
                ws = self._get_worksheet(sheet_name)
                headers = self._get_headers(ws, sheet_name)

                mapped_row = []
                for header in headers:
                    field_name = model.generate_field_map().get(header, header)
                    value = getattr(item, field_name, "")
                    mapped_row.append(value)

                row_number = idx + 2  # 1 for header, 1-based index
                cell_range = f"A{row_number}:{chr(64 + len(mapped_row))}{row_number}"
                ws.update(cell_range, [mapped_row])

                logger.info(f"Updated record in {sheet_name} at row {row_number}")
                return item

        raise NotFoundError(f"Record not found for filters: {filters}")

    def delete(self, model: Type[SheetModel], filters: Dict[str, str]):
        data = self.get_all(model)
        for item in data:
            if all(getattr(item, k, None) == v for k, v in filters.items()):
                self.delete_row(model, item)
                return item
        raise NotFoundError(f"Record not found for filters: {filters}")

    def delete_row(self, model: Type[SheetModel], item: SheetModel):
        client = self._get_client()
        spreadsheet = client.open_by_key(self.spreadsheet_id)
        sheet = spreadsheet.worksheet(model.sheet_name)
        row_number = int(item.id) + 1
        sheet.delete_rows(row_number)

    def delete_all(self, model: Type[SheetModel]):
        sheet_name = model.get_class_sheet_name()
        ws = self._get_worksheet(sheet_name)
        rows = ws.get_all_values()
        if len(rows) <= 1:
            logger.info(f"No data to clear on sheet '{sheet_name}'")
            return

        num_cols = len(rows[0])
        clear_range = f"A2:{chr(65 + num_cols - 1)}{len(rows)}"
        ws.batch_clear([clear_range])
        logger.info(f"Cleared {len(rows) - 1} row(s) from sheet '{sheet_name}'")
