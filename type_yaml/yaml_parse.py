from __future__ import annotations

import os
from tempfile import mkstemp
from typing import Any
from typing import TextIO
from typing import Type

from yaml import SafeLoader

from type_yaml.base import TypeLike
from type_yaml.yaml_interpreter import RealYamlDumper
from type_yaml.yaml_interpreter import YamlDumper
from type_yaml.yaml_interpreter import YamlInterpreter


def load(
    type_: TypeLike,
    stream: TextIO,
    *,
    loader: Type = SafeLoader,
    true_strings: tuple[str, ...] = ("true", "yes", "on", "1"),
    false_strings: tuple[str, ...] = ("false", "no", "off", "0"),
    type_name_map: dict[str, Any] | None = None,
    globalns: dict[str, Any] | None = None,
    localns: dict[str, Any] | None = None,
) -> Any:
    interpreter = YamlInterpreter(
        type_,
        stream,
        loader=loader,
        true_strings=true_strings,
        false_strings=false_strings,
        type_name_map=type_name_map,
        globalns=globalns,
        localns=localns,
    )
    return interpreter.load()


def loads(
    type_: TypeLike,
    string: str,
    *,
    loader: Type = SafeLoader,
    true_strings: tuple[str, ...] = ("true", "yes", "on", "1"),
    false_strings: tuple[str, ...] = ("false", "no", "off", "0"),
    type_name_map: dict[str, Any] | None = None,
    globalns: dict[str, Any] | None = None,
    localns: dict[str, Any] | None = None,
) -> Any:
    _, p = mkstemp()
    try:
        with open(p, "r+") as f:
            f.write(string)
            f.seek(0)
            return load(
                type_,
                f,
                loader=loader,
                true_strings=true_strings,
                false_strings=false_strings,
                type_name_map=type_name_map,
                globalns=globalns,
                localns=localns,
            )
    finally:
        os.remove(p)


def dump(value: Any, stream: TextIO, *, dumper: Type = RealYamlDumper) -> None:
    dumper = YamlDumper(value, stream, dumper=dumper)
    dumper.dump()


def dumps(value: Any, *, dumper: Type = RealYamlDumper) -> str:
    _, p = mkstemp()
    try:
        with open(p, "r+") as f:
            dump(value, f, dumper=dumper)
            f.seek(0)
            return f.read()
    finally:
        os.remove(p)
