"""L1 — the core. Context, Service, effect / disposer, the event bus.

Follows Cordis by name (ADR-0001). Nothing here knows what is being analysed (L2): the words in
this package are context, service, effect, disposer, event, fork. A domain term appearing here is
a defect `sch doctor --architecture` reports.
"""
from .context import Context, Service, Disposer, InjectError, DisposeError  # noqa: F401
from .events import EventBus  # noqa: F401
