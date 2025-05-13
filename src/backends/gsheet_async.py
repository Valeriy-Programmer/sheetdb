from typing import Any, List, Type, Dict, Optional
from gspread_asyncio import AsyncioGspreadClientManager
from gspread.exceptions import WorksheetNotFound
from src.logger_utils import get_logger
from src.interfaces.base import BaseSheetDB
from src.interfaces.model import SheetModel
from src.exceptions import NotFoundError

logger = get_logger("gsheetdb_async")

cache_headers: Dict[str, List[str]] = {}


class AsyncGoogleSheetDB(BaseSheetDB):
    def __init__(self, creds_fn, spreadsheet_id: str):
        self.creds_fn = creds_fn
        self.spreadsheet_id = spreadsheet_id
        self.agcm = AsyncioGspreadClientManager(creds_fn)
        self._client = None

    async def _get_client(self):
        if not self._client:
            self._client = await self.agcm.authorize()
        return self._client

    async def _get_worksheet(self, client, sheet_name: str, headers: List[str] = None):
        spreadsheet = await client.open_by_key(self.spreadsheet_id)
        try:
            return await spreadsheet.worksheet(sheet_name)
        except WorksheetNotFound:
            if headers is None:
                raise ValueError(
                    f"Sheet '{sheet_name}' not found and no headers provided to create it."
                )
            ws = await spreadsheet.add_worksheet(
                title=sheet_name, rows="100", cols=str(len(headers))
            )
            await ws.append_row(headers)
            cache_headers[sheet_name] = headers
            logger.info(f"Created new worksheet: {sheet_name} with headers: {headers}")
            return ws

    async def _get_headers(self, ws, sheet_name):
        if sheet_name in cache_headers:
            return cache_headers[sheet_name]
        headers = await ws.row_values(1)
        cache_headers[sheet_name] = headers
        return headers

    async def insert(self, model: SheetModel):
        await self.insert_many([model])

    async def insert_many(self, models: List[SheetModel]):
        if not models:
            return

        client = await self._get_client()
        sheet_name = models[0].get_sheet_name()

        # Получаем field_map для экземпляра модели
        field_map = models[0].get_field_map()
        if not isinstance(field_map, dict):
            raise ValueError(f"Invalid field_map for {models[0]}: {field_map}")

        mapped_rows = []
        for model in models:
            raw = {field_map.get(k, k): v for k, v in model.model_dump().items()}
            mapped_rows.append(raw)

        ws = await self._get_worksheet(
            client, sheet_name, headers=list(mapped_rows[0].keys())
        )
        headers = await self._get_headers(ws, sheet_name)

        values = [[row.get(h, "") for h in headers] for row in mapped_rows]
        await ws.append_rows(values)
        logger.info(f"Inserted {len(values)} row(s) into {sheet_name}")

    async def get_all(
        self, model: Type[SheetModel], filters: Optional[Dict[str, Any]] = None
    ):
        client = await self._get_client()
        sheet_name = model.get_class_sheet_name()
        ws = await self._get_worksheet(client, sheet_name)

        headers = await self._get_headers(ws, sheet_name)
        rows = await ws.get_all_values()

        # Получаем маппинг для переворота
        field_map = model.generate_field_map()

        data = []
        for row in rows[1:]:  # Пропускаем заголовок
            # Преобразуем полученные данные с учетом маппинга полей
            model_data = {
                field_map.get(header, header): value
                for header, value in zip(headers, row)
            }

            # Создаем объект модели с преобразованными данными
            try:
                item = model(**model_data)
            except Exception as e:
                logger.error(f"Failed to parse row {row}: {e}")
                continue

            # Фильтрация по условиям
            if filters:
                match = True
                for key, value in filters.items():
                    if getattr(item, key, None) != value:
                        match = False
                        break
                if match:
                    data.append(item)
            else:
                data.append(item)

        return data

    async def get_one(self, model: Type[SheetModel], filters: Dict[str, str]):
        """Получить одну запись по фильтру."""
        # Получаем все данные
        data = await self.get_all(model)

        # Ищем запись по фильтру
        for item in data:
            match = True
            for key, value in filters.items():
                if getattr(item, key, None) != value:
                    match = False
                    break
            if match:
                return item

        # Если не нашли - выбрасываем исключение
        raise NotFoundError(f"Record not found for filters: {filters}")

    async def update(
        self,
        model: Type[SheetModel],
        filters: Dict[str, str],
        update_data: Dict[str, str],
    ):
        """Обновить запись в Google Sheets."""
        data = await self.get_all(model)

        for idx, item in enumerate(data):
            if all(getattr(item, k, None) == v for k, v in filters.items()):
                # Применяем обновления к объекту
                for k, v in update_data.items():
                    setattr(item, k, v)

                client = await self._get_client()
                sheet_name = model.get_class_sheet_name()
                ws = await self._get_worksheet(client, sheet_name)
                headers = await self._get_headers(ws, sheet_name)

                # Подготовка данных для обновления
                mapped_row = []
                for header in headers:
                    field_name = model.generate_field_map().get(header, header)
                    value = getattr(item, field_name, "")
                    mapped_row.append(value)

                # Строка для обновления (плюс 2: одна строка заголовков + индекс с 0)
                row_number = idx + 2

                range_notation = (
                    f"A{row_number}:{chr(64 + len(mapped_row))}{row_number}"
                )
                await ws.update(range_notation, [mapped_row])

                logger.info(f"Updated record in {sheet_name} at row {row_number}")
                return item

        raise NotFoundError(f"Record not found for filters: {filters}")

    async def delete(self, model: Type[SheetModel], filters: Dict[str, str]):
        """Удалить запись из базы данных по фильтру."""
        # Получаем все данные
        data = await self.get_all(model)

        # Ищем запись по фильтру
        for item in data:
            match = True
            for key, value in filters.items():
                if getattr(item, key, None) != value:
                    match = False
                    break
            if match:
                # Удаляем запись
                await self.delete_row(model, item)
                return item

        # Если запись не найдена, выбрасываем исключение
        raise NotFoundError(f"Record not found for filters: {filters}")

    async def delete_row(self, model: Type[SheetModel], item: SheetModel):
        """Удалить строку из Google Sheets."""
        client = await self._get_client()  # Получаем клиент
        spreadsheet = await client.open_by_key(self.spreadsheet_id)  # Добавляем await
        sheet = await spreadsheet.worksheet(model.sheet_name)  # Добавляем await

        # Находим строку с данными, учитывая, что первая строка — это заголовок
        row_number = int(item.id) + 1  # Сдвигаем на 1, чтобы пропустить заголовок
        await sheet.delete_rows(row_number)  # Удаляем строку с данными

    async def delete_all(self, model: Type[SheetModel]):
        """Быстро очистить все записи на листе, кроме заголовка."""
        client = await self._get_client()
        sheet_name = model.get_class_sheet_name()
        ws = await self._get_worksheet(client, sheet_name)

        rows = await ws.get_all_values()
        if len(rows) <= 1:
            logger.info(f"No data to clear on sheet '{sheet_name}'")
            return

        # Определяем диапазон строк, которые нужно очистить
        num_cols = len(rows[0])  # Считаем количество колонок по заголовку

        clear_range = f"A2:{chr(65 + num_cols - 1)}{len(rows)}"  # например A2:C100
        await ws.batch_clear([clear_range])

        logger.info(f"Cleared {len(rows) - 1} row(s) from sheet '{sheet_name}'")
