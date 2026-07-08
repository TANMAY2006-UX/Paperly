import json
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional

from extractor.telemetry import (
    TelemetryEvent, EventType, StageTransitionEvent, DecisionEvent, AnomalyEvent
)

@dataclass(slots=True)
class DecisionRecord:
    evaluator: str
    status: str
    score: float
    reason: str

@dataclass(slots=True)
class InspectionRecord:
    group_id: str
    decisions: List[DecisionRecord] = field(default_factory=list)
    
    @property
    def was_accepted(self) -> bool:
        for d in self.decisions:
            if d.status == "ACCEPTED":
                return True
        return False

@dataclass(slots=True)
class StageTrace:
    stage_name: str
    group_records: Dict[str, InspectionRecord] = field(default_factory=dict)
    
    def get_record(self, group_id: str) -> InspectionRecord:
        if group_id not in self.group_records:
            self.group_records[group_id] = InspectionRecord(group_id=group_id)
        return self.group_records[group_id]

@dataclass(slots=True)
class PipelineTrace:
    stages: Dict[str, StageTrace] = field(default_factory=dict)
    
    def get_stage(self, stage_name: str) -> StageTrace:
        if stage_name not in self.stages:
            self.stages[stage_name] = StageTrace(stage_name=stage_name)
        return self.stages[stage_name]

class Inspector:
    """
    Subscribes to the EventBus and builds a hierarchical diagnostic tree.
    Completely read-only. Does not modify pipeline state.
    """
    def __init__(self):
        self.trace = PipelineTrace()
        
    def receive(self, event: TelemetryEvent) -> None:
        if event.event_type == EventType.DECISION and isinstance(event, DecisionEvent):
            stage = self.trace.get_stage(event.stage_name)
            record = stage.get_record(event.group_id)
            record.decisions.append(DecisionRecord(
                evaluator=event.evaluator,
                status=event.status,
                score=event.score,
                reason=event.reason
            ))
            
    def export_json(self) -> str:
        return json.dumps(asdict(self.trace), indent=2)
        
    def print_report(self) -> None:
        print("=== Inspector Report ===")
        for stage_name, stage in self.trace.stages.items():
            accepted = 0
            rejected = 0
            for group_id, record in stage.group_records.items():
                if record.was_accepted:
                    accepted += 1
                else:
                    rejected += 1
            print(f"Stage: {stage_name}")
            print(f"  Accepted groups: {accepted}")
            print(f"  Rejected groups: {rejected}")
            
    def print_group_trace(self, group_id: str) -> None:
        print(f"=== Trace for Group: {group_id} ===")
        found = False
        for stage_name, stage in self.trace.stages.items():
            if group_id in stage.group_records:
                found = True
                print(f"Stage: {stage_name}")
                record = stage.group_records[group_id]
                for d in record.decisions:
                    print(f"  - Evaluator: {d.evaluator}")
                    print(f"    Status: {d.status} | Score: {d.score:.2f} | Reason: {d.reason}")
        if not found:
            print("  (No trace found)")
