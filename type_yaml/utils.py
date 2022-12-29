def get_part_of_string(
    string: str, start_line: int, start_col: int, end_line: int, end_col: int
) -> str:
    if start_line == end_line:
        return string.splitlines()[start_line][start_col:end_col]
    else:
        lines = string.splitlines(keepends=True)
        res = [
            lines[start_line][start_col:],
            *lines[start_line + 1 : end_line],
            lines[end_line][:end_col],
        ]
        return "".join(res)
