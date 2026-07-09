from enum import Enum, auto
from dataclasses import dataclass
from typing import List, Callable, Any

class EventType(Enum):
    STAGE_TRANSITION = auto()
    DECISION = auto()
    ANOMALY = auto()
    ZONE_CREATED = auto()

from dataclasses import dataclass, field
from typing import Optional

@dataclass(slots=True)
class TelemetryEvent:
    stage_name: str
    event_type: EventType = field(init=False)

@dataclass(slots=True)
class StageTransitionEvent(TelemetryEvent):
    status: str  # "START" or "END"
    def __post_init__(self):
        self.event_type = EventType.STAGE_TRANSITION

@dataclass(slots=True)
class DecisionEvent(TelemetryEvent):
    group_id: str
    evaluator: str
    status: str       # "ACCEPTED", "REJECTED", "VETOED"
    score: float
    reason: str
    def __post_init__(self):
        self.event_type = EventType.DECISION

@dataclass(slots=True)
class AnomalyEvent(TelemetryEvent):
    severity: str     # "WARNING", "ERROR"
    message: str
    def __post_init__(self):
        self.event_type = EventType.ANOMALY

@dataclass(slots=True)
class ZoneEvent(TelemetryEvent):
    zone_type: str
    start_index: int
    end_index: int
    group_count: int
    trigger_fence: Optional[str]
    
    def __post_init__(self):
        self.event_type = EventType.ZONE_CREATED

class EventBus:
    """
    A lightweight, synchronous event bus that dispatches telemetry events to subscribers.
    Does NOT store events.
    """
    def __init__(self):
        self._subscribers: List[Callable[[TelemetryEvent], None]] = []

    def subscribe(self, subscriber_fn: Callable[[TelemetryEvent], None]) -> None:
        if subscriber_fn not in self._subscribers:
            self._subscribers.append(subscriber_fn)

    def dispatch(self, event: TelemetryEvent) -> None:
        for subscriber in self._subscribers:
            subscriber(event)
