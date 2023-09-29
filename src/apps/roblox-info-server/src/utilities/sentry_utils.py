import logging
from typing import Optional, Union, Callable, Mapping, Tuple
from sentry_sdk.utils import qualname_from_function
from sentry_sdk.tracing import Span, NoOpSpan
from constants import *
import sentry_sdk
import asyncio
import inspect


def trace(op: Optional[str] = None, description: Union[Optional[str], Callable[[Tuple[any], Mapping[str, any]], str]] = None):
    working_op = op or "function"
    working_description = description
    
    def inner(func, *args, **kwargs):
        async def wrapper(*inner_args, **inner_kwargs):
            inner_op = working_op
            inner_description = working_description(*inner_args, **inner_kwargs) if callable(working_description) else working_description or qualname_from_function(func)     
            parent_span = inner_kwargs.get("parent_span", None)
                        
            # with parent_span.start_child(op=inner_op, description=inner_description) if parent_span else (sentry_sdk.start_span(op=inner_op, description=inner_description) or NoOpSpan()) as span:
            with parent_span.start_child(op=inner_op, description=inner_description) if parent_span else (sentry_sdk.start_span(op=inner_op, description=inner_description) or NoOpSpan()) as span:
                if inspect.iscoroutinefunction(func):
                    return await func(*inner_args, **inner_kwargs)
                else:
                    return func(*inner_args, **inner_kwargs)
        return wrapper
    return inner