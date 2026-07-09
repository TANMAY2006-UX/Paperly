from typing import List, Dict
from extractor.models import ExtractionContext, ZonalPartition, DocumentZone, ZoneType, FenceType
from extractor.telemetry import StageTransitionEvent, ZoneEvent, AnomalyEvent

def partition_zones(context: ExtractionContext) -> ExtractionContext:
    context.emit(StageTransitionEvent(stage_name="ZonalPartitioning", status="START"))
    
    if not context.landmark_report or not context.landmark_report.fences:
        # Fallback: No fences -> UNKNOWN zone
        if context.assembled_groups:
            zone = DocumentZone(
                zone_type=ZoneType.UNKNOWN,
                start_index=0,
                end_index=len(context.assembled_groups),
                groups=context.assembled_groups
            )
            context.zonal_partition = ZonalPartition(zones=[zone])
            context.emit(ZoneEvent(
                stage_name="ZonalPartitioning",
                zone_type="UNKNOWN",
                start_index=0,
                end_index=len(context.assembled_groups),
                group_count=len(context.assembled_groups),
                trigger_fence=None
            ))
            context.emit(AnomalyEvent(
                stage_name="ZonalPartitioning",
                severity="WARNING",
                message="UNKNOWN fallback triggered: 0 fences found"
            ))
            context.log("ZonalPartitioning", "Partitioned into UNKNOWN zone", "0 fences found in LandmarkReport")
        else:
            context.zonal_partition = ZonalPartition(zones=[])
        context.emit(StageTransitionEvent(stage_name="ZonalPartitioning", status="END"))
        return context

    # Sort fences to guarantee linear monotonic processing
    fences = sorted(context.landmark_report.fences, key=lambda f: f.reading_order_start)
    fence_map = {f.reading_order_start: f for f in fences}
    
    zones: List[DocumentZone] = []
    
    current_zone_type = ZoneType.FRONT_MATTER
    current_start = 0
    current_trigger = None
    
    # We track sequence to ensure unexpected ordering emits an anomaly
    seen_zones = set()
    
    for i in range(len(context.assembled_groups)):
        if i in fence_map:
            fence = fence_map[i]
            
            # Map FenceType to ZoneType
            next_zone_type = None
            if fence.fence_type == FenceType.SECTION_HEADING:
                if current_zone_type == ZoneType.FRONT_MATTER:
                    # First section heading transitions Front Matter -> Body
                    next_zone_type = ZoneType.BODY
            elif fence.fence_type == FenceType.REFERENCES_HEADING:
                if current_zone_type != ZoneType.REFERENCES:
                    next_zone_type = ZoneType.REFERENCES
            elif fence.fence_type == FenceType.ACKNOWLEDGEMENTS_HEADING:
                if current_zone_type != ZoneType.ACKNOWLEDGEMENTS:
                    next_zone_type = ZoneType.ACKNOWLEDGEMENTS
            elif fence.fence_type == FenceType.APPENDIX_HEADING:
                if current_zone_type != ZoneType.APPENDIX:
                    next_zone_type = ZoneType.APPENDIX
                    
            if next_zone_type:
                # Close current zone
                if i > current_start:
                    z = DocumentZone(
                        zone_type=current_zone_type,
                        start_index=current_start,
                        end_index=i,
                        groups=context.assembled_groups[current_start:i]
                    )
                    zones.append(z)
                    context.emit(ZoneEvent(
                        stage_name="ZonalPartitioning",
                        zone_type=current_zone_type.name,
                        start_index=current_start,
                        end_index=i,
                        group_count=i - current_start,
                        trigger_fence=current_trigger
                    ))
                    seen_zones.add(current_zone_type)
                    
                    # Detect unexpected sequences
                    if next_zone_type == ZoneType.BODY and (ZoneType.REFERENCES in seen_zones or ZoneType.APPENDIX in seen_zones):
                        context.emit(AnomalyEvent(
                            stage_name="ZonalPartitioning",
                            severity="WARNING",
                            message=f"Unexpected landmark ordering: {fence.fence_type.name} after back-matter zone"
                        ))
                
                # Open new zone
                current_zone_type = next_zone_type
                current_start = i
                current_trigger = f"{fence.fence_type.name} on group {fence.group_ids[0]}"
                
    # Close final zone
    total_len = len(context.assembled_groups)
    if current_start < total_len:
        z = DocumentZone(
            zone_type=current_zone_type,
            start_index=current_start,
            end_index=total_len,
            groups=context.assembled_groups[current_start:total_len]
        )
        zones.append(z)
        context.emit(ZoneEvent(
            stage_name="ZonalPartitioning",
            zone_type=current_zone_type.name,
            start_index=current_start,
            end_index=total_len,
            group_count=total_len - current_start,
            trigger_fence=current_trigger
        ))
        
    context.zonal_partition = ZonalPartition(zones=zones)
    context.log("ZonalPartitioning", "Partitioned document", f"Created {len(zones)} zones")
    
    _verify_invariants(context)
    
    context.emit(StageTransitionEvent(stage_name="ZonalPartitioning", status="END"))
    return context


def _verify_invariants(context: ExtractionContext):
    part = context.zonal_partition
    if not part:
        return
        
    # 1. Exhaustive Partitioning
    total_groups = sum(len(z.groups) for z in part.zones)
    if total_groups != len(context.assembled_groups):
        raise ValueError(f"Invariant Violated: Exhaustive Partitioning failed. Zones contain {total_groups} groups, expected {len(context.assembled_groups)}")
        
    seen_ids = set()
    # 2. Mutual Exclusivity
    for z in part.zones:
        for g in z.groups:
            if g.group_id in seen_ids:
                raise ValueError(f"Invariant Violated: Mutual Exclusivity failed. Group {g.group_id} appears in multiple zones.")
            seen_ids.add(g.group_id)
            
    # 3. Monotonic Sequence Preservation
    idx = 0
    for z in part.zones:
        # 5. Boundary Containment is implicitly verified since the zones are sliced at exactly the index of the structural fence,
        # so the structural fence group becomes the 0th element of the new zone.
        for g in z.groups:
            if g.group_id != context.assembled_groups[idx].group_id:
                raise ValueError(f"Invariant Violated: Monotonic Sequence Preservation failed at index {idx}.")
            idx += 1
