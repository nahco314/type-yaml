from __future__ import annotations

from textwrap import indent
from typing import Any
from typing import Optional
from typing import TextIO
from typing import Type
from typing import Union
from typing import cast

from yaml import DocumentEndEvent
from yaml import DocumentStartEvent
from yaml import Event
from yaml import MappingEndEvent
from yaml import MappingStartEvent
from yaml import Node
from yaml import SafeDumper
from yaml import SafeLoader
from yaml import ScalarEvent
from yaml import SequenceEndEvent
from yaml import SequenceStartEvent
from yaml import StreamEndEvent
from yaml import StreamStartEvent
from yaml import dump
from yaml import parse

import type_yaml.errors as errors
from type_yaml.base import DumperBase
from type_yaml.base import InterpreterBase
from type_yaml.base import TypeHandler
from type_yaml.base import TypeLike


class YamlInterpreter(InterpreterBase):
    EVENT_NAME: dict[Type[Event], str] = {
        SequenceStartEvent: "sequence",
        MappingStartEvent: "mapping",
        ScalarEvent: "scalar",
    }

    def __init__(
        self,
        type_: TypeLike,
        stream: TextIO,
        *,
        multi_document: bool = False,
        loader: Type = SafeLoader,
        true_strings: tuple[str, ...] = ("true", "yes", "on", "1"),
        false_strings: tuple[str, ...] = ("false", "no", "off", "0"),
        type_name_map: Optional[dict[str, Type]] = None,
        globalns: Optional[dict[str, Any]] = None,
        localns: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(
            type_,
            stream,
            type_name_map=type_name_map,
            globalns=globalns,
            localns=localns,
        )
        self.multi_document = multi_document
        self.event_list: list[Event] = list(parse(stream, Loader=loader))
        self.pos = 0

        self.true_strings = true_strings
        self.false_strings = false_strings

    @property
    def event(self) -> Event:
        return self.event_list[self.pos]

    def get_and_advance(self) -> Event:
        event = self.event
        self.advance()
        return event

    def advance(self) -> None:
        self.pos += 1

    def mark(self) -> int:
        return self.pos

    def reset(self, pos: int) -> None:
        self.pos = pos

    def build_error(
        self, type_: TypeLike, found_event: Event, message: Optional[str] = None
    ) -> errors.YamlTypeError:
        event_name = self.EVENT_NAME[type(found_event)]
        if message is None:
            message = f"expected {self.type_to_str(type_)}, {event_name} found"
        return errors.YamlTypeError(found_event.start_mark, message)

    def _load_int(self, type_: Type[int], typelike: TypeLike) -> int:
        event = self.get_and_advance()
        if not isinstance(event, ScalarEvent):
            raise self.build_error(typelike, event)  # pragma: no cover

        try:
            res = int(event.value)
        except ValueError:  # pragma: no cover
            raise self.build_error(
                typelike, event, f"expected int, {event.value!r} found"
            )

        return res

    def _load_str(self, type_: Type[str], typelike: TypeLike) -> str:
        event = self.get_and_advance()
        if not isinstance(event, ScalarEvent):
            raise self.build_error(typelike, event)  # pragma: no cover

        return event.value

    def _load_float(self, type_: Type[float], typelike: TypeLike) -> float:
        event = self.get_and_advance()
        if not isinstance(event, ScalarEvent):
            raise self.build_error(typelike, event)  # pragma: no cover

        try:
            res = float(event.value)
        except ValueError:  # pragma: no cover
            raise self.build_error(
                typelike, event, f"expected float, {event.value!r} found"
            )

        return res

    def _load_bool(self, type_: Type[bool], typelike: TypeLike) -> bool:
        event = self.get_and_advance()
        if not isinstance(event, ScalarEvent):
            raise self.build_error(typelike, event)  # pragma: no cover

        if event.value in self.true_strings:
            return True
        elif event.value in self.false_strings:
            return False
        else:
            raise self.build_error(  # pragma: no cover
                typelike, event, f"expected bool, {event.value!r} found"
            )

    def _load_list(self, type_: Type[list], typelike: TypeLike) -> list[Any]:
        event = self.get_and_advance()
        if not isinstance(event, SequenceStartEvent):
            raise self.build_error(typelike, event)  # pragma: no cover

        item_type = self.get_list_item(cast(Type[list], type_))

        res = []
        while not isinstance(self.event, SequenceEndEvent):
            res.append(self._load(item_type))

        self.advance()

        return res

    def _load_multi_document(self, type_: Type[list], typelike: TypeLike) -> list[Any]:
        item_type = self.get_list_item(cast(Type[list], type_))

        res = []
        while isinstance(self.event, DocumentStartEvent):
            self.advance()
            res.append(self._load(item_type))
            assert isinstance(self.event, DocumentEndEvent)
            self.advance()

        return res

    def _load_dict(self, type_: Type[dict], typelike: TypeLike) -> dict[Any, Any]:
        event = self.get_and_advance()
        if not isinstance(event, MappingStartEvent):
            raise self.build_error(typelike, event)  # pragma: no cover

        key_type, value_type = self.get_dict_key_item(cast(Type[dict], type_))

        res = {}
        while not isinstance(self.event, MappingEndEvent):
            key = self._load(key_type)
            value = self._load(value_type)
            res[key] = value

        self.advance()

        return res

    def _load_set(self, type_: Type[set], typelike: TypeLike) -> set[Any]:
        event = self.get_and_advance()
        if not isinstance(event, SequenceStartEvent):
            raise self.build_error(typelike, event)  # pragma: no cover

        item_type = self.get_set_item(cast(Type[set], type_))

        res = set()
        while not isinstance(self.event, SequenceEndEvent):
            res.add(self._load(item_type))

        self.advance()

        return res

    def _load_tuple(self, type_: Type[tuple], typelike: TypeLike) -> tuple[Any, ...]:
        event = self.get_and_advance()
        if not isinstance(event, SequenceStartEvent):
            raise self.build_error(typelike, event)  # pragma: no cover

        item_types = self.get_tuple_item(cast(Type[tuple], type_))

        if len(item_types) == 2 and self.eval_typelike(item_types[1]) is Ellipsis:
            res = []
            while not isinstance(self.event, SequenceEndEvent):
                res.append(self._load(item_types[0]))

            self.advance()

            return tuple(res)

        else:
            res = []
            for item_type in item_types:
                res.append(self._load(item_type))

            if not isinstance(self.event, SequenceEndEvent):
                raise self.build_error(typelike, self.event)  # pragma: no cover

            self.advance()

            return tuple(res)

    def _load_dataclass(self, type_: Type, typelike: TypeLike) -> Type:
        event = self.get_and_advance()
        if not isinstance(event, MappingStartEvent):
            raise self.build_error(typelike, event)  # pragma: no cover

        fields = self.get_dataclass_fields(type_)

        fields_dict = {}

        while not isinstance(self.event, MappingEndEvent):
            key = self._load(str)

            if key not in fields:
                raise errors.YamlTypeError(  # pragma: no cover
                    self.event.start_mark, f"invalid field: {key!r}"
                )

            field = fields[key]

            if "yaml_type" in field.metadata:
                field_type = field.metadata["yaml_type"]
            else:
                field_type = field.type

            value = self._load(field_type)
            if "yaml_convert" in field.metadata:
                value = field.metadata["yaml_convert"](value)
            fields_dict[key] = value

        for field_name, field in fields.items():
            if field_name not in fields_dict:
                if self.has_default(field):
                    fields_dict[field_name] = self.get_default(field)
                else:
                    raise errors.YamlTypeError(  # pragma: no cover
                        self.event.start_mark, f"missing field {field_name!r}"
                    )

        res = type_(**fields_dict)

        self.advance()

        return res

    def _load_any(self, type_: Type[Any], typelike: TypeLike) -> Any:
        event = self.get_and_advance()
        if isinstance(event, ScalarEvent):
            if event.value in self.true_strings:
                return True
            elif event.value in self.false_strings:
                return False
            else:
                try:
                    return int(event.value)
                except ValueError:
                    try:
                        return float(event.value)
                    except ValueError:
                        return event.value
        elif isinstance(event, SequenceStartEvent):
            res: list[Any] = []
            while not isinstance(self.event, SequenceEndEvent):
                res.append(self._load(Any))
            self.advance()
            return res
        elif isinstance(event, MappingStartEvent):
            res: dict[Any, Any] = {}  # type: ignore
            while not isinstance(self.event, MappingEndEvent):
                key = self._load(Any)
                value = self._load(Any)
                res[key] = value
            self.advance()
            return res
        else:
            raise self.build_error(typelike, event)  # pragma: no cover

    def _load_union(self, type_: Type[Union], typelike: TypeLike) -> Any:
        args = self.get_union_item(type_)
        pos = self.mark()
        errors_list: list[errors.YamlError] = []
        for item_type in args:
            try:
                return self._load(item_type)
            except errors.YamlError as e:
                self.reset(pos)
                errors_list.append(e)
        else:
            args_string = "(" + ", ".join(map(self.type_to_str, args)) + ")"
            error_txt_list = [
                f"failed to parse yaml. expected one of {args_string}",
                "errors for each type:",
            ]
            for type_i, error in zip(args, errors_list):
                error_txt_list.append(f"type: {self.type_to_str(type_i)}")
                error_txt_list.append(indent(str(error), " " * 4))
            raise errors.YamlTypeError(  # pragma: no cover
                self.event.start_mark, "\n".join(error_txt_list)
            )

    def _load(self, typelike: TypeLike) -> Any:
        type_ = self.eval_typelike(typelike)

        if type_ == int:
            return self._load_int(cast(Type[int], type_), typelike)
        elif type_ == str:
            return self._load_str(cast(Type[str], type_), typelike)
        elif type_ == float:
            return self._load_float(cast(Type[float], type_), typelike)
        elif type_ == bool:
            return self._load_bool(cast(Type[bool], type_), typelike)
        elif self.is_list(type_):
            return self._load_list(cast(Type[list], type_), typelike)
        elif self.is_dict(type_):
            return self._load_dict(cast(Type[dict], type_), typelike)
        elif self.is_set(type_):
            return self._load_set(cast(Type[set], type_), typelike)
        elif self.is_tuple(type_):
            return self._load_tuple(cast(Type[tuple], type_), typelike)
        elif self.is_dataclass(type_):
            return self._load_dataclass(cast(Type, type_), typelike)
        elif type_ == Any:
            return self._load_any(cast(Type[Any], type_), typelike)
        elif self.is_union(type_):
            return self._load_union(cast(Type[Union[Any]], type_), typelike)
        else:
            raise ValueError(f"unsupported type: {type_}")  # pragma: no cover

    def load(self) -> Any:
        assert isinstance(self.get_and_advance(), StreamStartEvent)
        if isinstance(self.event, StreamEndEvent):
            raise errors.YamlTypeError(  # pragma: no cover
                self.event.start_mark, "empty stream, expected data"
            )

        if self.multi_document:
            type_ = self.eval_typelike(self.type)
            if not self.is_list(type_):
                raise ValueError("multi_document requires list type")
            type_ = cast(Type[list], type_)
            res = self._load_multi_document(type_, self.type)
        else:
            assert isinstance(self.get_and_advance(), DocumentStartEvent)

            res = self._load(self.type)

            if not isinstance(self.get_and_advance(), DocumentEndEvent):
                raise errors.YamlTypeError(  # pragma: no cover
                    self.event.start_mark, "expected document end"
                )

        if not isinstance(self.get_and_advance(), StreamEndEvent):
            raise errors.YamlTypeError(  # pragma: no cover
                self.event.start_mark, "expected stream end"
            )

        return res


class RealYamlDumper(SafeDumper, TypeHandler):
    def represent_data(self, data: Any) -> Node:
        if self.is_dataclass(type(data)):
            fields = self.get_dataclass_fields(type(data))
            dict_ = {}
            for field_name in fields:
                dict_[field_name] = getattr(data, field_name)

            return self.represent_data(dict_)

        return super().represent_data(data)


class YamlDumper(DumperBase):
    def __init__(
        self,
        value: Any,
        stream: TextIO,
        *,
        dumper: Type = RealYamlDumper,
    ):
        super().__init__(value, stream)
        self.dumper = dumper

    def dump(self) -> None:
        self._dump(self.value)

    def _dump(self, value: Any) -> None:
        dump(value, self.stream, Dumper=self.dumper, sort_keys=False)
