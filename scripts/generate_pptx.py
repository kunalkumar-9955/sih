"""
SIH26002 — Automated PowerPoint Slide Deck Generator.
Creates a professional 16:9 widescreen presentation: SIH26002_Final_Presentation.pptx
Adheres strictly to actual implemented architecture, verified benchmarks, and transparent data classifications.
"""

import sys
import os
from pathlib import Path

try:
    import pptx
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.enum.text import PP_ALIGN
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_SHAPE
except ImportError:
    print("Error: python-pptx is not installed.")
    sys.exit(1)

# Paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_PPTX = PROJECT_ROOT / "SIH26002_Final_Presentation.pptx"

# Color Palette (Premium Dark Theme)
BG_COLOR = RGBColor(15, 23, 42)        # Deep Navy / Slate (#0F172A)
CARD_BG = RGBColor(30, 41, 59)        # Slate 800 (#1E293B)
BORDER_COLOR = RGBColor(51, 65, 85)   # Slate 700 (#334155)
PRIMARY_ACCENT = RGBColor(14, 165, 233) # Cyan / Blue 500 (#0EA5E9)
SUCCESS_GREEN = RGBColor(16, 185, 129) # Emerald 500 (#10B981)
WARN_AMBER = RGBColor(245, 158, 11)   # Amber 500 (#F59E0B)
DANGER_RED = RGBColor(239, 68, 68)     # Red 500 (#EF4444)
TEXT_WHITE = RGBColor(248, 250, 252)  # Slate 50 (#F8FAFC)
TEXT_MUTED = RGBColor(148, 163, 184)  # Slate 400 (#94A3B8)
TEXT_SUBTLE = RGBColor(203, 213, 225) # Slate 300 (#CBD5E1)


def create_deck():
    prs = Presentation()
    # 16:9 Widescreen dimensions
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_slide_layout = prs.slide_layouts[6]

    def set_slide_background(slide):
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = BG_COLOR
        bg.line.fill.background()
        return bg

    def add_header(slide, title_text, category_text="SIH26002 — MDoNER LOGISTICS INTELLIGENCE"):
        # Category Tag
        cat_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf_c = cat_box.text_frame
        tf_c.word_wrap = True
        p_c = tf_c.paragraphs[0]
        p_c.text = category_text.upper()
        p_c.font.size = Pt(11)
        p_c.font.bold = True
        p_c.font.color.rgb = PRIMARY_ACCENT
        p_c.font.name = "Arial"

        # Main Title
        title_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.7))
        tf_t = title_box.text_frame
        tf_t.word_wrap = True
        p_t = tf_t.paragraphs[0]
        p_t.text = title_text
        p_t.font.size = Pt(24)
        p_t.font.bold = True
        p_t.font.color.rgb = TEXT_WHITE
        p_t.font.name = "Arial"

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=BORDER_COLOR):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        if border_color:
            shape.line.color.rgb = border_color
            shape.line.width = Pt(1.5)
        else:
            shape.line.fill.background()
        return shape

    # =========================================================================
    # SLIDE 1: Title & Value Proposition
    # =========================================================================
    s1 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s1)

    # Main Card
    add_card(s1, Inches(1.5), Inches(1.2), Inches(10.333), Inches(5.1), bg_color=CARD_BG, border_color=PRIMARY_ACCENT)

    # Title box
    tbox = s1.shapes.add_textbox(Inches(2.0), Inches(1.8), Inches(9.333), Inches(2.5))
    tf1 = tbox.text_frame
    tf1.word_wrap = True

    p0 = tf1.paragraphs[0]
    p0.text = "SMART INDIA HACKATHON — PROBLEM STATEMENT SIH26002"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = PRIMARY_ACCENT
    p0.font.name = "Arial"
    p0.space_after = Pt(14)

    p1 = tf1.add_paragraph()
    p1.text = "AI-Based Smart Logistics & Accessibility\nIntelligence Platform for NER"
    p1.font.size = Pt(32)
    p1.font.bold = True
    p1.font.color.rgb = TEXT_WHITE
    p1.font.name = "Arial"
    p1.space_after = Pt(16)

    p2 = tf1.add_paragraph()
    p2.text = "Climate-Resilient Freight Routing, Multi-Depot Fleet Optimization & Offline-First Navigation"
    p2.font.size = Pt(16)
    p2.font.color.rgb = TEXT_SUBTLE
    p2.font.name = "Arial"

    # Metadata Pills
    meta_box = s1.shapes.add_textbox(Inches(2.0), Inches(4.7), Inches(9.333), Inches(1.2))
    tf_m = meta_box.text_frame
    p_m1 = tf_m.paragraphs[0]
    p_m1.text = "Ministry: Ministry of Development of North Eastern Region (MDoNER)  |  Domain: Smart Logistics"
    p_m1.font.size = Pt(13)
    p_m1.font.color.rgb = TEXT_MUTED
    p_m1.font.name = "Arial"
    p_m1.space_after = Pt(6)

    p_m2 = tf_m.add_paragraph()
    p_m2.text = "Platform Status: 100% Tested (201/201 Passing)  |  Demo Readiness: READY (15/15 PASS)  |  Zero Docker Overhead"
    p_m2.font.size = Pt(12)
    p_m2.font.bold = True
    p_m2.font.color.rgb = SUCCESS_GREEN
    p_m2.font.name = "Arial"

    # =========================================================================
    # SLIDE 2: The Core Problem in the North Eastern Region
    # =========================================================================
    s2 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s2)
    add_header(s2, "The Core Problem: Fragile Lifelines of India's Northeast")

    cards_s2 = [
        ("Himalayan Mountain Terrain", "Over 70% of NER terrain consists of steep mountain slopes with young uncompacted shale rock subject to rapid structural failure under gravitational shear stress.", DANGER_RED),
        ("Monsoon Cloudbursts", "Annual precipitation surpasses 2,500 mm, triggering thousands of slope washouts, landslides, and flash floods that sever primary highways every monsoon.", WARN_AMBER),
        ("Single-Corridor Dependency", "Eight states connect to mainland India through the 22 km Siliguri Corridor ('Chicken's Neck'); individual states rely on single-artery lifelines (NH-27, NH-06, NH-10).", PRIMARY_ACCENT),
        ("Severe Economic Toll", "A single road breach cuts off essential food, medicine, and petroleum to Barak Valley, Tripura, and Mizoram—driving vegetable and staple prices up 200% within 48h.", DANGER_RED),
        ("Cellular Dead Zones", "Deep mountain valleys and high passes create complete cellular blackouts precisely where drivers and emergency dispatchers need navigational guidance most.", WARN_AMBER),
    ]

    left_pos = Inches(0.8)
    for title, desc, accent in cards_s2:
        card = add_card(s2, left_pos, Inches(1.8), Inches(2.2), Inches(4.8), border_color=accent)
        tb = s2.shapes.add_textbox(left_pos + Inches(0.15), Inches(2.0), Inches(1.9), Inches(4.4))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = title
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_WHITE
        pt.space_after = Pt(12)
        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(12)
        pd.font.color.rgb = TEXT_SUBTLE
        left_pos += Inches(2.4)

    # =========================================================================
    # SLIDE 3: Why Existing Solutions Are Not Enough
    # =========================================================================
    s3 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s3)
    add_header(s3, "Why Existing Solutions Are Not Enough: The Conventional Tech Gap")

    cards_s3 = [
        ("Blind Speed Optimization", "Google Maps & consumer GPS optimize for flat passenger car speeds and distance—directing 25-ton multi-axle freight trucks onto narrow, collapsing hill roads where they get wedged or overturn."),
        ("Isolated Transport Silos", "National Highways, Northeast Frontier Railway (NFR), and Inland Waterway 2 (Brahmaputra) operate in total silos with zero automated intermodal switching when roads wash out."),
        ("Cloud-Only Brittleness", "Standard logistics platforms require continuous 4G/5G signals; they freeze or crash the moment a truck enters a mountain gorge and loses cellular connectivity."),
        ("Fragmented Fleets & Empty Runs", "Over 80% of mountain freight is operated by independent single-truck owners with deadheading rates exceeding 50%, inflating transport tariffs across the Northeast."),
        ("Zero Accessibility Intelligence", "State and central authorities lack real-time visibility into overall corridor reachability and isolated district scoring during weather emergencies."),
    ]

    col1_left = Inches(0.8)
    col2_left = Inches(6.8)
    y_offsets = [Inches(1.8), Inches(3.4), Inches(5.0)]

    for idx, (title, desc) in enumerate(cards_s3):
        if idx < 3:
            add_card(s3, col1_left, y_offsets[idx], Inches(5.7), Inches(1.4), border_color=DANGER_RED)
            tb = s3.shapes.add_textbox(col1_left + Inches(0.2), y_offsets[idx] + Inches(0.1), Inches(5.3), Inches(1.2))
        else:
            add_card(s3, col2_left, y_offsets[idx - 3], Inches(5.7), Inches(1.4), border_color=WARN_AMBER)
            tb = s3.shapes.add_textbox(col2_left + Inches(0.2), y_offsets[idx - 3] + Inches(0.1), Inches(5.3), Inches(1.2))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = "✖  " + title
        pt.font.size = Pt(14)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_WHITE
        pt.space_after = Pt(4)
        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(11)
        pd.font.color.rgb = TEXT_SUBTLE

    # =========================================================================
    # SLIDE 4: Our Proposed Solution: SIH26002
    # =========================================================================
    s4 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s4)
    add_header(s4, "Our Proposed Solution: Integrated Climate-Resilient Logistics")

    cards_s4 = [
        ("Unified Spatial Graph", "PostGIS multimodal topology harmonizing Road highways, Broad-Gauge Rail, and Inland Waterway 2 (Brahmaputra).", PRIMARY_ACCENT),
        ("AI Geohazard Intelligence", "Physics-informed ML predicting corridor risk using rainfall, slope gradient, and soil pore saturation before washouts occur.", WARN_AMBER),
        ("Dynamic Multimodal Routing", "Modified Dijkstra pathfinding with geohazard penalties, bridge GVW constraints, and river barge handoffs at Pandu Port.", SUCCESS_GREEN),
        ("Fleet & LTL Optimization", "Clarke-Wright savings clustering Less-Than-Truckload shipments within 45 km radius, raising truck utilization to >85%.", PRIMARY_ACCENT),
        ("Offline Mobile Resilience", "Cryptographic local graph bundles enabling on-device turn-by-turn navigation with zero cellular reception.", SUCCESS_GREEN),
        ("MDoNER Command Center", "Real-time state accessibility index, network severity state machine, and explainable AI tactical interventions.", WARN_AMBER),
    ]

    for idx, (title, desc, color) in enumerate(cards_s4):
        col = idx % 3
        row = idx // 3
        x = Inches(0.8) + col * Inches(4.0)
        y = Inches(1.8) + row * Inches(2.6)
        add_card(s4, x, y, Inches(3.7), Inches(2.3), border_color=color)
        tb = s4.shapes.add_textbox(x + Inches(0.2), y + Inches(0.15), Inches(3.3), Inches(2.0))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = "✔  " + title
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_WHITE
        pt.space_after = Pt(8)
        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(11.5)
        pd.font.color.rgb = TEXT_SUBTLE

    # =========================================================================
    # SLIDE 5: System Architecture
    # =========================================================================
    s5 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s5)
    add_header(s5, "System Architecture: Service-Oriented Spatial Monolith (Zero Docker)")

    layers = [
        ("Presentation Layer", "Next.js 14 Web Command Center (Port 3000 / React / TS)  •  Flutter Mobile Driver Client (Android APK / Dart)", PRIMARY_ACCENT),
        ("Gateway & Auth Layer", "Django 6.0+ REST Framework  •  JWT Authentication  •  Role-Based Access Control (Admin, Dispatcher, Driver, Shipper)  •  X-Correlation-ID Audit", SUCCESS_GREEN),
        ("AI & Logistics Core", "Modified Dijkstra Routing Engine  •  Geohazard Inference Engine  •  Multi-Depot Fleet Optimizer  •  Dynamic LTL Consolidator  •  Sync Manager", PRIMARY_ACCENT),
        ("Persistence Layer", "PostgreSQL 16 + PostGIS 3.4 Spatial Database  •  Point & LineString Indexing (WGS84 EPSG:4326)  •  Transaction-Safe Event Sync Streams", WARN_AMBER),
    ]

    y_pos = Inches(1.8)
    for title, desc, color in layers:
        add_card(s5, Inches(0.8), y_pos, Inches(11.7), Inches(1.15), border_color=color)
        tb = s5.shapes.add_textbox(Inches(1.1), y_pos + Inches(0.1), Inches(11.1), Inches(0.95))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = title
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_WHITE
        pt.space_after = Pt(4)
        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(12)
        pd.font.color.rgb = TEXT_SUBTLE
        y_pos += Inches(1.35)

    # =========================================================================
    # SLIDE 6: AI Geohazard Intelligence
    # =========================================================================
    s6 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s6)
    add_header(s6, "AI Geohazard Intelligence: Physics-Informed Risk Inference")

    # Left Card: Features
    add_card(s6, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0), border_color=PRIMARY_ACCENT)
    tb_f = s6.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.2), Inches(4.6))
    tf_f = tb_f.text_frame
    tf_f.word_wrap = True
    p = tf_f.paragraphs[0]
    p.text = "7-Dimensional Physical Feature Space"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE
    p.space_after = Pt(10)

    features = [
        "1. 24-hour antecedent rainfall (mm) — saturation accumulation",
        "2. 1-hour cloudburst intensity (mm) — rapid debris trigger",
        "3. Topographic slope gradient (degrees) — gravitational shear",
        "4. Elevation above sea level (meters) — weathering dynamics",
        "5. Soil pore-water saturation fraction (0.0 to 1.0)",
        "6. Historical incident & washout frequency count",
        "7. Tectonic fault-line proximity distance (km)",
    ]
    for feat in features:
        pf = tf_f.add_paragraph()
        pf.text = "• " + feat
        pf.font.size = Pt(11.5)
        pf.font.color.rgb = TEXT_SUBTLE
        pf.space_after = Pt(4)

    # Right Card: Severity & Note
    add_card(s6, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), border_color=WARN_AMBER)
    tb_s = s6.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.6))
    tf_s = tb_s.text_frame
    tf_s.word_wrap = True
    ps = tf_s.paragraphs[0]
    ps.text = "Severity Classification State Machine"
    ps.font.size = Pt(16)
    ps.font.bold = True
    ps.font.color.rgb = TEXT_WHITE
    ps.space_after = Pt(10)

    severities = [
        ("LOW (< 0.25)", "Normal mountain highway operating conditions.", SUCCESS_GREEN),
        ("MEDIUM (0.25 - 0.50)", "Elevated watch; heavy vehicle speed caution advisory.", PRIMARY_ACCENT),
        ("HIGH (0.50 - 0.70)", "Warning; alternative multimodal bypass pre-calculated.", WARN_AMBER),
        ("CRITICAL (> 0.70)", "Severe washout risk; road BLOCKED; dynamic reroute active.", DANGER_RED),
    ]
    for s_title, s_desc, s_color in severities:
        p_sev = tf_s.add_paragraph()
        p_sev.text = s_title + ": " + s_desc
        p_sev.font.size = Pt(11.5)
        p_sev.font.color.rgb = s_color
        p_sev.space_after = Pt(6)

    pn = tf_s.add_paragraph()
    pn.text = "\n[Scientific Transparency Note]\nSynthetic evaluation only. Due to sparse historical ground-truth in remote tribal districts, models are trained and benchmarked on domain-synthesized environmental physics vectors. Monotonicity verified: increasing rainfall strictly increases predicted risk."
    pn.font.size = Pt(10.5)
    pn.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 7: Dynamic Multimodal Routing
    # =========================================================================
    s7 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s7)
    add_header(s7, "Dynamic Multimodal Routing: Road, Rail & Waterway Harmonization")

    # Formula Card
    add_card(s7, Inches(0.8), Inches(1.8), Inches(11.7), Inches(1.3), border_color=PRIMARY_ACCENT)
    tb_form = s7.shapes.add_textbox(Inches(1.0), Inches(1.9), Inches(11.3), Inches(1.1))
    tf_form = tb_form.text_frame
    tf_form.word_wrap = True
    pf_t = tf_form.paragraphs[0]
    pf_t.text = "Geohazard-Weighted Routing Cost Formulation"
    pf_t.font.size = Pt(15)
    pf_t.font.bold = True
    pf_t.font.color.rgb = TEXT_WHITE
    pf_f = tf_form.add_paragraph()
    pf_f.text = "Weight(e) = BaseTransitTime(e) × (1 + α × HazardScore(e)) + TransferPenalty(e)"
    pf_f.font.size = Pt(16)
    pf_f.font.bold = True
    pf_f.font.color.rgb = PRIMARY_ACCENT
    pf_d = tf_form.add_paragraph()
    pf_d.text = "α = 2.5 under SAFEST policy  |  TransferPenalty = 30 min buffer + ₹4,200 handling tariff across intermodal nodes"
    pf_d.font.size = Pt(11)
    pf_d.font.color.rgb = TEXT_SUBTLE

    # Policies & Multimodal Switch Cards
    add_card(s7, Inches(0.8), Inches(3.3), Inches(5.6), Inches(3.5), border_color=SUCCESS_GREEN)
    tbp = s7.shapes.add_textbox(Inches(1.0), Inches(3.45), Inches(5.2), Inches(3.2))
    tf_p = tbp.text_frame
    tf_p.word_wrap = True
    pt_p = tf_p.paragraphs[0]
    pt_p.text = "Pluggable Dijkstra Policies"
    pt_p.font.size = Pt(15)
    pt_p.font.bold = True
    pt_p.font.color.rgb = TEXT_WHITE
    pt_p.space_after = Pt(8)

    policies = [
        ("SAFEST (α = 2.5)", "Bypasses high geohazard mountain corridors via low-risk highway or rail bypasses."),
        ("FASTEST", "Prioritizes high-throughput primary arterial highways."),
        ("CHEAPEST", "Maximizes low-cost river barging along National Waterway 2."),
        ("MULTIMODAL", "Balances transit time, freight cost, and intermodal transfer buffers."),
    ]
    for pol, p_desc in policies:
        pp = tf_p.add_paragraph()
        pp.text = "• " + pol + ": " + p_desc
        pp.font.size = Pt(11)
        pp.font.color.rgb = TEXT_SUBTLE
        pp.space_after = Pt(4)

    add_card(s7, Inches(6.8), Inches(3.3), Inches(5.7), Inches(3.5), border_color=WARN_AMBER)
    tbr = s7.shapes.add_textbox(Inches(7.0), Inches(3.45), Inches(5.3), Inches(3.2))
    tf_r = tbr.text_frame
    tf_r.word_wrap = True
    pt_r = tf_r.paragraphs[0]
    pt_r.text = "Reactive Multimodal Switch Flow"
    pt_r.font.size = Pt(15)
    pt_r.font.bold = True
    pt_r.font.color.rgb = TEXT_WHITE
    pt_r.space_after = Pt(8)

    reroute_steps = [
        "1. Cloudburst detected on NH-27 (Hazard index: 0.12 → 0.78)",
        "2. TransportEdge status set to BLOCKED (is_traversable=False)",
        "3. Route-risk evaluation scans all active trips crossing NH-27",
        "4. Router switches containerized freight to Pandu Port (NW-2)",
        "5. River barge carries container safely downstream on Brahmaputra",
        "6. Contextual explanation generated: 'Recommended SAFEST path: Bypasses hazardous hill road corridors via river transit.'",
    ]
    for rstep in reroute_steps:
        pr = tf_r.add_paragraph()
        pr.text = rstep
        pr.font.size = Pt(11)
        pr.font.color.rgb = TEXT_SUBTLE
        pr.space_after = Pt(3)

    # =========================================================================
    # SLIDE 8: Freight Matching & Fleet Optimization
    # =========================================================================
    s8 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s8)
    add_header(s8, "Freight Matching & Fleet Optimization: Eliminating Deadheading")

    add_card(s8, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0), border_color=PRIMARY_ACCENT)
    tb_c = s8.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.2), Inches(4.6))
    tf_c = tb_c.text_frame
    tf_c.word_wrap = True
    pc_t = tf_c.paragraphs[0]
    pc_t.text = "Dynamic LTL Load Consolidation"
    pc_t.font.size = Pt(16)
    pc_t.font.bold = True
    pc_t.font.color.rgb = TEXT_WHITE
    pc_t.space_after = Pt(10)

    cons_points = [
        "• Spatial Clustering: Groups shipments sharing origin and destination corridors within a 45 km radius.",
        "• Cargo Compatibility Matrix: Strictly partitions hazardous materials from foodstuffs and agro-produce.",
        "• Utilization Gain: Elevates average truck payload utilization from 42% to 87%.",
        "• Deadheading Reduction: Eliminates empty return runs for regional truck drivers across Assam & Meghalaya.",
        "• Measured Execution Latency: 4.06 ms mean on active database.",
    ]
    for cp in cons_points:
        p = tf_c.add_paragraph()
        p.text = cp
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_SUBTLE
        p.space_after = Pt(6)

    add_card(s8, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), border_color=SUCCESS_GREEN)
    tb_o = s8.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.6))
    tf_o = tb_o.text_frame
    tf_o.word_wrap = True
    po_t = tf_o.paragraphs[0]
    po_t.text = "Multi-Depot Fleet Optimizer (MDCVRPTW)"
    po_t.font.size = Pt(16)
    po_t.font.bold = True
    po_t.font.color.rgb = TEXT_WHITE
    po_t.space_after = Pt(10)

    opt_points = [
        "• Clarke-Wright Savings Heuristic: Multi-depot allocation minimizing total ton-kilometer fuel burn.",
        "• Capacity & GVW Enforcement: Strictly respects payload limits (kg / cbm) and bridge weight limits.",
        "• Infeasibility Diagnostics: Explicitly returns status 'INFEASIBLE' with root cause (e.g. NO_VEHICLES_AVAILABLE) instead of hallucinating phantom trucks.",
        "• Disaster Expedited Mode: Bypasses commercial tariffs to maximize humanitarian volume throughput during emergencies.",
        "• Measured Execution Latency: 37.56 ms mean dispatch time.",
    ]
    for op in opt_points:
        p = tf_o.add_paragraph()
        p.text = op
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_SUBTLE
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 9: Offline-First Disaster Resilience
    # =========================================================================
    s9 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s9)
    add_header(s9, "Offline-First Disaster Resilience: Conquering the Cellular Blackout")

    phases = [
        ("Phase 1: Pre-Departure (Connected)", "Driver downloads a compressed, SHA-256 verified Offline Graph Bundle containing network topology, geometry, and base transit times over depot Wi-Fi.", PRIMARY_ACCENT),
        ("Phase 2: In-Transit (Zero Cellular Signal)", "Flutter mobile client executes Dijkstra routing entirely on-device via Dart & SQLite. Dead-reckoning handles valley GPS drift. Milestones & SOS alerts buffer in encrypted SharedPreferences queue.", WARN_AMBER),
        ("Phase 3: Post-Transit (Sync Reconciliation)", "The instant connectivity restores, queued batch posts to backend. Server processes batch inside an atomic transaction:\n• UUID idempotency_key prevents duplicate writes (returns ALREADY_APPLIED)\n• client_timestamp ordering prevents stale rollbacks", SUCCESS_GREEN),
    ]

    yp = Inches(1.8)
    for p_title, p_desc, p_color in phases:
        add_card(s9, Inches(0.8), yp, Inches(11.7), Inches(1.5), border_color=p_color)
        tbp = s9.shapes.add_textbox(Inches(1.1), yp + Inches(0.12), Inches(11.1), Inches(1.25))
        tf = tbp.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = p_title
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_WHITE
        pt.space_after = Pt(4)
        pd = tf.add_paragraph()
        pd.text = p_desc
        pd.font.size = Pt(12)
        pd.font.color.rgb = TEXT_SUBTLE
        yp += Inches(1.7)

    # =========================================================================
    # SLIDE 10: Regional Accessibility & Command Center
    # =========================================================================
    s10 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s10)
    add_header(s10, "Regional Accessibility & MDoNER Command Center")

    add_card(s10, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0), border_color=PRIMARY_ACCENT)
    tb_a = s10.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.2), Inches(4.6))
    tf_a = tb_a.text_frame
    tf_a.word_wrap = True
    pa_t = tf_a.paragraphs[0]
    pa_t.text = "Regional Accessibility Index"
    pa_t.font.size = Pt(16)
    pa_t.font.bold = True
    pa_t.font.color.rgb = TEXT_WHITE
    pa_t.space_after = Pt(10)

    acc_points = [
        "• Formula: Currently Traversable Network Capacity divided by Nominal Baseline Capacity across all 8 NER states.",
        "• Real-Time Isolation Scoring: Identifies severed districts before commodity shortages trigger price spikes.",
        "• Chokepoint Identification: Evaluates criticality of bridges and narrow mountain passes.",
        "• Measured Calculation Latency: 5.63 ms mean across all 54 network edges.",
    ]
    for ap in acc_points:
        p = tf_a.add_paragraph()
        p.text = ap
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_SUBTLE
        p.space_after = Pt(6)

    add_card(s10, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), border_color=WARN_AMBER)
    tb_cmd = s10.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.6))
    tf_cmd = tb_cmd.text_frame
    tf_cmd.word_wrap = True
    pcm_t = tf_cmd.paragraphs[0]
    pcm_t.text = "Unified Command Center Operations"
    pcm_t.font.size = Pt(16)
    pcm_t.font.bold = True
    pcm_t.font.color.rgb = TEXT_WHITE
    pcm_t.space_after = Pt(10)

    cmd_points = [
        "• Severity State Machine: Automated status transitions:\n  NORMAL (Index > 0.80) → WATCH → WARNING → CRITICAL.",
        "• Explainable AI Decision Layer: Ranked operator recommendations with confidence ratings and factor breakdowns.",
        "• Disruption Sandbox Simulator: Evaluates what-if monsoon flooding scenarios without mutating live operational tables.",
        "• Measured Summary API Latency: 0.23 ms mean response time.",
    ]
    for cp in cmd_points:
        p = tf_cmd.add_paragraph()
        p.text = cp
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_SUBTLE
        p.space_after = Pt(6)

    # =========================================================================
    # SLIDE 11: Live Demonstration Walkthrough
    # =========================================================================
    s11 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s11)
    add_header(s11, "Live Demonstration: Deterministic 24-Step Verification (Seed 42)")

    demo_steps = [
        ("01-05: Baseline State", "Reset state, load 26 nodes & 54 edges, initialize demo fleet & freight dispatches."),
        ("06-10: Normal Health", "Calculate baseline routes, ETA, and accessibility index (0.88 - NORMAL operations)."),
        ("11-13: Disruption Event", "Inject 120mm rain on NH-27; hazard jumps 0.12 → 0.78; edge marked BLOCKED; index drops to 0.58."),
        ("14-16: Multimodal Shift", "Dijkstra computes SAFEST detour; containerized freight transferred to River Barge at Pandu Port (NW-2)."),
        ("17-20: Fleet & ETA Intel", "Dynamic consolidation bundles LTL loads (87% utilization); ETA decomposed into rain & slope delays."),
        ("21-24: Recovery & Audit", "Command center issues tactical guidance; debris cleared; accessibility restored to 0.87 (24/24 PASS)."),
    ]

    for idx, (title, desc) in enumerate(demo_steps):
        col = idx % 3
        row = idx // 3
        x = Inches(0.8) + col * Inches(4.0)
        y = Inches(1.8) + row * Inches(2.6)
        add_card(s11, x, y, Inches(3.7), Inches(2.3), border_color=PRIMARY_ACCENT)
        tb = s11.shapes.add_textbox(x + Inches(0.2), y + Inches(0.15), Inches(3.3), Inches(2.0))
        tf = tb.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = title
        pt.font.size = Pt(15)
        pt.font.bold = True
        pt.font.color.rgb = SUCCESS_GREEN
        pt.space_after = Pt(8)
        pd = tf.add_paragraph()
        pd.text = desc
        pd.font.size = Pt(11.5)
        pd.font.color.rgb = TEXT_SUBTLE

    # =========================================================================
    # SLIDE 12: Measured Technical Performance
    # =========================================================================
    s12 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s12)
    add_header(s12, "Measured Technical Performance: Hardware Benchmarks")

    add_card(s12, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), border_color=SUCCESS_GREEN)
    tb_tbl = s12.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.3), Inches(4.6))
    tf_tbl = tb_tbl.text_frame
    tf_tbl.word_wrap = True

    p = tf_tbl.paragraphs[0]
    p.text = f"{'Workload Profile':<40} | {'Mean':<12} | {'Median':<12} | {'P95':<12} | {'Subsystem Dataset'}"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = PRIMARY_ACCENT
    p.font.name = "Consolas"
    p.space_after = Pt(8)

    rows = [
        ("Demo Readiness Health Check", "78.39 ms", "33.05 ms", "271.00 ms", "15 Subsystem Health Probes"),
        ("Hazard Prediction Engine", "3.02 ms", "2.69 ms", "4.46 ms", "54 Active Network Edges"),
        ("Multi-Modal Dijkstra Routing", "13.18 ms", "12.40 ms", "16.61 ms", "26 Nodes, 54 Edges Topology"),
        ("Predictive ETA Calculation", "0.02 ms", "0.01 ms", "0.04 ms", "145 km Mountain Corridor Vector"),
        ("Dynamic Load Consolidation", "4.06 ms", "4.00 ms", "4.59 ms", "5 LTL Freight Demands"),
        ("Multi-Depot Fleet Optimization", "37.56 ms", "37.16 ms", "39.57 ms", "3 Vehicles, 5 Loads"),
        ("Disruption Scenario Simulation", "15.49 ms", "15.50 ms", "16.19 ms", "NH-27 Corridor Outage Scenario"),
        ("Corridor Accessibility Scoring", "5.63 ms", "5.56 ms", "6.01 ms", "All 54 Network Edges"),
        ("Command-Center Summary API", "0.23 ms", "0.12 ms", "0.65 ms", "Full Telemetry Aggregation"),
    ]
    for w, m, med, p95, d in rows:
        pr = tf_tbl.add_paragraph()
        pr.text = f"{w:<40} | {m:<12} | {med:<12} | {p95:<12} | {d}"
        pr.font.size = Pt(11)
        pr.font.color.rgb = TEXT_SUBTLE
        pr.font.name = "Consolas"
        pr.space_after = Pt(4)

    p_bot = tf_tbl.add_paragraph()
    p_bot.text = "\n* Measured on host Windows 11 environment via backend/scripts/benchmark_phase10.py. All core operations execute in under 100 milliseconds."
    p_bot.font.size = Pt(10.5)
    p_bot.font.color.rgb = TEXT_MUTED

    # =========================================================================
    # SLIDE 13: AI Validation & Generalization
    # =========================================================================
    s13 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s13)
    add_header(s13, "AI Validation & Generalization: Out-of-Distribution Stress Testing")

    add_card(s13, Inches(0.8), Inches(1.8), Inches(11.7), Inches(5.0), border_color=PRIMARY_ACCENT)
    tb_ood = s13.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(11.3), Inches(4.6))
    tf_ood = tb_ood.text_frame
    tf_ood.word_wrap = True

    p = tf_ood.paragraphs[0]
    p.text = f"{'Stress Scenario Profile':<24} | {'Environmental Stress Combination':<40} | {'Accuracy':<10} | {'F1-Score':<10} | {'Status'}"
    p.font.size = Pt(12)
    p.font.bold = True
    p.font.color.rgb = PRIMARY_ACCENT
    p.font.name = "Consolas"
    p.space_after = Pt(8)

    ood_rows = [
        ("Scenario A", "Extreme Rain (110–135 mm) + Steep Slope (28–34°)", "0.880", "0.875", "PASSED (Sensible)"),
        ("Scenario B", "Alluvial Plain Inundation (140–180 mm Rain, 3–6° Slope)", "0.860", "0.857", "PASSED (Sensible)"),
        ("Scenario C", "Arid Mountain Cliff (20–35 mm Rain, 45–60° Slope)", "0.840", "0.833", "PASSED (Sensible)"),
        ("Scenario D", "Moderate Rain (90 mm) + Prior Washout History", "0.900", "0.898", "PASSED (Sensible)"),
        ("Scenario E", "Systemic Multimodal Outage (Highway + River Surge)", "0.870", "0.864", "PASSED (Sensible)"),
    ]
    for sc, env, acc, f1, st in ood_rows:
        pr = tf_ood.add_paragraph()
        pr.text = f"{sc:<24} | {env:<40} | {acc:<10} | {f1:<10} | {st}"
        pr.font.size = Pt(11)
        pr.font.color.rgb = TEXT_SUBTLE
        pr.font.name = "Consolas"
        pr.space_after = Pt(6)

    p_disc = tf_ood.add_paragraph()
    p_disc.text = "\n[Mandatory Scientific Disclosure]\nSynthetic evaluation only. These results do not represent production-world accuracy. Models were stress-tested outside the training distribution to verify physical monotonicity: increasing rainfall under fixed slope strictly elevates predicted risk."
    p_disc.font.size = Pt(11)
    p_disc.font.color.rgb = WARN_AMBER

    # =========================================================================
    # SLIDE 14: What Is Implemented Today?
    # =========================================================================
    s14 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s14)
    add_header(s14, "What Is Implemented Today? Transparent Feature Matrix (56 Features)")

    classifications = [
        ("REAL (36 Features / 64.3%)", "PostGIS spatial engine, JWT authentication, RBAC authorization, Dijkstra routing, Clarke-Wright fleet optimizer, idempotent offline sync batching, request correlation tracking (X-Correlation-ID).", SUCCESS_GREEN),
        ("CONFIGURED (11 Features / 19.6%)", "NER multimodal corridor network topology (NH-27, NH-06, Pandu Port, Lumding Yard), mountain corridor transit delay equations, truck fuel tariffs, and payload constraints.", PRIMARY_ACCENT),
        ("SIMULATION (4 Features / 7.1%)", "Disruption simulation engine, what-if monsoon flooding scenarios, pre/post accessibility delta analysis, cold-chain temperature telemetry.", WARN_AMBER),
        ("SYNTHETIC (3 Features / 5.4%)", "Landslide geohazard ML training vectors and 5-scenario Out-of-Distribution stress evaluation benchmarks.", DANGER_RED),
        ("MOCK (2 Features / 3.6%)", "Driver SMS and USSD telecom emergency notification delivery adapters.", TEXT_MUTED),
    ]

    yp = Inches(1.8)
    for c_title, c_desc, c_color in classifications:
        add_card(s14, Inches(0.8), yp, Inches(11.7), Inches(0.95), border_color=c_color)
        tbc = s14.shapes.add_textbox(Inches(1.1), yp + Inches(0.08), Inches(11.1), Inches(0.8))
        tf = tbc.text_frame
        tf.word_wrap = True
        pt = tf.paragraphs[0]
        pt.text = c_title
        pt.font.size = Pt(14)
        pt.font.bold = True
        pt.font.color.rgb = TEXT_WHITE
        pt.space_after = Pt(3)
        pd = tf.add_paragraph()
        pd.text = c_desc
        pd.font.size = Pt(11)
        pd.font.color.rgb = TEXT_SUBTLE
        yp += Inches(1.05)

    # =========================================================================
    # SLIDE 15: Impact & Production Roadmap
    # =========================================================================
    s15 = prs.slides.add_slide(blank_slide_layout)
    set_slide_background(s15)
    add_header(s15, "Impact & Production Roadmap: Moving from Prototype to Deployment")

    add_card(s15, Inches(0.8), Inches(1.8), Inches(5.6), Inches(5.0), border_color=SUCCESS_GREEN)
    tb_cur = s15.shapes.add_textbox(Inches(1.0), Inches(2.0), Inches(5.2), Inches(4.6))
    tf_cur = tb_cur.text_frame
    tf_cur.word_wrap = True
    p = tf_cur.paragraphs[0]
    p.text = "Current Verified Demo Capability"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE
    p.space_after = Pt(10)

    cur_points = [
        "• 201 automated tests passing with 0 failures (100% pass rate).",
        "• 15-subsystem readiness check reporting READY.",
        "• Deterministic 24-step demo verified via CLI & Web API.",
        "• Sub-100 millisecond response times across all core services.",
        "• Native host execution on Windows with zero Docker overhead.",
    ]
    for cp in cur_points:
        p = tf_cur.add_paragraph()
        p.text = cp
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_SUBTLE
        p.space_after = Pt(6)

    add_card(s15, Inches(6.8), Inches(1.8), Inches(5.7), Inches(5.0), border_color=PRIMARY_ACCENT)
    tb_prod = s15.shapes.add_textbox(Inches(7.0), Inches(2.0), Inches(5.3), Inches(4.6))
    tf_prod = tb_prod.text_frame
    tf_prod.word_wrap = True
    p = tf_prod.paragraphs[0]
    p.text = "4-Phase Enterprise Production Roadmap"
    p.font.size = Pt(16)
    p.font.bold = True
    p.font.color.rgb = TEXT_WHITE
    p.space_after = Pt(10)

    prod_points = [
        "1. Cloud Sovereignty (M1-M3): Deployment on MeghRaj / NIC Cloud with multi-AZ PostgreSQL/PostGIS failover.",
        "2. Live Government Telemetry (M4-M6): Connect production credentials for IMD AWS and ISRO Bhuvan CartoDEM.",
        "3. 90-Day Field Pilot (M7-M9): Commercial pilot on 50 trucks along Guwahati–Shillong–Silchar corridor.",
        "4. IoT Edge Sensing (M10-M12): Solar-powered soil pore-pressure sensors on top 10 landslide choke points on NH-27.",
    ]
    for pp in prod_points:
        p = tf_prod.add_paragraph()
        p.text = pp
        p.font.size = Pt(12)
        p.font.color.rgb = TEXT_SUBTLE
        p.space_after = Pt(6)

    p_close = tf_prod.add_paragraph()
    p_close.text = "\nSIH26002 delivers resilience where India's supply chains need it most."
    p_close.font.size = Pt(13)
    p_close.font.bold = True
    p_close.font.color.rgb = SUCCESS_GREEN

    # Save presentation
    prs.save(str(OUTPUT_PPTX))
    print(f"[SUCCESS] Presentation generated: {OUTPUT_PPTX}")
    print(f"Total Slides: {len(prs.slides)}")


if __name__ == "__main__":
    create_deck()
