import os
import fitz
from extractor.models import ExtractionContext, DocumentLayoutKind, BlockType

def draw_debug_overlays(context: ExtractionContext, output_dir: str = "debug_output", visualize_groups: bool = False, visualize_landmarks: bool = False, visualize_zones: bool = False, visualize_semantics: bool = False) -> ExtractionContext:
    """
    Stage 5/Debug: Debug Rendering
    Generates a debug PDF with visual overlays to validate geometric algorithms.
    """
    os.makedirs(output_dir, exist_ok=True)
    if visualize_semantics:
        out_name = f"{context.slug}_semantics_debug.pdf"
    elif visualize_zones:
        out_name = f"{context.slug}_zones_debug.pdf"
    elif visualize_landmarks:
        out_name = f"{context.slug}_landmarks_debug.pdf"
    elif visualize_groups:
        out_name = f"{context.slug}_groups_debug.pdf"
    else:
        out_name = f"{context.slug}_debug.pdf"
    out_path = os.path.join(output_dir, out_name)
    
    doc = fitz.open(context.pdf_path)
    
    # Pre-calculate counts for summary
    total_raw_blocks = sum(len(p.blocks) for p in context.pages)
    total_groups = len(context.assembled_groups) if hasattr(context, 'assembled_groups') and context.assembled_groups else 0
    furniture_removed = sum(len(p.layout.page_headers) + len(p.layout.page_footers) for p in context.pages if p.layout)
    landmarks_detected = len(context.landmark_report.fences) + len(context.landmark_report.anchors) if hasattr(context, 'landmark_report') and context.landmark_report else 0
    zones_detected = len(context.zonal_partition.zones) if hasattr(context, 'zonal_partition') and context.zonal_partition else 0
    semantic_nodes = len(context.semantic_blocks) if hasattr(context, 'semantic_blocks') and context.semantic_blocks else 0
    
    for p in context.pages:
        page = doc[p.page_num]
        layout = p.layout
        
        # Determine block/group order
        ordered_block_ids = []
        if hasattr(context, 'ordered_blocks') and context.ordered_blocks:
            ordered_block_ids = [b.textblock_id for b in context.ordered_blocks]
            
        group_to_order = {}
        if hasattr(context, 'assembled_groups') and context.assembled_groups:
            for idx, g in enumerate(context.assembled_groups):
                group_to_order[g.group_id] = idx
        
        # 1. Draw Text Blocks or Typographic Groups
        if visualize_semantics and hasattr(context, 'semantic_blocks') and context.semantic_blocks:
            semantic_colors = {
                "TITLE": (0.2, 0.6, 1.0),
                "AUTHORS": (0.8, 0.4, 1.0),
                "AFFILIATIONS": (0.6, 0.2, 0.8),
                "ABSTRACT": (0.9, 0.6, 0.2),
                "KEYWORDS": (0.7, 0.7, 0.2),
                "SECTION_HEADER": (1.0, 0.2, 0.2),
                "PARAGRAPH": (0.8, 0.8, 0.8),
                "FIGURE_CAPTION": (0.2, 0.8, 0.4),
                "TABLE_CAPTION": (0.2, 0.8, 0.6),
                "REFERENCES": (1.0, 0.5, 0.5),
                "APPENDIX": (0.7, 0.4, 0.7),
                "ACKNOWLEDGEMENTS": (1.0, 0.8, 0.4),
                "FRONT_MATTER": (0.9, 0.9, 0.9),
                "NOISE": (0.5, 0.5, 0.5)
            }
            group_to_sem = {sb.source_group.group_id: sb for sb in context.semantic_blocks}
            
            page_groups = [g for g in context.assembled_groups if g.source_blocks and g.source_blocks[0].page_num == p.page_num]
            for g in page_groups:
                x0 = g.x0 * p.width
                y0 = g.y0 * p.height
                x1 = g.x1 * p.width
                y1 = g.y1 * p.height
                rect = fitz.Rect(x0, y0, x1, y1)
                
                order_idx = group_to_order.get(g.group_id, "?")
                
                if g.group_id in group_to_sem:
                    sb = group_to_sem[g.group_id]
                    color = semantic_colors.get(sb.semantic_type.name, (0.8, 0.8, 0.8))
                    page.draw_rect(rect, color=color, fill=color, fill_opacity=0.3, width=2.0)
                    label = f"TG#{g.group_id} | O:{order_idx} | {sb.semantic_type.name}"
                    page.insert_text(fitz.Point(x0, max(y0 - 2, 0)), label, fontsize=6, color=(0, 0, 0))
                else:
                    page.draw_rect(rect, color=(1, 0, 0), width=1.0)
                    label = f"TG#{g.group_id} | O:{order_idx} | UNCLASSIFIED"
                    page.insert_text(fitz.Point(x0, max(y0 - 2, 0)), label, fontsize=6, color=(1, 0, 0))
                    
        elif visualize_zones and hasattr(context, 'zonal_partition') and context.zonal_partition:
            group_to_zone = {}
            zone_colors = {
                "FRONT_MATTER": (0.8, 0.9, 1.0),
                "BODY": (0.5, 0.8, 0.5),
                "REFERENCES": (1.0, 0.7, 0.7),
                "APPENDIX": (0.8, 0.6, 0.8),
                "ACKNOWLEDGEMENTS": (1.0, 0.9, 0.5),
                "UNKNOWN": (0.7, 0.7, 0.7)
            }
            for z in context.zonal_partition.zones:
                color = zone_colors.get(z.zone_type.name, (0.8, 0.8, 0.8))
                for g in z.groups:
                    group_to_zone[g.group_id] = (z.zone_type.name, color)
            
            page_groups = [g for g in context.assembled_groups if g.source_blocks and g.source_blocks[0].page_num == p.page_num]
            for g in page_groups:
                x0 = g.x0 * p.width
                y0 = g.y0 * p.height
                x1 = g.x1 * p.width
                y1 = g.y1 * p.height
                rect = fitz.Rect(x0, y0, x1, y1)
                order_idx = group_to_order.get(g.group_id, "?")
                
                if g.group_id in group_to_zone:
                    z_name, z_color = group_to_zone[g.group_id]
                    page.draw_rect(rect, color=z_color, fill=z_color, fill_opacity=0.3, width=2.0)
                    label = f"TG#{g.group_id} | O:{order_idx} | {z_name}"
                    page.insert_text(fitz.Point(x0, max(y0 - 2, 0)), label, fontsize=6, color=(0, 0, 0))
                else:
                    page.draw_rect(rect, color=(1, 0.5, 0), width=1.0)
                    label = f"TG#{g.group_id} | O:{order_idx} | UNZONED"
                    page.insert_text(fitz.Point(x0, max(y0 - 2, 0)), label, fontsize=6, color=(1, 0.5, 0))
                    
        elif visualize_groups and hasattr(context, 'assembled_groups') and context.assembled_groups:
            page_groups = [g for g in context.assembled_groups if g.source_blocks and g.source_blocks[0].page_num == p.page_num]
            for g in page_groups:
                x0 = g.x0 * p.width
                y0 = g.y0 * p.height
                x1 = g.x1 * p.width
                y1 = g.y1 * p.height
                rect = fitz.Rect(x0, y0, x1, y1)
                order_idx = group_to_order.get(g.group_id, "?")
                
                # Draw group box in orange
                page.draw_rect(rect, color=(1, 0.5, 0), width=2.0)
                
                # If visualizing landmarks, draw landmarks on top
                if visualize_landmarks and hasattr(context, 'landmark_report') and context.landmark_report:
                    matched_fence = next((f for f in context.landmark_report.fences if g.group_id in f.group_ids), None)
                    matched_anchor = next((a for a in context.landmark_report.anchors if g.group_id in a.group_ids), None)
                    
                    if matched_fence:
                        page.draw_rect(rect, color=(1, 0, 0), fill=(1, 0, 0), fill_opacity=0.2, width=3.0)
                        lbl = f"TG#{g.group_id} | O:{order_idx} | {matched_fence.fence_type.name}"
                        page.insert_text(fitz.Point(x0, max(y0 - 2, 0)), lbl, fontsize=8, color=(1, 0, 0))
                    elif matched_anchor:
                        page.draw_rect(rect, color=(0, 0.5, 1), fill=(0, 0.5, 1), fill_opacity=0.2, width=3.0)
                        lbl = f"TG#{g.group_id} | O:{order_idx} | {matched_anchor.anchor_type.name}"
                        page.insert_text(fitz.Point(x0, max(y0 - 2, 0)), lbl, fontsize=8, color=(0, 0.5, 1))
                    else:
                        conf_str = f"{g.evidence_vector.total_confidence:.2f}"
                        lbl = f"TG#{g.group_id} | O:{order_idx} | Conf:{conf_str}"
                        page.insert_text(fitz.Point(x0, max(y0 - 2, 0)), lbl, fontsize=6, color=(1, 0.5, 0))
                else:
                    conf_str = f"{g.evidence_vector.total_confidence:.2f}"
                    lbl = f"TG#{g.group_id} | O:{order_idx} | Conf:{conf_str}"
                    page.insert_text(fitz.Point(x0, max(y0 - 2, 0)), lbl, fontsize=6, color=(1, 0.5, 0))
        else:
            for b in p.blocks:
                x0 = b.x0 * p.width
                y0 = b.y0 * p.height
                x1 = b.x1 * p.width
                y1 = b.y1 * p.height
                rect = fitz.Rect(x0, y0, x1, y1)
                
                is_noise = b.block_type == BlockType.NOISE
                is_spanning = b.spans_columns
                is_header = layout and b.textblock_id in layout.page_headers
                is_footer = layout and b.textblock_id in layout.page_footers
                
                color = (0.5, 0.5, 0.5)  
                
                if not is_noise:
                    if is_spanning:
                        color = (0.5, 0, 0.5)  # Purple
                    else:
                        split_x = context.document_layout.primary_split_x if (context.document_layout and context.document_layout.primary_split_x) else (layout.column_split_x if layout.column_split_x else 0.5)
                        if b.x0 < split_x:
                            color = (0, 0.8, 0)  # Green
                        else:
                            color = (0, 0, 0.8)  # Blue
                            
                page.draw_rect(rect, color=color, width=1.5)
                
                order_idx = "?"
                try:
                    if b.textblock_id in ordered_block_ids:
                        order_idx = ordered_block_ids.index(b.textblock_id)
                except ValueError:
                    pass
                
                lbl = f"TB#{b.textblock_id} | O:{order_idx}"
                if is_header: lbl += " | HEADER"
                if is_footer: lbl += " | FOOTER"
                page.insert_text(fitz.Point(x0, max(y0 - 2, 0)), lbl, fontsize=6, color=color)
            
        # 2. Draw Header/Footer Zones
        if layout:
            header_y = layout.header_zone_y * p.height
            footer_y = layout.footer_zone_y * p.height
            page.draw_line(fitz.Point(0, header_y), fitz.Point(p.width, header_y), color=(0.8, 0.8, 0), width=2)
            page.draw_line(fitz.Point(0, footer_y), fitz.Point(p.width, footer_y), color=(0.8, 0, 0), width=2)
            
        # 3. Draw Gutters
        if context.document_layout and context.document_layout.kind == DocumentLayoutKind.DOUBLE_COLUMN:
            global_split = context.document_layout.primary_split_x
            if global_split:
                gx = global_split * p.width
                page.draw_line(fitz.Point(gx, 0), fitz.Point(gx, p.height), color=(1, 0.5, 0), width=3)
                
        if layout and layout.column_count == 2 and layout.column_split_x:
            split_x_px = layout.column_split_x * p.width
            page.draw_line(fitz.Point(split_x_px, 0), fitz.Point(split_x_px, p.height), color=(1, 0.5, 0), width=1.5, dashes="[5 5]")
            
        # 4. Annotate Page & Add Legend to Page 0
        publisher_name = context.publisher.name if context.publisher else "Unknown"
        doc_kind = context.document_layout.kind.name if context.document_layout else "UNKNOWN"
        doc_conf = context.document_layout.confidence if context.document_layout else 0.0
        
        if p.page_num == 0:
            # Legend & Developer Summary on Page 0
            dev_summary = (
                "--- Developer Summary ---\n"
                f"Pages: {len(context.pages)}\n"
                f"Raw TextBlocks: {total_raw_blocks}\n"
                f"TypographicGroups: {total_groups}\n"
                f"Furniture removed: {furniture_removed}\n"
                f"Landmarks detected: {landmarks_detected}\n"
                f"Zones detected: {zones_detected}\n"
                f"Semantic Nodes: {semantic_nodes}\n\n"
                "--- Legend ---\n"
            )
            
            if visualize_semantics:
                dev_summary += (
                    "Renderer: Semantic\n"
                    "Blue: TITLE\n"
                    "Purple: AUTHORS/AFFILIATIONS\n"
                    "Orange: ABSTRACT\n"
                    "Red: SECTION_HEADER\n"
                    "Light Gray: PARAGRAPH\n"
                    "Green/Teal: CAPTIONS\n"
                    "Light Red: REFERENCES\n"
                )
            elif visualize_zones:
                dev_summary += (
                    "Renderer: Zonal\n"
                    "Light Blue: FRONT_MATTER\n"
                    "Green: BODY\n"
                    "Light Red: REFERENCES\n"
                    "Purple: APPENDIX\n"
                )
            elif visualize_landmarks:
                dev_summary += (
                    "Renderer: Landmarks & Groups\n"
                    "Red fill: MATCHED FENCE (Sections)\n"
                    "Blue fill: MATCHED ANCHOR (Title/Abstract)\n"
                    "Orange outline: TYPOGRAPHIC GROUP\n"
                )
            elif visualize_groups:
                dev_summary += (
                    "Renderer: Typographic Groups\n"
                    "Orange outline: TYPOGRAPHIC GROUP\n"
                )
            else:
                dev_summary += (
                    "Renderer: Raw TextBlocks\n"
                    "Green outline: Left Column Block\n"
                    "Blue outline: Right Column Block\n"
                    "Purple outline: Spanning Block\n"
                    "Gray outline: Noise Block\n"
                    "Yellow line: Universal Body Top (M_top)\n"
                    "Red line: Universal Body Bottom (M_bot)\n"
                    "Dashed Orange line: Local Column Split\n"
                    "Solid Orange line: Global Column Split\n"
                )
                
            text_rect = fitz.Rect(10, 10, 250, 350)
            page.draw_rect(text_rect, color=(0,0,0), fill=(1,1,1), width=1, fill_opacity=0.85)
            page.insert_textbox(text_rect, dev_summary, fontsize=10, color=(0,0,0), align=0)

        # Standard Page Annotation (top right)
        annotation_text = (
            f"Page: {p.page_num}\n"
            f"Publisher: {publisher_name}\n"
            f"Local Layout: {layout.column_count if layout else '?'}-col\n"
            f"Doc Layout: {doc_kind} (Conf: {doc_conf:.2f})\n"
        )
        
        text_rect2 = fitz.Rect(p.width - 200, 10, p.width - 10, 80)
        page.draw_rect(text_rect2, color=(0,0,0), fill=(1,1,1), width=1, fill_opacity=0.85)
        page.insert_textbox(text_rect2, annotation_text, fontsize=12, color=(0,0,0), align=0)
        
    doc.save(out_path)
    doc.close()
    
    context.log(
        stage="debug",
        action="generate_debug_pdf",
        reason=f"Saved debug overlay to {out_path}",
        details={"output_path": out_path}
    )
    return context
