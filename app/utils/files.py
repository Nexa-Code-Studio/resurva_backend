import os
import re


def get_safe_filename(filename: str) -> str:
    """
    Sanitize filename by removing suspicious characters
    and returning a lowercase ASCII safe file name.
    """
    base, ext = os.path.splitext(filename)
    # Remove all non-word characters (except periods/dashes)
    safe_base = re.sub(r"[^\w\.-]", "_", base)
    # Remove double underscores
    safe_base = re.sub(r"__+", "_", safe_base)
    # Ensure it's not empty
    if not safe_base:
        safe_base = "file"
    return f"{safe_base.lower()}{ext.lower()}"
