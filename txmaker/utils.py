import json
from decimal import Decimal
from functools import partial, wraps
from typing import Any, Awaitable, Callable, Dict, Optional, Type

from aiohttp import web
from pydantic import BaseModel, ValidationError


class DecimalJsonEncoder(json.JSONEncoder):
    def default(self, obj: Any) -> str:
        if isinstance(obj, Decimal):
            return str(obj)
        return super().default(obj)


json_dumps = partial(json.dumps, cls=DecimalJsonEncoder, indent=2)
json_response = partial(web.json_response, dumps=json_dumps)


def error_response(code: str, message: Optional[str] = None, *, details: Optional[Dict[str, Any]] = None,
                   status_code: int = 400) -> web.Response:
    error = {
        'code': code,
        'message': message,
    }
    if details is not None:
        error['details'] = details  # type: ignore
    return json_response({'error': error}, status=status_code)


AIOHTTP_HANDLER = Callable[[web.Request, BaseModel], Awaitable[web.Response]]


def validate_request(req_model: Type[BaseModel]) -> Callable[[AIOHTTP_HANDLER], AIOHTTP_HANDLER]:
    def decorator(handler: AIOHTTP_HANDLER) -> AIOHTTP_HANDLER:
        async def wrapped_handler(request: web.Request) -> web.Response:
            body = await request.read() if request.can_read_body else '{}'
            try:
                req_obj = req_model.parse_raw(body, content_type='application/json')
            except ValidationError as e:
                return error_response('invalid_request_schema', 'Your request does not match the spec',
                                      details={'debug_info': e.errors(), 'json_schema': req_model.schema()})
            return await handler(request, req_obj)
        return wraps(handler)(wrapped_handler)
    return decorator
