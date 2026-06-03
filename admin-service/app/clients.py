"""Тонкие httpx-обёртки над catalog-service и orders-service.

admin-service выступает аутентифицированным шлюзом (BFF): панель управления
ходит только сюда, а сюда — проксирует запросы в нужный микросервис.
"""

import httpx
from fastapi import HTTPException

from .config import settings


def _forward(response: httpx.Response):
    """Пробрасываем ответ апстрима как есть (тело + код), ошибки → HTTPException."""
    if response.status_code >= 400:
        try:
            detail = response.json().get("detail", response.text)
        except Exception:
            detail = response.text
        raise HTTPException(response.status_code, detail)
    if response.status_code == 204 or not response.content:
        return None
    return response.json()


class _Upstream:
    def __init__(self, base_url: str):
        self.base_url = base_url

    def _client(self) -> httpx.Client:
        # trust_env=False — обращения между сервисами идут напрямую по docker-сети,
        # системные HTTP(S)_PROXY/NO_PROXY игнорируем (иначе ломаемся на чужих прокси).
        return httpx.Client(
            base_url=self.base_url,
            timeout=settings.upstream_request_timeout,
            trust_env=False,
        )

    def get(self, path: str, params: dict | None = None):
        try:
            with self._client() as c:
                return _forward(c.get(path, params=params))
        except httpx.RequestError as exc:
            raise HTTPException(502, f"Upstream unavailable: {exc}")

    def post(self, path: str, json: dict):
        try:
            with self._client() as c:
                return _forward(c.post(path, json=json))
        except httpx.RequestError as exc:
            raise HTTPException(502, f"Upstream unavailable: {exc}")

    def put(self, path: str, json: dict):
        try:
            with self._client() as c:
                return _forward(c.put(path, json=json))
        except httpx.RequestError as exc:
            raise HTTPException(502, f"Upstream unavailable: {exc}")

    def patch(self, path: str, json: dict):
        try:
            with self._client() as c:
                return _forward(c.patch(path, json=json))
        except httpx.RequestError as exc:
            raise HTTPException(502, f"Upstream unavailable: {exc}")

    def delete(self, path: str):
        try:
            with self._client() as c:
                return _forward(c.delete(path))
        except httpx.RequestError as exc:
            raise HTTPException(502, f"Upstream unavailable: {exc}")


catalog = _Upstream(settings.catalog_service_url)
orders = _Upstream(settings.orders_service_url)
