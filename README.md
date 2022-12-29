# type-yaml

Describes a yaml schema using Python types.

Simple Python types such as `list[str]` or `dict[int, list[str]]` that allow yaml to verify that the type fits and parse values based on it.

## Requirements
- Python 3.8+
- PyYAML

## Install
```commandline
pip install type-yaml
```

## Features:
- `int`
- `float`
- `str`
- `bool`
- `list` / `typing.List`
- `dict` / `typing.Dict`
- `set` / `typing.Set`
- `tuple` / `typing.Tuple`
- `dataclass`
  - default values and default-factory
  - special notation in yaml with metadata
- `operator |`/ `typing.Union`
- `typing.Any`
- lazy evaluation by string representation of type

## Examples

```python
from dataclasses import dataclass

from type_yaml import load


@dataclass
class Point:
    x: int
    y: int


print(load(list[Point], open("points.yaml")))
# >>> [Point(x=1, y=2), Point(x=3, y=4)]
```

```yaml
# points.yaml
-
  x: 1
  y: 2
-
  x: 3
  y: 4
```

## Usage

Functions such as `load`, `loads`, `dump`, and `dumps` can be imported from type_yaml. The details of each are as follows.

- `load(type, stream, **kwargs)`
  - Load a yaml file and parse it into a Python object.
  - `type` is a type that can be parsed by type_yaml.
  - `stream` is a text stream. e.g. `open("file.yaml")`
  - options
    - `loader`: yaml loader of PyYAML. default: `yaml.SafeLoader`
    - `true_strings`: list of strings that are parsed as `True`. default: `("true", "yes", "on", "1")`
    - `false_strings`: list of strings that are parsed as `False`. default: `("false", "no", "off", "0")`
    - `type_name_map`, `globalns`, `localns`: a dictionary or namespace of variable names is given to allow interpretation of the string representation of the type
- `loads(type, string, **kwargs)`
  - Load a yaml string and parse it into a Python object.
  - `type` is a type that can be parsed by type_yaml.
  - `string` is a yaml string.
  - options is same as `load`
- `dump(value, stream, **kwargs)`
  - Dump a Python object to a yaml file.
  - `value` is a Python object that can be parsed by type_yaml.
  - `stream` is a text stream. e.g. `open("file.yaml")`
  - options
    - `dumper`: yaml dumper of PyYAML. default: `type_yaml.yaml_interpreter.RealYamlDumper
- `dumps(value, **kwargs)`
  - Dump a Python object to a yaml string.
  - `value` is a Python object that can be parsed by type_yaml.
  - options is same as `dump`

## Other

The license is the MIT License.

If you have any bugs, mistakes, feature suggestions, etc., issues and pull requests are welcome.
