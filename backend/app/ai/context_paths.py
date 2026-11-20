"""Mask infrastructure paths only when constructing outbound AI diagnostics."""
from pathlib import Path
import re
from ..paths import toolchains_dir


def mask_diagnostics(value, data_dir):
    prefixes = [(Path.home(), '<user-home>'), (Path(data_dir), '<data>')]
    try:
        prefixes.append((toolchains_dir(), '<toolchain>'))
    except ValueError:
        pass
    replacements = {}
    for path, label in prefixes:
        text = str(path)
        for variant in (text, text.replace('\\','/'), text.replace('/','\\')):
            replacements[variant] = label
    def mask(item):
        if isinstance(item, dict): return {key:mask(child) for key,child in item.items()}
        if isinstance(item, list): return [mask(child) for child in item]
        if not isinstance(item, str): return item
        for prefix in sorted(replacements, key=len, reverse=True):
            item = re.sub(re.escape(prefix), lambda _:replacements[prefix], item, flags=re.IGNORECASE)
        # Diagnostics may reference another user's SDK or an older toolchain.
        item = re.sub(r'[A-Za-z]:[/\\]Users[/\\][^/\\\r\n]+(?=[/\\])', '<user-home>', item)
        return re.sub(r'/Users/[^/\r\n]+(?=/)', '<user-home>', item)
    return mask(value)
