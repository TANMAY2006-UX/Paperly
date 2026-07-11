import argparse
import sys
import os

from extractor.ingest import ingest_pdf
from extractor.normalize import normalize_context
from extractor.publishers import detect_publisher
from extractor.layout import detect_layout
from extractor.consensus import detect_consensus
from extractor.debug import draw_debug_overlays
from extractor.ordering import compute_reading_order
from extractor.preprocess import assemble_typographic_groups
from extractor.landmarks import detect_landmarks
from extractor.semantic import reconstruct_semantics
from extractor.models import AssemblyPolicy, ParticipationPolicy

def cmd_inspect(args):
    print(f"Inspecting: {args.pdf_path}")
    slug = os.path.splitext(os.path.basename(args.pdf_path))[0]
    
    # 1. Ingestion
    print("\nStage 1: Ingestion...")
    context = ingest_pdf(args.pdf_path, slug)
    
    total_pages = len(context.pages)
    total_raw_blocks = sum(len(p.blocks) for p in context.pages)
    
    fonts = set()
    sizes = []
    for p in context.pages:
        for b in p.blocks:
            fonts.add(b.font)
            sizes.append(b.size)
            
    print(f"  Total Pages: {total_pages}")
    print(f"  Total Raw Blocks: {total_raw_blocks}")
    if total_pages > 0:
        p0 = context.pages[0]
        print(f"  Page 0 Dimensions: {p0.width:.1f} x {p0.height:.1f}")
        
    if sizes:
        sizes.sort()
        median_size = sizes[len(sizes)//2]
        print(f"  Unique Fonts: {len(fonts)}")
        print(f"  Font Size Range: {min(sizes):.1f}pt - {max(sizes):.1f}pt (Median: {median_size:.1f}pt)")
        
    if total_pages > 0 and len(p0.blocks) > 0:
        b0 = p0.blocks[0]
        print(f"  Sample Raw Coordinate (Block 0): (x0={b0.x0:.1f}, y0={b0.y0:.1f}, x1={b0.x1:.1f}, y1={b0.y1:.1f})")
    
    # 2. Normalization
    print("\nStage 2: Normalization...")
    context = normalize_context(context)
    
    total_norm_blocks = sum(len(p.blocks) for p in context.pages)
    norm_log = next((log for log in context.audit_log if log["stage"] == "normalize"), None)
    
    print(f"  Total Normalized Blocks: {total_norm_blocks}")
    if norm_log:
        print(f"  Ligature Corrections: {norm_log.get('ligatures_resolved', 0)}")
        print(f"  Empty/Zero-area Blocks Removed: {norm_log.get('blocks_removed', 0)}")
        
    if total_pages > 0 and len(context.pages[0].blocks) > 0:
        b0 = context.pages[0].blocks[0]
        print(f"  Sample Normalized Coordinate (Block 0): (x0={b0.x0:.4f}, y0={b0.y0:.4f}, x1={b0.x1:.4f}, y1={b0.y1:.4f})")


def cmd_detect(args):
    print(f"Detecting Layout & Publisher for: {args.pdf_path}")
    slug = os.path.splitext(os.path.basename(args.pdf_path))[0]
    
    context = ingest_pdf(args.pdf_path, slug)
    context = normalize_context(context)
    
    # 3. Publisher Detection
    print("\nStage 3: Publisher Detection...")
    context = detect_publisher(context)
    print(f"  Detected Publisher: {context.publisher.name}")
    
    # 4. Layout Detection
    print("\nStage 4: Per-Page Layout Detection...")
    context = detect_layout(context)
    
    for i, p in enumerate(context.pages[:5]):
        split = f"split at x={p.layout.column_split_x:.3f}" if p.layout.column_split_x else "N/A"
        print(f"  Page {i}: {p.layout.column_count}-column | Split: {split} | Conf: {p.layout.confidence:.2f}")
    
    if len(context.pages) > 5:
        print(f"  ... and {len(context.pages) - 5} more pages.")

    # 4b. Consensus
    print("\nStage 4b: Document Layout Consensus...")
    context = detect_consensus(context)
    if context.document_layout:
        print(f"  Consensus: {context.document_layout.kind.name} (Conf: {context.document_layout.confidence:.2f})")
        print(f"  Primary Gutter: {context.document_layout.primary_split_x}")
        print(f"  Anomaly Pages: {context.document_layout.anomaly_pages}")

def cmd_assemble(args):
    print(f"Stage 1 Typographic Assembly for: {args.pdf_path}")
    slug = os.path.splitext(os.path.basename(args.pdf_path))[0]
    
    context = ingest_pdf(args.pdf_path, slug)
    context = normalize_context(context)
    context = detect_publisher(context)
    context = detect_layout(context)
    context = detect_consensus(context)
    
    ordered_blocks = compute_reading_order(context)
    
    policy = AssemblyPolicy.CONSERVATIVE
    if getattr(args, 'balanced', False):
        policy = AssemblyPolicy.BALANCED
    elif getattr(args, 'aggressive', False):
        policy = AssemblyPolicy.AGGRESSIVE
        
    context = assemble_typographic_groups(ordered_blocks, context, policy=policy)
    
    report = context.quality_reports.get("Stage1_Assembly")
    if report:
        print("\nStage 1 Quality Report:")
        print(f"  Raw Blocks: {report.raw_block_count}")
        print(f"  Participating: {report.participating_blocks}")
        print(f"  Ignored: {report.ignored_blocks}")
        print(f"  Assembled Groups: {report.assembled_groups}")
        print(f"  Fragmentation Ratio: {report.fragmentation_ratio:.2f}")
        print(f"  Average Confidence: {report.average_confidence:.2f}")
        if report.warnings:
            print("  Warnings:")
            for w in report.warnings:
                print(f"    - {w}")

def cmd_landmarks(args):
    print(f"Stage 3A.2 Landmark Detection for: {args.pdf_path}")
    slug = os.path.splitext(os.path.basename(args.pdf_path))[0]
    
    context = ingest_pdf(args.pdf_path, slug)
    
    inspector = None
    if getattr(args, 'telemetry', False) or getattr(args, 'telemetry_json', False) or getattr(args, 'trace_group', None):
        from extractor.telemetry import EventBus
        from extractor.inspector import Inspector
        context.event_bus = EventBus()
        context.telemetry_enabled = True
        inspector = Inspector()
        context.event_bus.subscribe(inspector.receive)
        
    context = normalize_context(context)
    context = detect_publisher(context)
    context = detect_layout(context)
    context = detect_consensus(context)
    
    ordered_blocks = compute_reading_order(context)
    context = assemble_typographic_groups(ordered_blocks, context)
    
    context = detect_landmarks(context)
    
    report = context.landmark_report
    if report:
        from extractor.models import LandmarkKind
        
        fences = [t for t in report.tokens if t.kind == LandmarkKind.OUTLIER]
        anchors = [t for t in report.tokens if t.kind == LandmarkKind.ANCHOR]
        
        print(f"\nDetected {len(fences)} Structural Outliers:")
        for f in fences:
            print(f"  [OUTLIER] Group {f.group_id}")
            
        print(f"\nDetected {len(anchors)} Document Anchors:")
        for a in anchors:
            print(f"  [ANCHOR] Group {a.group_id}")

    if inspector:
        print("\n")
        if getattr(args, 'telemetry_json', False):
            print(inspector.export_json())
        elif getattr(args, 'trace_group', None):
            inspector.print_group_trace(args.trace_group)
        else:
            inspector.print_report()



def cmd_debug(args):
    print(f"Generating Debug PDF for: {args.pdf_path}")
    slug = os.path.splitext(os.path.basename(args.pdf_path))[0]
    
    context = ingest_pdf(args.pdf_path, slug)
    context = normalize_context(context)
    context = detect_publisher(context)
    context = detect_layout(context)
    context = detect_consensus(context)
    
    if args.groups or args.landmarks or args.zones or args.semantic:
        print("\nStage 1: Assembling groups for debug visualization...")
        ordered_blocks = compute_reading_order(context)
        context = assemble_typographic_groups(ordered_blocks, context)
        
    if args.landmarks or args.zones or args.semantic:
        print("\nStage 3A.2: Detecting landmarks for debug visualization...")
        context = detect_landmarks(context)
        


    if args.semantic:
        print("\nStage 3A.2: Reconstructing semantics for debug visualization...")
        context = reconstruct_semantics(context)
    
    print("\nStage 5: Generating Debug PDF...")
    context = draw_debug_overlays(
        context, 
        visualize_groups=args.groups or args.landmarks or args.zones or args.semantic, 
        visualize_landmarks=args.landmarks, 
        visualize_semantics=args.semantic,
        visualize_audit=args.audit_evidence
    )
    
    debug_log = next(log for log in reversed(context.audit_log) if log["action"] == "generate_debug_pdf")
    print(f"  Success: {debug_log.get('output_path')}")

def cmd_semantic(args):
    print(f"Stage 3A.2 Semantic Reconstruction for: {args.pdf_path}")
    slug = os.path.splitext(os.path.basename(args.pdf_path))[0]
    
    context = ingest_pdf(args.pdf_path, slug)
    
    inspector = None
    if getattr(args, 'telemetry', False) or getattr(args, 'telemetry_json', False) or getattr(args, 'trace_group', None):
        from extractor.telemetry import EventBus
        from extractor.inspector import Inspector
        context.event_bus = EventBus()
        context.telemetry_enabled = True
        inspector = Inspector()
        context.event_bus.subscribe(inspector.receive)
        
    context = normalize_context(context)
    context = detect_publisher(context)
    context = detect_layout(context)
    context = detect_consensus(context)
    
    ordered_blocks = compute_reading_order(context)
    context = assemble_typographic_groups(ordered_blocks, context)
    context = detect_landmarks(context)

    context = reconstruct_semantics(context)
    
    tree = context.semantic_tree
    if tree:
        def count_nodes(node):
            return 1 + sum(count_nodes(child) for child in node.children)
        print(f"\nDocument reconstructed into a Semantic Tree with {count_nodes(tree)} nodes:")
        
        def print_tree(node, depth=0):
            indent = "  " * depth
            text_preview = ""
            if node.group:
                text = node.group.display_text.replace("\n", " ").strip()
                if len(text) > 50:
                    text_preview = f" => \"{text[:47]}...\""
                else:
                    text_preview = f" => \"{text}\""
            try:
                print(f"{indent}- {node.node_type.name}{text_preview}")
            except UnicodeEncodeError:
                safe_text = text_preview.encode('ascii', 'replace').decode('ascii')
                print(f"{indent}- {node.node_type.name}{safe_text}")
            for child in node.children:
                print_tree(child, depth + 1)
                
        print_tree(tree, depth=1)
            
    if inspector:
        print("\n")
        if getattr(args, 'telemetry_json', False):
            print(inspector.export_json())
        elif getattr(args, 'trace_group', None):
            inspector.print_group_trace(args.trace_group)
        else:
            inspector.print_report()

def main():
    parser = argparse.ArgumentParser(description="Paperly Phase 3A.0 Extraction Pipeline")
    parser.add_argument("--telemetry", action="store_true", help="Enable telemetry and print inspector report")
    parser.add_argument("--telemetry-json", action="store_true", help="Enable telemetry and print trace as JSON")
    parser.add_argument("--trace-group", type=str, help="Print trace for a specific group ID")
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # inspect
    inspect_parser = subparsers.add_parser("inspect", help="Raw metadata, fonts, blocks, and page dimensions")
    inspect_parser.add_argument("pdf_path", help="Path to the PDF file")
    
    # detect
    detect_parser = subparsers.add_parser("detect", help="Publisher and per-page layout report")
    detect_parser.add_argument("pdf_path", help="Path to the PDF file")
    
    # debug
    debug_parser = subparsers.add_parser("debug", help="Produce a debug PDF with visual overlays")
    debug_parser.add_argument("pdf_path", help="Path to the PDF file")
    debug_parser.add_argument("--groups", action="store_true", help="Visualize assembled TypographicGroups instead of raw blocks")
    debug_parser.add_argument("--landmarks", action="store_true", help="Visualize Structural Fences and Document Anchors")
    debug_parser.add_argument("--zones", action="store_true", help="Visualize Zonal Partitioning")
    debug_parser.add_argument("--semantic", action="store_true", help="Visualize Semantic Reconstruction")
    debug_parser.add_argument("--audit-evidence", action="store_true", help="Visualize hidden physical evidence (Audit Mode)")
    
    # assemble
    assemble_parser = subparsers.add_parser("assemble", help="Run Stage 1 Typographic Assembly")
    assemble_parser.add_argument("pdf_path", help="Path to the PDF file")
    assemble_parser.add_argument("--balanced", action="store_true", help="Use Balanced policy")
    assemble_parser.add_argument("--aggressive", action="store_true", help="Use Aggressive policy")
    
    # landmarks
    landmarks_parser = subparsers.add_parser("landmarks", help="Run Stage 3A.2 Landmark Detection")
    landmarks_parser.add_argument("pdf_path", help="Path to the PDF file")
    

    # semantic
    semantic_parser = subparsers.add_parser("semantic", help="Run Stage 3A.2 Semantic Reconstruction")
    semantic_parser.add_argument("pdf_path", help="Path to the PDF file")
    
    args = parser.parse_args()
    
    if not os.path.exists(args.pdf_path):
        print(f"Error: File not found -> {args.pdf_path}", file=sys.stderr)
        sys.exit(1)
        
    if args.command == "inspect":
        cmd_inspect(args)
    elif args.command == "detect":
        cmd_detect(args)
    elif args.command == "debug":
        cmd_debug(args)
    elif args.command == "assemble":
        cmd_assemble(args)
    elif args.command == "landmarks":
        cmd_landmarks(args)

    elif args.command == "semantic":
        cmd_semantic(args)

if __name__ == "__main__":
    main()
