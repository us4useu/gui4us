"""Assembles the ES modules in ``ui/src`` into a single module for anywidget.

anywidget evaluates ``_esm`` as one standalone module, so relative imports cannot be resolved
at run time -- the widget code has to arrive pre-bundled. The canonical way to produce that
bundle is ``npm run build:widgets`` (Vite, see ui/vite.widgets.config.js), and the result is
looked up first. This module is the fallback that keeps the notebook usable in an environment
without Node, which is the normal situation on an acquisition workstation.

It is a deliberately small bundler and it works because the component sources obey two rules
(checked by ``tests/test_bundler.py``):

1. modules only ever import from each other with static, relative ``import`` statements placed
   at the top of the file;
2. top-level names are unique across all modules, so the concatenation cannot shadow anything.
"""

import pathlib
import re
from typing import Dict, List, Set

#: Any static import statement: `import ... from "x";` or a side-effect `import "x";`.
_IMPORT_RE = re.compile(
    r"""^[ \t]*import\s+(?:[^'"]*?\s+from\s+)?['"](?P<path>[^'"]+)['"][ \t]*;?[ \t]*$""",
    re.MULTILINE)
_EXPORT_DEFAULT_RE = re.compile(r"^\s*export\s+default\s+", re.MULTILINE)
_EXPORT_RE = re.compile(r"^\s*export\s+(?=(?:const|let|var|function|class|async)\b)",
                        re.MULTILINE)


class BundleError(RuntimeError):
    pass


def bundle(entry: pathlib.Path) -> str:
    """Returns a single ES module with ``entry`` and everything it imports.

    The entry's ``export default`` is preserved; all other exports become plain top-level
    declarations (the bundle has a single module scope).
    """
    entry = pathlib.Path(entry).resolve()
    sources: List[str] = []
    visited: Set[pathlib.Path] = set()
    _collect(entry, sources, visited, entry)
    return "\n".join(sources)


def _collect(path: pathlib.Path, out: List[str], visited: Set[pathlib.Path],
             entry: pathlib.Path) -> None:
    path = path.resolve()
    if path in visited:
        return
    if not path.is_file():
        raise BundleError(f"Imported module not found: {path}")
    visited.add(path)
    source = path.read_text(encoding="utf-8")

    # Depth first: a module's dependencies must precede it in the output.
    for match in _IMPORT_RE.finditer(source):
        specifier = match.group("path")
        if not specifier.startswith("."):
            raise BundleError(
                f"{path.name} imports '{specifier}'. The fallback bundler only supports "
                f"relative imports; build the widgets with `npm run build:widgets` instead.")
        _collect(path.parent/specifier, out, visited, entry)

    source = _IMPORT_RE.sub("", source)
    if path != entry:
        source = _EXPORT_DEFAULT_RE.sub("", source)
    source = _EXPORT_RE.sub("", source)
    out.append(f"/* --- {path.name} --- */\n{source.strip()}\n")


def top_level_names(source: str) -> Dict[str, int]:
    """Counts top-level ``const/let/var/function/class`` names in a bundle.

    Used by the tests to guarantee rule (2) above.
    """
    names: Dict[str, int] = {}
    pattern = re.compile(
        r"^(?:const|let|var|function|class)\s+([A-Za-z_$][\w$]*)", re.MULTILINE)
    for match in pattern.finditer(source):
        name = match.group(1)
        names[name] = names.get(name, 0) + 1
    return names
