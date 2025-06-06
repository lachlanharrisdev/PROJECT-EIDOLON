import re
from .utils import check_ext  # Here to avoid false errors in IDE

re_content = re.compile(r"(post|blog)s?|docs|support/|/(\d{4}|pages?)/\d+/")
content_patterns = []


def has_ext(path, params, meta) -> bool:
    """
    returns True if url has extension e.g. example.com/about-us/team.php
    """
    has_ext, _ = check_ext(path, ())
    return has_ext


def no_ext(path, params, meta) -> bool:
    """
    returns True if url has no extension e.g. example.com/about-us/team
    """
    has_ext, _ = check_ext(path, ())
    return not has_ext


def has_params(path, params, meta) -> bool:
    """
    returns True if url has parameters
    """
    return len(params) != 0


def no_params(path, params, meta) -> bool:
    """
    returns True if url has no parameters
    """
    return len(params) == 0


def whitelisted(path, params, meta) -> bool:
    """
    returns True if url has no extension or has a whitelisted extension
    """
    has_ext, is_ext = check_ext(path, meta["ext_list"])
    return is_ext or (not meta["strict"] and not has_ext)


def blacklisted(path, params, meta) -> bool:
    """
    returns True if url has no extension or doesn't have a blacklisted extension
    """
    has_ext, is_ext = check_ext(path, meta["ext_list"])
    return not is_ext or (not meta["strict"] and not has_ext)


def remove_content(path, params, meta) -> bool:
    """
    checks if a path is likely to contain
    human written content e.g. a blog

    returns False if it is
    """
    for part in path.split("/"):
        if part.count("-") > 3:
            return False
    if path.startswith(tuple(content_patterns)):
        return False
    else:
        match = re.search(re_content, path)
        if match:
            content_patterns.append(path[: match.end()])
    return True


def has_vuln_param(path, params, meta) -> bool:
    """
    checks if a url has a vulnerable parameter
    """
    for param in params:
        if param in meta["vuln_params"]:
            return True
