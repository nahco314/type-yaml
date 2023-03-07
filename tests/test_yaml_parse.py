from __future__ import annotations

import re
from dataclasses import dataclass
from dataclasses import field
from textwrap import dedent
from typing import Any
from typing import List

import pytest
from type_parse.base import TypeLike

import type_yaml.errors as errors
from type_yaml.yaml_parse import dumps
from type_yaml.yaml_parse import loads


@pytest.mark.parametrize(
    ("yaml_str", "type_", "value"),
    [
        ("[1, 2, 3]", "list[int]", [1, 2, 3]),
        ("[1, 2, 3]", "list[str]", ["1", "2", "3"]),
        ("[1, 2, 3]", "list[float]", [1.0, 2.0, 3.0]),
        ("[yes, no, 1]", "list[bool]", [True, False, True]),
        ("[[1, 2, 3], [], [5]]", "list[list[int]]", [[1, 2, 3], [], [5]]),
        (
            """\
            - 1
            - 2
            - 3
            """,
            "list[int]",
            [1, 2, 3],
        ),
        ("{1: 2, 3: 4}", "dict[int, int]", {1: 2, 3: 4}),
        (
            """\
            foo: 1
            bar: 2
            """,
            "dict[str, int]",
            {"foo": 1, "bar": 2},
        ),
        ("[1, 2, 3]", "set[int]", {1, 2, 3}),
        ("[1, 2, 3]", "tuple[int, int, int]", (1, 2, 3)),
        ("[1, 2, 3, 4]", "tuple[int, ...]", (1, 2, 3, 4)),
        ("[1, 2, 3]", "Any", [1, 2, 3]),
        ("[1, no, 1.0]", "Any", [1, False, 1.0]),
        ("{1: a, b: 2}", "Any", {1: "a", "b": 2}),
        ("[1, 2, 3]", "list", [1, 2, 3]),
        ("{1: a}", "dict", {1: "a"}),
        ("[1, 2, 3]", "set", {1, 2, 3}),
        ("[1, 2, 3]", "tuple", (1, 2, 3)),
        ("[[1, 2, 3], [], [5]]", "list[list[\nint\n]]", [[1, 2, 3], [], [5]]),
        ("[1, 2, 3]", "Union[int, list[int]]", [1, 2, 3]),
    ],
)
def test_yaml_load(yaml_str: str, type_: TypeLike, value: Any) -> None:
    yaml = dedent(yaml_str)

    assert loads(type_, yaml) == value


@dataclass
class Person1:
    name: str
    age: int
    friends: List[Person1]


@dataclass
class Person2:
    name: str
    age: int
    friends: List["Person2"]


@dataclass
class Point:
    x: int
    y: int


class Tag:
    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, other: object) -> bool:  # pragma: no cover
        if not isinstance(other, Tag):
            return NotImplemented
        return self.name == other.name


@dataclass
class String:
    value: str
    is_empty: bool = False
    tags: list[Tag] = field(
        default_factory=list,
        metadata={
            "yaml_type": "list[str]",
            "yaml_convert": lambda x: [Tag(t) for t in x],
        },
    )


@pytest.mark.parametrize(
    ("yaml_str", "type_", "value"),
    [
        (
            """\
            name: John
            age: 30
            friends:
                - name: Mary
                  age: 28
                  friends: []
            """,
            Person1,
            Person1("John", 30, [Person1("Mary", 28, [])]),
        ),
        (
            """\
            name: John
            age: 30
            friends:
                - name: Mary
                  age: 28
                  friends: []
            """,
            Person2,
            Person2("John", 30, [Person2("Mary", 28, [])]),
        ),
        (
            """\
            value: foo
            """,
            String,
            String("foo", False, []),
        ),
        (
            """\
            value: foo
            is_empty: true
            """,
            String,
            String("foo", True, []),
        ),
        (
            """\
            value: foo
            tags:
                - tag1
                - tag2
            """,
            String,
            String("foo", False, [Tag("tag1"), Tag("tag2")]),
        ),
    ],
)
def test_yaml_load_dataclass(yaml_str: str, type_: TypeLike, value: Any) -> None:
    yaml = dedent(yaml_str)

    assert loads(type_, yaml, globalns=globals(), localns=locals()) == value


def test_type_name_map() -> None:
    yaml = dedent(
        """\
        name: John
        age: 30
        friends:
            - name: Mary
              age: 28
              friends: []
        """
    )

    p = Person1("John", 30, [Person2("Mary", 28, [])])  # type: ignore
    assert (
        loads(
            Person1,
            yaml,
            globalns=globals(),
            localns=locals(),
            type_name_map={"Person1": Person2},
        )
        == p
    )


def test_multi_document() -> None:
    yaml = dedent(
        """\
        ---
        x: 1
        y: 2
        ---
        x: 3
        y: 4
        """
    )

    p = [Point(1, 2), Point(3, 4)]
    assert (
        loads(
            "list[Point]",
            yaml,
            multi_document=True,
            globalns=globals(),
            localns=locals(),
        )
        == p
    )


@pytest.mark.parametrize(
    ("yaml_str", "type_", "error_msg"),
    [
        ("aaa", int, "expected int, 'aaa' found\n" '  in ".*", line 1, column 1'),
        (
            "aaa",
            "int | list",
            "failed to parse yaml\\. expected one of \\(int, list\\[Any\\]\\)\n"
            "errors for each type:\n"
            "type: int\n"
            "    expected int, 'aaa' found\n"
            '      in ".*", line 1, column 1\n'
            "type: list\\[Any\\]\n"
            "    expected list\\[Any\\], scalar found\n"
            '      in ".*", line 1, column 1\n'
            '  in ".*", line 1, column 1',
        ),
    ],
)
def test_yaml_load_error(yaml_str: str, type_: TypeLike, error_msg: str) -> None:
    with pytest.raises(errors.YamlTypeError) as e:
        loads(type_, yaml_str)

    assert re.match(error_msg, str(e.value))


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (1, "1\n...\n"),
        (
            [1, 2, 3],
            """\
            - 1
            - 2
            - 3
            """,
        ),
        (
            String("foo"),
            """\
            value: foo
            is_empty: false
            tags: []
            """,
        ),
    ],
)
def test_yaml_dump(value: Any, expected: str) -> None:
    assert dumps(value) == dedent(expected)
