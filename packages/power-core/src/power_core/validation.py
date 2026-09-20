"""Dependency-graph validation and reporting.

The DI container builds an object graph lazily, so a missing registration is
normally only discovered when ``resolve`` is first called. Validation makes that
graph *explicit and checkable up front*: the framework walks every injectable
constructor parameter from a set of roots and reports, as a human-readable tree,
which dependencies are satisfiable and which are missing.

A validation report looks like::

    Application dependency validation failed:

    OrderService
    └── OrderRepository
        └── Database
            └── DatabaseConfiguration   ✓

    RiskService
    └── MarketDataProvider
        └── MarketDataConfiguration     ✗ missing

This module owns the *tree* data structure and its rendering; the concrete
:class:`~power_core.container.Container` builds the tree from its registry.
"""

from __future__ import annotations

from dataclasses import dataclass, field

#: Marker shown on a resolvable leaf dependency.
SATISFIED_MARK = "✓"
#: Marker shown on a dependency with no registration.
MISSING_MARK = "✗ missing"


@dataclass
class DependencyNode:
    """A single type in a dependency tree.

    ``missing`` is ``True`` when the type has no registration (a dead end with
    no children). A satisfied leaf has no children and ``missing=False``. An
    internal node carries its resolved dependencies in ``children``.
    """

    name: str
    missing: bool = False
    children: list[DependencyNode] = field(default_factory=list)

    def has_missing(self) -> bool:
        """Return ``True`` if this node or any descendant is missing."""
        if self.missing:
            return True
        return any(child.has_missing() for child in self.children)


def _status_suffix(node: DependencyNode) -> str:
    """Return the ``✓``/``✗ missing`` annotation for a node."""
    if node.missing:
        return f"   {MISSING_MARK}"
    if not node.children:
        return f"   {SATISFIED_MARK}"
    return ""


def render_tree(
    node: DependencyNode,
    prefix: str = "",
    is_last: bool = True,
    is_root: bool = True,
) -> list[str]:
    """Render a dependency node and its descendants as an indented tree."""
    lines: list[str] = []
    if is_root:
        lines.append(node.name)
    else:
        connector = "└── " if is_last else "├── "
        lines.append(f"{prefix}{connector}{node.name}{_status_suffix(node)}")

    child_prefix = prefix
    if not is_root:
        child_prefix += "    " if is_last else "│   "
    for index, child in enumerate(node.children):
        lines.extend(
            render_tree(
                child,
                prefix=child_prefix,
                is_last=index == len(node.children) - 1,
                is_root=False,
            )
        )
    return lines


def render_report(nodes: list[DependencyNode]) -> str:
    """Render a full validation report for one or more root nodes."""
    body: list[str] = []
    for node in nodes:
        body.extend(render_tree(node))
        body.append("")
    return "Application dependency validation failed:\n\n" + "\n".join(body).rstrip() + "\n"


__all__ = [
    "MISSING_MARK",
    "SATISFIED_MARK",
    "DependencyNode",
    "render_report",
    "render_tree",
]
