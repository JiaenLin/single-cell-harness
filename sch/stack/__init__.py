"""The stack declaration: `stack.yml`, composed by overlay (site → project → run)."""
from .compose import compose, load_layers, StackError  # noqa: F401
