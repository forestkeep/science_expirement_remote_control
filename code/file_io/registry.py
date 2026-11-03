# code/file_io/registry.py
"""Реестр парсеров и writer'ов.

Один файл = одна граница «регистрация» по ТЗ. Внутри — два словаря,
но никаких фабрик реестров, вложенных провайдеров и т.п.

Список моделей, которые нужно импортировать для срабатывания
@register/@register_writer, задаётся снаружи — в точке вызова
register_all_parsers(). Обычно это main.py. Здесь этот файл
не меняется при добавлении моделей.
"""
from __future__ import annotations

import importlib
import logging
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from .document import RawDocument

logger = logging.getLogger(__name__)


@dataclass
class ParserInfo:
    kind: str
    formats: tuple[str, ...]
    can_parse: Callable[[RawDocument], bool]
    parse: Callable[[RawDocument], Any]
    model_cls: type


@dataclass
class WriterInfo:
    kind: str
    formats: tuple[str, ...]
    can_write: Callable[[Any], bool]
    serialize: Callable[[Any], RawDocument]
    model_cls: type


_PARSERS: dict[str, ParserInfo] = {}
_WRITERS: list[WriterInfo] = []
_WRITER_KINDS: dict[str, WriterInfo] = {}


def register(
    cls: type | None = None,
    *,
    kind: str | None = None,
    formats: tuple[str, ...] | None = None,
):
    """Декоратор: регистрирует модель как semantic parser.

    Модель обязана иметь @classmethod can_parse(doc)->bool и
    @classmethod parse(doc)->Model. kind и formats можно либо передать
    явно в декораторе, либо объявить атрибутами KIND / FORMATS на классе.

    Идемпотентен при повторном импорте того же модуля. Дубликат kind
    другим классом — ошибка на старте, а не «кто последний, тот и прав».
    """

    def _decorate(model_cls: type) -> type:
        k = kind or getattr(model_cls, "KIND", None)
        f = formats or getattr(model_cls, "FORMATS", None)
        if not k or not f:
            raise ValueError(
                f"register: kind/formats not provided for {model_cls.__name__}"
            )
        if not hasattr(model_cls, "can_parse") or not hasattr(model_cls, "parse"):
            raise TypeError(
                f"{model_cls.__name__} must implement classmethods can_parse and parse"
            )
        existing = _PARSERS.get(k)
        if existing is not None:
            if existing.model_cls is model_cls:
                return model_cls  # idempotent re-import
            raise RuntimeError(
                f"register: kind {k!r} already registered by "
                f"{existing.model_cls.__module__}.{existing.model_cls.__name__}"
            )
        _PARSERS[k] = ParserInfo(
            kind=k,
            formats=tuple(f),
            can_parse=model_cls.can_parse,
            parse=model_cls.parse,
            model_cls=model_cls,
        )
        logger.debug("registered parser %r for formats %s", k, f)
        return model_cls

    if cls is not None:
        return _decorate(cls)
    return _decorate


def register_writer(
    cls: type | None = None,
    *,
    kind: str | None = None,
    formats: tuple[str, ...] | None = None,
):
    """Симметрично register, для writer'ов.

    Модель обязана иметь @classmethod can_write(obj)->bool и
    @classmethod serialize(obj)->RawDocument. Дубликат kind другим
    классом — ошибка на старте.
    """

    def _decorate(model_cls: type) -> type:
        k = kind or getattr(model_cls, "KIND", None)
        f = formats or getattr(
            model_cls, "WRITER_FORMATS", getattr(model_cls, "FORMATS", None)
        )
        if not k or not f:
            raise ValueError(
                f"register_writer: kind/formats not provided for {model_cls.__name__}"
            )
        if not hasattr(model_cls, "can_write") or not hasattr(model_cls, "serialize"):
            raise TypeError(
                f"{model_cls.__name__} must implement classmethods can_write and serialize"
            )
        existing = _WRITER_KINDS.get(k)
        if existing is not None:
            if existing.model_cls is model_cls:
                return model_cls
            raise RuntimeError(
                f"register_writer: kind {k!r} already registered by "
                f"{existing.model_cls.__module__}.{existing.model_cls.__name__}"
            )
        info = WriterInfo(
            kind=k,
            formats=tuple(f),
            can_write=model_cls.can_write,
            serialize=model_cls.serialize,
            model_cls=model_cls,
        )
        _WRITERS.append(info)
        _WRITER_KINDS[k] = info
        logger.debug("registered writer %r for formats %s", k, f)
        return model_cls

    if cls is not None:
        return _decorate(cls)
    return _decorate


def register_all_parsers(model_modules: Iterable[str]) -> None:
    """Импортирует модельные модули, триггеря @register/@register_writer.

    :param model_modules: имена модулей, в которых объявлены модели
        с декораторами. Список задаёт вызывающий (обычно main.py);
        registry.py при добавлении модели не меняется.

    Идемпотентна: повторный вызов ничего не делает (Python кэширует
    импорт, а register/register_writer идемпотентны по kind). Ошибки
    отдельных модулей логируются и не валят остальные — приложение
    продолжает старт с тем набором моделей, которые импортировались
    успешно.
    """
    for module_name in model_modules:
        try:
            importlib.import_module(module_name)
        except ImportError as exc:
            logger.warning(
                "register_all_parsers: import %r failed: %s", module_name, exc
            )
        except Exception as exc:
            logger.exception(
                "register_all_parsers: import %r raised %s", module_name, exc
            )


def assert_registry_complete(
    expected_kinds: list[str] | tuple[str, ...] | None = None,
) -> None:
    """Проверяет, что все ожидаемые kind зарегистрировали парсер.

    Вызывается на старте (main.py). Ловит опечатку в @register / забытый
    декоратор у новой модели — иначе она всплывёт только в момент
    load_file() с UnknownKindError у пользователя.
    """
    if not expected_kinds:
        return
    missing = [k for k in expected_kinds if k not in _PARSERS]
    if missing:
        raise RuntimeError(
            f"assert_registry_complete: missing parsers for kinds: {missing}"
        )


def assert_writer_registry_complete(
    expected_kinds: list[str] | tuple[str, ...] | None = None,
) -> None:
    """Симметрично assert_registry_complete — по реестру writer'ов.

    Вызывается на старте (main.py). Ловит «модель зарегистрировала парсер,
    но забыла @register_writer» — иначе это всплывёт только при попытке
    save_file() у пользователя.

    Read-only модели (например BufferData) сюда не включаются — у них
    writer'а нет by design.
    """
    if not expected_kinds:
        return
    missing = [k for k in expected_kinds if k not in _WRITER_KINDS]
    if missing:
        raise RuntimeError(
            f"assert_writer_registry_complete: missing writers for kinds: {missing}"
        )


def parsers_snapshot() -> dict[str, ParserInfo]:
    """Для тестов и диагностики: снимок реестра парсеров."""
    return dict(_PARSERS)


def writers_snapshot() -> list[WriterInfo]:
    """Для тестов и диагностики: снимок реестра writer'ов."""
    return list(_WRITERS)