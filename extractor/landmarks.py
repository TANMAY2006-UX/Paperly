from typing import List, Tuple
from extractor.telemetry import StageTransitionEvent
from extractor.models import (
    ExtractionContext,
    TypographicGroup,
    LandmarkKind,
    LandmarkToken,
    LandmarkReport
)


def detect_landmarks(context: ExtractionContext) -> ExtractionContext:
    context.emit(StageTransitionEvent(stage_name="Landmarks", status="START"))
    
    tokens: List[LandmarkToken] = []
    groups = context.assembled_groups
    
    if not groups:
        context.landmark_report = LandmarkReport(tokens=tokens)
        context.emit(StageTransitionEvent(stage_name="Landmarks", status="COMPLETE"))
        return context
        
    anchor_idx = 0
    max_emphasis = groups[0].typography_class
    
    for i in range(1, len(groups)):
        emp = groups[i].typography_class
        if emp > max_emphasis:
            max_emphasis = emp
            anchor_idx = i
            
    tokens.append(LandmarkToken(kind=LandmarkKind.ANCHOR, group_id=groups[anchor_idx].group_id))
    
    for i in range(len(groups)):
        curr_emp = groups[i].typography_class
        
        prev_emp = groups[i-1].typography_class if i > 0 else -1
        next_emp = groups[i+1].typography_class if i < len(groups) - 1 else -1
        
        if curr_emp > prev_emp and curr_emp > next_emp:
            tokens.append(LandmarkToken(kind=LandmarkKind.OUTLIER, group_id=groups[i].group_id))
            
    context.landmark_report = LandmarkReport(tokens=tokens)
    context.emit(StageTransitionEvent(stage_name="Landmarks", status="COMPLETE"))
    
    return context
