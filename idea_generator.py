import os
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Preformatted
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def create_blueprint_pdf():
    # Setup document and styles
    doc = SimpleDocTemplate("NexusSim_Architectural_Blueprint.pdf", pagesize=letter)
    styles = getSampleStyleSheet()
    
    # Custom text styles
    title_style = ParagraphStyle('TitleStyle', parent=styles['Heading1'], alignment=1, spaceAfter=14)
    h2 = styles['Heading2']
    h3 = styles['Heading3']
    body = styles['BodyText']
    
    # Preformatted style for ASCII diagrams (Courier font preserves spacing perfectly)
    ascii_style = ParagraphStyle(
        'ASCII',
        fontName='Courier',
        fontSize=8,
        leading=10,
        spaceBefore=12,
        spaceAfter=12,
        textColor='#1a1a1a'
    )

    story = []

    # --- Title Header ---
    story.append(Paragraph("TECHNICAL SPECIFICATION & SYSTEM ARCHITECTURAL BLUEPRINT", title_style))
    story.append(Paragraph("<b>Project Title:</b> NexusSim: A High-Performance Multi-Agent Urban Mobility Engine", body))
    story.append(Paragraph("<b>Document Class:</b> Production Whitepaper / Reference Manual", body))
    story.append(Spacer(1, 20))

    # --- Section 1: Executive Summary ---
    story.append(Paragraph("1. The Executive Summary (The Analogy)", h2))
    story.append(Paragraph("To understand NexusSim, imagine a highly detailed city-building simulator like SimCity, but built using the actual, messy streets of a real metropolitan area (like Ahmedabad or Surat) instead of a fictional grid.", body))
    story.append(Spacer(1, 10))
    story.append(Paragraph("Instead of a human player manually switching traffic signals, an advanced AI handles the controls. This AI earns points not just by making cars move faster on average, but by ensuring that working-class or peripheral neighborhoods receive the exact same traffic efficiency upgrades as wealthy commercial corridors.", body))
    
    # ASCII DIAGRAM 1
    diagram_1 = '''
+------------------------------------------------------------------------+
|                               NEXUSSIM                                 |
+------------------------------------------------------------------------+
|                                                                        |
|  [ The Physical Engine ]   --->   [ The Distributed Brain ]            |
|  Written in native C++            Multi-Agent Python API               |
|  Handles 50,000+ moving           Learns intersection signal policies  |
|  agents at 60 FPS cleanly.        via continuous trial-and-error.      |
|                                                                        |
|                     \\                       /                          |
|                      \\                     /                           |
|                       v                   v                            |
|                            [ Ground Truth Map ]                        |
|                            OpenStreetMap Spatial Data                  |
|                            Ingests dirty, real-world geometries        |
|                            and processes them cleanly.                 |
+------------------------------------------------------------------------+
'''
    # Escape XML characters for ReportLab
    d1_safe = diagram_1.strip().replace('<', '&lt;').replace('>', '&gt;')
    story.append(Preformatted(d1_safe, ascii_style))
    story.append(Spacer(1, 10))

    # --- Section 2: Glossary ---
    story.append(Paragraph("2. Technical Glossary", h2))
    glossary = [
        "<b>Mathematical Graph:</b> A structural model where intersections are vertices and directed edges represent the connecting roadways.",
        "<b>Agent-Based Simulation (ABS):</b> A computing paradigm where every vehicle is an independent software object with distinct velocity and routing.",
        "<b>Multi-Agent Reinforcement Learning (MARL):</b> A subfield where multiple independent AI models simultaneously learn to optimize a localized reward function.",
        "<b>Inter-Process Communication (IPC):</b> High-speed protocols transferring binary data payloads directly between running processes.",
        "<b>Spatial Partitioning (Quadtree):</b> A tree data structure used to recursively divide 2D coordinate space for high-speed collision checking."
    ]
    for item in glossary:
        story.append(Paragraph(f"• {item}", body))
    story.append(Spacer(1, 20))

    # --- Section 3: Full-Stack Architecture ---
    story.append(Paragraph("3. Full-Stack System Architecture Diagram", h2))
    
    diagram_2 = '''
       [ OPENSTREETMAP DATA (.osm) ] 
                     |
                     v
       [ Python ETL Pipeline (OSMnx) ]  <--- Snaps nodes, cleans topology
                     |
                     v
         [ Clean Binary Graph File ]
                     |
                     v
+---------------------------------------------------------------------+
|                      NATIVE C++ RUNTIME ENGINE                      |
|                                                                     |
|   +-----------------------+         +----------------------------+  |
|   |   Main Thread Loop    | <-----> | Spatial Partitioning Module|  |
|   +-----------------------+         +----------------------------+  |
|               | (Async Reads)                                       |
|               v                                                     |
|   +-----------------------+                                         |
|   | Local Policy Cache    | <---------+ (Updates weights async)     |
|   +-----------------------+                                         |
+---------------------------------------|-----------------------------+
                                        |
       +--------------------------------+-----------------------+
       | IPC Interface: gRPC Streaming over Unix Domain Sockets |
       +--------------------------------+-----------------------+
                                        |
                                        v
+---------------------------------------------------------------------+
|                      DECENTRALIZED PYTHON AI API                    |
|                                                                     |
|    [ Async Batching ] ---> [ MAPPO Neural Nets ] ---> [ ONNX ]      |
+---------------------------------------------------------------------+
                                        |
                                        v (Delta-Updates Only via Protobuf)
                         [ REACT WEB VISUALIZATION ]
'''
    d2_safe = diagram_2.strip().replace('<', '&lt;').replace('>', '&gt;')
    story.append(Preformatted(d2_safe, ascii_style))
    story.append(Spacer(1, 20))

    # --- Section 4: Deep Dive ---
    story.append(Paragraph("4. Deep-Dive Solution Blueprint", h2))
    
    # SDE
    story.append(Paragraph("Track 1: Software Development Engineering (SDE)", h3))
    story.append(Paragraph("<b>A. Resolving the Synchronous Loop Bottleneck:</b> The system decouples the loop. The C++ thread reads from a Local Policy Cache in native RAM. An independent worker thread pushes states via gRPC to Python, updating the Cache asynchronously.", body))
    story.append(Paragraph("<b>B. Resolving Raw OpenStreetMap Structural Failures:</b> An offline Python ETL Pipeline parses data before runtime using OSMnx and Shapely, snapping overlapping nodes and pruning disconnected edges.", body))
    story.append(Paragraph("<b>C. Resolving the Network Bandwidth Choke Point:</b> The serialization protocol utilizes Google Protocol Buffers (Protobuf). The engine transmits only spatial delta-updates (changes) rather than full state dumps.", body))
    story.append(Spacer(1, 10))

    # ML
    story.append(Paragraph("Track 2: Machine Learning Engineering (ML)", h3))
    story.append(Paragraph("<b>A. Resolving the State-Action Space Explosion:</b> Transitions to Decentralized Multi-Agent Reinforcement Learning using MAPPO. Each intersection is an autonomous agent.", body))
    story.append(Paragraph("<b>B. Resolving the Python Concurrency Bottleneck:</b> Incorporates an Asynchronous Batching Middleware Layer, compiling finalized networks into an ONNX graph file called directly within C++ native memory.", body))
    story.append(Paragraph("<b>C. Resolving the Credit Assignment Dilemma:</b> Integrates a Value-Decomposition Network (VDN) architecture. The reward function balances local efficiency with downstream network stress to prevent bouncing jams.", body))
    story.append(Spacer(1, 10))

    # Policy
    story.append(Paragraph("Track 3: Civil Services & Public Policy", h3))
    story.append(Paragraph("<b>A. Resolving the Heterogeneous Traffic Gap:</b> Replaces rigid grid lanes with a Continuous Sub-Lane Social Force Framework. Agents calculate lateral repulsion to allow smaller vehicles to squeeze through gaps.", body))
    story.append(Paragraph("<b>B. Resolving the Demographics Blind Spot:</b> The pipeline intersects spatial nodes with ward-level census datasets and registries to track wait times across socioeconomic zones.", body))
    story.append(Paragraph("<b>C. Resolving the Real-World Data Deficit:</b> Traffic generation is seeded from Municipal Origin-Destination (O-D) Matrices and regional RTO statistics rather than randomized flows.", body))
    story.append(Spacer(1, 20))

    # --- Section 5: Math & Policy Metric ---
    story.append(Paragraph("5. Algorithmic Equity & Core Policy Metric", h2))
    story.append(Paragraph("To ensure structural fairness rather than raw average efficiency, the fitness score is mathematically bound to spatial equity. The global optimization target is defined as:", body))
    story.append(Spacer(1, 10))
    
    math_eq = "Fitness = - [ (Average_Network_Delay) + (Alpha * Gini_Coefficient_of_Wait_Times) ]"
    story.append(Preformatted(math_eq, ascii_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("By penalizing high spatial variance in wait times (via the Gini Coefficient), this prevents the machine learning model from sacrificing peripheral or lower-income neighborhoods to artificially maximize traffic speeds in central commercial hubs.", body))

    # Generate Document
    doc.build(story)
    print("PDF successfully generated: NexusSim_Architectural_Blueprint.pdf")

if __name__ == '__main__':
    create_blueprint_pdf()