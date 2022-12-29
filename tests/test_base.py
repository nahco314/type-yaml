import io
import sys
from typing import List

import pytest

from type_yaml.base import InterpreterBase
from type_yaml.base import TypeLike


@pytest.mark.parametrize(
    ("typelike", "expected"),
    [
        (int, "int"),
        ("int", "int"),
        (List[int], "list[int]"),
        (List["int"], "list[int]"),
        (List[List[int]], "list[list[int]]"),
        (List, "list[Any]"),
        (dict, "dict[Any, Any]"),
        (set, "set[Any]"),
        (tuple, "tuple[Any, ...]"),
        ("Any", "Any"),
    ],
)
def test_interpret_typelike(typelike: TypeLike, expected: str) -> None:
    interpreter = InterpreterBase(typelike, io.StringIO())
    assert interpreter.type_to_str(interpreter.eval_typelike(typelike)) == expected


if sys.version_info >= (3, 10):

    @pytest.mark.parametrize(
        ("typelike", "expected"),
        [
            (list[int], "list[int]"),
            (list["int"], "list[int]"),
            (list[list[int]], "list[list[int]]"),
            ("list[int]", "list[int]"),
        ],
    )
    def test_interpret_typelike_310(typelike: TypeLike, expected: str) -> None:
        interpreter = InterpreterBase(typelike, io.StringIO())
        assert interpreter.type_to_str(interpreter.eval_typelike(typelike)) == expected
