from __future__ import annotations

import ast
import builtins
import operator
import sys
import typing
from dataclasses import MISSING
from dataclasses import Field
from typing import Any
from typing import ForwardRef
from typing import Optional
from typing import TextIO
from typing import Type
from typing import Union
from typing import cast

from type_yaml.utils import get_part_of_string

try:
    from typing import TypeAlias  # type: ignore
    from typing import TypeGuard  # type: ignore
except ImportError:  # pragma: no cover
    from typing_extensions import TypeAlias
    from typing_extensions import TypeGuard

TypeLike: TypeAlias = Union[Type, str]


class TypeHandler:
    @staticmethod
    def is_list(type_: Type) -> TypeGuard[Type[list]]:
        origin = typing.get_origin(type_)
        if origin is not None:
            type_ = origin

        return type_ == list or type_ == typing.List

    @staticmethod
    def get_list_item(type_: Type[list]) -> TypeLike:
        assert InterpreterBase.is_list(type_)
        if hasattr(type_, "__args__"):
            return type_.__args__[0]
        else:
            return Any

    @staticmethod
    def is_dict(type_: Type) -> TypeGuard[Type[dict]]:
        origin = typing.get_origin(type_)
        if origin is not None:
            type_ = origin

        return type_ == dict or type_ == typing.Dict

    @staticmethod
    def get_dict_key_item(type_: Type[dict]) -> tuple[TypeLike, TypeLike]:
        assert InterpreterBase.is_dict(type_)
        if hasattr(type_, "__args__"):
            return type_.__args__[0], type_.__args__[1]
        else:
            return Any, Any

    @staticmethod
    def is_set(type_: Type) -> TypeGuard[Type[set]]:
        origin = typing.get_origin(type_)
        if origin is not None:
            type_ = origin

        return type_ == set or type_ == typing.Set

    @staticmethod
    def get_set_item(type_: Type[set]) -> TypeLike:
        assert InterpreterBase.is_set(type_)
        if hasattr(type_, "__args__"):
            return type_.__args__[0]
        else:
            return Any

    @staticmethod
    def is_tuple(type_: Type) -> TypeGuard[Type[tuple]]:
        origin = typing.get_origin(type_)
        if origin is not None:
            type_ = origin

        return type_ == tuple or type_ == typing.Tuple

    @staticmethod
    def get_tuple_item(type_: Type[tuple]) -> tuple[TypeLike, ...]:
        assert InterpreterBase.is_tuple(type_)
        if hasattr(type_, "__args__"):
            return type_.__args__
        else:
            return Any, ...

    @staticmethod
    def is_dataclass(type_: Type) -> bool:
        return hasattr(type_, "__dataclass_fields__")

    @staticmethod
    def get_dataclass_fields(type_: Type) -> dict[str, Field]:
        assert InterpreterBase.is_dataclass(type_)
        return type_.__dataclass_fields__  # type: ignore

    @staticmethod
    def has_default(field: Field) -> bool:
        return field.default is not MISSING or field.default_factory is not MISSING

    @staticmethod
    def get_default(field: Field) -> typing.Any:
        if field.default is not MISSING:
            return field.default
        elif field.default_factory is not MISSING:
            assert field.default_factory is not MISSING
            return field.default_factory()
        else:
            raise ValueError("Field has no default value")  # pragma: no cover

    @staticmethod
    def is_union(type_: Type) -> TypeGuard[Type[typing.Union]]:
        origin = typing.get_origin(type_)
        if origin is not None:
            type_ = origin

        return type_ == typing.Union

    @staticmethod
    def get_union_item(type_: Type[typing.Union]) -> tuple[TypeLike, ...]:
        assert InterpreterBase.is_union(type_)
        if hasattr(type_, "__args__"):
            return type_.__args__  # type: ignore
        else:
            raise ValueError("Union has no args")  # pragma: no cover

    def type_to_str(self, type_: TypeLike) -> str:
        if isinstance(type_, str):
            return type_

        if isinstance(type_, ForwardRef):
            return type_.__forward_arg__

        # at this time, PyCharm doesn't support TypeGuard
        if self.is_list(type_):
            return (
                f"list[{self.type_to_str(self.get_list_item(cast(Type[list], type_)))}]"
            )
        elif self.is_dict(type_):
            key, item = self.get_dict_key_item(cast(Type[dict], type_))
            return f"dict[{self.type_to_str(key)}, " f"{self.type_to_str(item)}]"
        elif self.is_set(type_):
            return f"set[{self.type_to_str(self.get_set_item(cast(Type[set], type_)))}]"
        elif self.is_tuple(type_):
            args_str = ", ".join(
                self.type_to_str(t)
                for t in self.get_tuple_item(cast(Type[tuple], type_))
            )
            return f"tuple[{args_str}]"
        elif type_ is ...:
            return "..."

        return type_.__name__


class InterpreterBase(TypeHandler):

    builtin_type_name_map = {
        name: value for name, value in vars(builtins).items() if isinstance(value, type)
    }

    if sys.version_info < (3, 9):  # pragma: no cover
        builtin_type_name_map["list"] = typing.List
        builtin_type_name_map["dict"] = typing.Dict
        builtin_type_name_map["set"] = typing.Set
        builtin_type_name_map["tuple"] = typing.Tuple  # type: ignore

    builtin_type_name_map["List"] = typing.List
    builtin_type_name_map["Dict"] = typing.Dict
    builtin_type_name_map["Set"] = typing.Set
    builtin_type_name_map["Tuple"] = typing.Tuple  # type: ignore

    builtin_type_name_map["Any"] = typing.Any  # type: ignore
    builtin_type_name_map["Union"] = typing.Union  # type: ignore

    def __init__(
        self,
        type_: TypeLike,
        stream: TextIO,
        *,
        type_name_map: Optional[dict[str, Type]] = None,
        globalns: Optional[dict[str, Any]] = None,
        localns: Optional[dict[str, Any]] = None,
    ) -> None:
        type_name_map_ = self.builtin_type_name_map.copy()
        for key, value in (globalns or {}).items():
            type_name_map_.setdefault(key, value)
        for key, value in (localns or {}).items():
            type_name_map_.setdefault(key, value)
        if type_name_map is not None:
            type_name_map_.update(type_name_map)

        self.type = type_
        self.stream = stream
        self.type_name_map = type_name_map_

    def eval_typelike(self, type_: TypeLike) -> Type:
        if isinstance(type_, ForwardRef):
            type_ = type_.__forward_arg__

        if isinstance(type_, str):
            try:
                type_ast = ast.parse(type_, mode="eval")
            except SyntaxError:  # pragma: no cover
                raise ValueError(f"invalid type: {type_}")

            if not isinstance(type_ast, ast.Expression):
                raise ValueError(f"invalid type: {type_}")  # pragma: no cover

            expr = type_ast.body

            if isinstance(expr, ast.Name):
                if expr.id not in self.type_name_map:
                    raise ValueError(f"invalid type: {type_}")  # pragma: no cover

                return self.type_name_map[expr.id]

            elif isinstance(expr, ast.Subscript):
                value = get_part_of_string(
                    type_,
                    expr.value.lineno - 1,
                    expr.value.col_offset,
                    expr.value.end_lineno - 1,  # type: ignore
                    expr.value.end_col_offset,  # type: ignore
                )
                s_value: ast.expr | ast.slice
                if isinstance(expr.slice, ast.Index):  # pragma: no cover
                    s_value = expr.slice.value
                else:
                    s_value = expr.slice

                item: str | tuple[str, ...]
                if isinstance(s_value, ast.Tuple):
                    args_sting: list[str] = []
                    for arg in s_value.elts:
                        args_sting.append(
                            get_part_of_string(
                                type_,
                                arg.lineno - 1,
                                arg.col_offset,
                                arg.end_lineno - 1,  # type: ignore
                                arg.end_col_offset,  # type: ignore
                            )
                        )
                    item = tuple(args_sting)
                else:
                    item = get_part_of_string(
                        type_,
                        s_value.lineno - 1,
                        s_value.col_offset,
                        s_value.end_lineno - 1,  # type: ignore
                        s_value.end_col_offset,  # type: ignore
                    )

                try:
                    return operator.getitem(  # type: ignore
                        self.eval_typelike(value), item  # type: ignore
                    )
                except TypeError:  # pragma: no cover
                    raise ValueError(f"invalid type: {type_}")

            elif isinstance(expr, ast.Constant) and isinstance(expr.value, str):
                if expr.value not in self.type_name_map:
                    raise ValueError(f"invalid type: {type_}")  # pragma: no cover

                return self.type_name_map[expr.value]

            elif isinstance(expr, ast.Constant) and expr.value is ...:
                return ...  # type: ignore

            elif isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.BitOr):
                left = self.eval_typelike(
                    get_part_of_string(
                        type_,
                        expr.left.lineno - 1,
                        expr.left.col_offset,
                        expr.left.end_lineno - 1,  # type: ignore
                        expr.left.end_col_offset,  # type: ignore
                    )
                )
                right = self.eval_typelike(
                    get_part_of_string(
                        type_,
                        expr.right.lineno - 1,
                        expr.right.col_offset,
                        expr.right.end_lineno - 1,  # type: ignore
                        expr.right.end_col_offset,  # type: ignore
                    )
                )
                return typing.Union[left, right]  # type: ignore

            else:
                raise ValueError(f"invalid type: {type_}")  # pragma: no cover

        else:
            return type_

    def load(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError

    def _load(self, *args: Any, **kwargs: Any) -> Any:
        raise NotImplementedError


class DumperBase(TypeHandler):
    def __init__(
        self,
        value: Any,
        stream: TextIO,
    ):
        self.value = value
        self.stream = stream

    def dump(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    def _dump(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError
