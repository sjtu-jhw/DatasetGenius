import regex
from document import Title

def _find_closed_brackets(in_tex: str, start: int, end: int):
    """
    Cause using regex to match multiline brackets is so difficult, we find another way to locate what we want

    Args:
        in_tex(str): input latex code
        start(int): match location beginning
        end(int): match location ending
    
    Returns:
        a string we want to match 
    """
    bracket_dict = {"(": ")", "[": "]", "{": "}"}
    bracket = in_tex[end-1]
    bracket_lst = [bracket]
    while bracket_lst.count(bracket) != bracket_lst.count(bracket_dict[bracket]):
        char = in_tex[end]
        if char == bracket or char == bracket_dict[bracket]:
            bracket_lst.append(char)
        end += 1
    return in_tex[start:end]

def parse_title(in_tex: str):
    pattern = r"\\title{(.*)}"
    p = regex.compile(pattern)
    title = p.findall(in_tex)[0]
    return Title(content=title)

def parse_affiliations(in_tex: str):
    pattern = r"\\author{"
    p = regex.compile(pattern)
    start = p.search(in_tex).start()
    end = p.search(in_tex).end()
    in_tex = _find_closed_brackets(in_tex, start, end)

    def _parse_author(in_tex: str):
        # first clean unwanted
        patterns = [r"\$\\qquad\$", r"\\begin\{(.*?)\}", r"\\end\{(.*?)\}"]