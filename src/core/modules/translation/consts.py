from typing import Any, Dict, List, Optional, Union  # Ensure List is imported

default_rules = {
    "conversions": {
        "str_to_list_str": {
            "from_type": "str",
            "to_type": "List[str]",
            "method": "split_string",
        },
        "int_to_str": {"from_type": "int", "to_type": "str", "method": "simple_cast"},
        "float_to_str": {
            "from_type": "float",
            "to_type": "str",
            "method": "simple_cast",
        },
        "str_to_int": {"from_type": "str", "to_type": "int", "method": "simple_cast"},
        "str_to_float": {
            "from_type": "str",
            "to_type": "float",
            "method": "simple_cast",
        },
        "str_to_bool": {
            "from_type": "str",
            "to_type": "bool",
            "method": "string_to_bool",
        },
    }
}


# Dictionary to map type names to actual types
type_mapping = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
    "List[str]": List[str],
    "List[int]": List[int],
    "List[float]": List[float],
    "List[bool]": List[bool],
    "List[dict]": List[dict],
    "Dict[str, Any]": Dict[str, Any],
}
