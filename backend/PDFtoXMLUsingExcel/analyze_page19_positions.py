#!/usr/bin/env python3
"""
Diagnostic script to analyze page 19 positions and column detection.
This will help us understand why ColID is weaving between 1, 0, and 2.
"""

import xml.etree.ElementTree as ET
from collections import defaultdict

# The XML data from the user's query
page19_xml = """<page number="19" position="absolute" top="0" left="0" height="1161" width="823">
	<fontspec id="16" size="12" family="GMBBNN+TimesNewRomanPS" color="#181818"/>
	<fontspec id="17" size="17" family="GMBCAA+TimesNewRomanPS" color="#181818"/>
	<fontspec id="18" size="15" family="GMBBNN+TimesNewRomanPS" color="#181818"/>
	<fontspec id="19" size="15" family="GMBBML+TimesNewRomanPSMT" color="#181818"/>
<text top="134" left="101" width="331" height="18" font="13"><b>MAGNETIC PROPERTIES OF PROTONS </b></text>
<text top="167" left="101" width="298" height="18" font="13"><b>Spinning Protons Act Like Little Magnets </b></text>
<text top="201" left="128" width="572" height="18" font="11">A moving electric charge, be it positive or negative, produces a magnetic field. The </text>
<text top="221" left="101" width="599" height="18" font="11">faster a charge moves or the larger the charge, the larger the magnetic field it produces. </text>
<text top="241" left="101" width="598" height="18" font="11">Think back to when you were a child and would make a crude electromagnet by wrapping </text>
<text top="260" left="101" width="599" height="18" font="11">wire around a nail and connecting it to a battery. The larger the voltage of the battery, the </text>
<text top="280" left="101" width="313" height="18" font="11">larger the current and the stronger the magnet.  </text>
<text top="314" left="128" width="571" height="18" font="11">Some of the basic properties of a simple proton include mass, a positive electric charge </text>
<text top="333" left="101" width="598" height="18" font="11">and spin. Granted, a proton does not have a very large electric charge, but it does spin very </text>
<text top="353" left="101" width="598" height="18" font="11">fast and, therefore, does produce a very small, yet significant, magnetic field. Water is the </text>
<text top="373" left="101" width="598" height="18" font="11">largest source of hydrogen protons in the body, followed by fat. Normally, the direction that </text>
<text top="393" left="101" width="345" height="18" font="11">these tiny magnets point in is randomly distributed (</text>
<text top="393" left="446" width="71" height="18" font="13"><b>Figure 1A</b></text>
<text top="393" left="517" width="14" height="18" font="11">). </text>
<text top="426" left="128" width="109" height="18" font="13"><b>Key Definition:</b></text>
<text top="426" left="238" width="463" height="18" font="11"> Spinning protons are little magnets which are frequently referred to </text>
<text top="446" left="101" width="75" height="18" font="11">as "spins". </text>
<text top="479" left="128" width="108" height="18" font="13"><b>Key Definition:</b></text>
<text top="479" left="237" width="459" height="18" font="11"> Tesla (T) – A unit of magnetic field strength. 1 T = 10,000 Gauss (an-</text>
<text top="499" left="101" width="515" height="18" font="11">other unit of magnetic field). The earth's magnetic field is roughly 0.5 Gauss. </text>
<text top="532" left="128" width="571" height="18" font="11">Just as a compass aligns with the Earth's magnetic field, a spinning proton placed near </text>
<text top="552" left="101" width="323" height="18" font="11">(or within) a large external magnetic field (called </text>
<text top="552" left="424" width="11" height="18" font="13"><b>B</b></text>
<text top="560" left="435" width="9" height="13" font="16"><b>Ø</b></text>
<text top="552" left="444" width="251" height="18" font="11">) will align with the external field. Un-</text>
<text top="572" left="101" width="598" height="18" font="11">fortunately, it is not quite so simple. At the atomic level, some of the protons align with the </text>
<text top="592" left="101" width="599" height="18" font="11">field and some align against the field, cancelling each other out. A slight excess will align </text>
<text top="611" left="101" width="475" height="18" font="11">with the field so that the net result is an alignment with the external field. </text>
<text top="611" left="577" width="69" height="18" font="13"><b>Figure 1B</b></text>
<text top="611" left="645" width="54" height="18" font="11"> depicts </text>
<text top="631" left="101" width="265" height="18" font="11">nine protons, four of which have aligned </text>
<text top="631" left="366" width="48" height="18" font="14"><i>against</i></text>
<text top="631" left="414" width="4" height="18" font="11"> </text>
<text top="631" left="418" width="11" height="18" font="13"><b>B</b></text>
<text top="639" left="429" width="9" height="13" font="16"><b>Ø</b></text>
<text top="631" left="438" width="145" height="18" font="11"> and five have aligned </text>
<text top="631" left="583" width="28" height="18" font="14"><i>with</i></text>
<text top="631" left="611" width="4" height="18" font="11"> </text>
<text top="631" left="615" width="11" height="18" font="13"><b>B</b></text>
<text top="639" left="625" width="9" height="13" font="16"><b>Ø</b></text>
<text top="631" left="635" width="64" height="18" font="11"> resulting </text>
<text top="651" left="101" width="598" height="18" font="11">in an excess of one proton. (Note that this diagram showing the protons aligning perfectly </text>
<text top="671" left="101" width="103" height="18" font="11">with or against </text>
<text top="671" left="205" width="11" height="18" font="13"><b>B</b></text>
<text top="679" left="216" width="9" height="13" font="16"><b>Ø</b></text>
<text top="671" left="225" width="424" height="18" font="11"> is not completely accurate. This will be addressed further with </text>
<text top="671" left="649" width="51" height="18" font="13"><b>Figure </b></text>
<text top="691" left="101" width="8" height="18" font="13"><b>3</b></text>
<text top="691" left="109" width="14" height="18" font="11">.) </text>
<text top="961" left="101" width="171" height="18" font="13"><b>Some Quantum Physics </b></text>
<text top="995" left="128" width="572" height="18" font="11">A complete explanation of why the protons align both with and against the external </text>
<text top="1015" left="101" width="594" height="18" font="11">magnetic field would require a study of quantum mechanics. Suffice it to say that both align-</text>
<text top="1034" left="101" width="200" height="18" font="11">ments are possible but the one </text>
<text top="1034" left="301" width="29" height="17" font="17"><i><b>with</b></i></text>
<text top="1034" left="331" width="365" height="18" font="11"> the field is at a lower energy state. The protons are con-</text>
<text top="77" left="101" width="8" height="18" font="13"><b>2</b></text>
<text top="77" left="155" width="341" height="18" font="13"><b>Basic MRI Physics: Implications for MRI Safety</b></text>
<text top="729" left="115" width="82" height="17" font="18"><b>Figure 1. (A)</b></text>
<text top="729" left="196" width="53" height="17" font="19"> Protons </text>
<text top="747" left="115" width="131" height="17" font="19">that are randomly ori-</text>
<text top="765" left="115" width="141" height="17" font="19">ented in the absence of </text>
<text top="783" left="115" width="129" height="17" font="19">an external magnetic </text>
<text top="801" left="115" width="35" height="17" font="19">field. </text>
<text top="801" left="150" width="20" height="17" font="18"><b>(B)</b></text>
<text top="801" left="170" width="53" height="17" font="19"> Protons </text>
<text top="819" left="115" width="116" height="17" font="19">aligned either with </text>
<text top="837" left="115" width="118" height="17" font="19">(slight majority) or </text>
<text top="855" left="115" width="149" height="17" font="19">against (slight minority) </text>
<text top="873" left="115" width="129" height="17" font="19">an external magnetic </text>
<text top="891" left="115" width="31" height="17" font="19">field.</text>
<text top="3" left="45" width="347" height="13" font="15">BioRef 2021 V10 001-434_Layout 1  12/5/2021  3:11 PM  Page 2</text>
</page>"""

def analyze_positions():
    """Parse the XML and analyze fragment positions."""
    
    # Parse the XML
    root = ET.fromstring(page19_xml)
    page_width = float(root.get("width"))
    page_height = float(root.get("height"))
    
    print(f"Page dimensions: {page_width} x {page_height}")
    print("=" * 80)
    
    # Extract all text fragments
    fragments = []
    for text_elem in root.findall("text"):
        top = float(text_elem.get("top"))
        left = float(text_elem.get("left"))
        width = float(text_elem.get("width"))
        height = float(text_elem.get("height"))
        text = "".join(text_elem.itertext()).strip()
        
        # Calculate baseline (assuming baseline = top + height)
        baseline = top + height
        
        fragments.append({
            "left": left,
            "top": top,
            "width": width,
            "height": height,
            "baseline": baseline,
            "text": text[:50],  # First 50 chars
        })
    
    print(f"\nTotal fragments: {len(fragments)}")
    print("=" * 80)
    
    # Group by left position
    by_left = defaultdict(list)
    for f in fragments:
        by_left[f["left"]].append(f)
    
    print(f"\nUnique left positions: {len(by_left)}")
    print("=" * 80)
    
    # Show left position distribution
    print("\nLeft Position Distribution:")
    print(f"{'Left':>6} | {'Count':>5} | {'Baselines':>10} | Sample Text")
    print("-" * 80)
    
    for left in sorted(by_left.keys()):
        frags = by_left[left]
        baselines = sorted(set(f["baseline"] for f in frags))
        unique_baselines = len(baselines)
        sample_text = frags[0]["text"][:40]
        print(f"{left:>6.0f} | {len(frags):>5} | {unique_baselines:>10} | {sample_text}")
    
    # Analyze what positions could be mistaken for columns
    print("\n" + "=" * 80)
    print("COLUMN DETECTION SIMULATION")
    print("=" * 80)
    
    # Simulate the clustering algorithm
    xs = sorted(f["left"] for f in fragments)
    column_gap_threshold = page_width * 0.25  # Same as in code
    
    print(f"\nColumn gap threshold: {column_gap_threshold:.1f} pixels")
    print(f"(25% of page width)")
    
    # Group into clusters
    clusters = []
    current_cluster_xs = [xs[0]]
    
    for x in xs[1:]:
        mean_current = sum(current_cluster_xs) / len(current_cluster_xs)
        if abs(x - mean_current) <= column_gap_threshold:
            current_cluster_xs.append(x)
        else:
            clusters.append(current_cluster_xs)
            current_cluster_xs = [x]
    clusters.append(current_cluster_xs)
    
    print(f"\nDetected {len(clusters)} x-position clusters BEFORE vertical extent check:")
    for i, cluster in enumerate(clusters, 1):
        mean_x = sum(cluster) / len(cluster)
        print(f"  Cluster {i}: mean={mean_x:.1f}, count={len(cluster)}, range={min(cluster):.0f}-{max(cluster):.0f}")
    
    # Now check vertical extent for each cluster
    print("\n" + "=" * 80)
    print("VERTICAL EXTENT CHECK (Key to column detection)")
    print("=" * 80)
    
    min_unique_baselines = 12  # UPDATED: Real columns need more lines
    baseline_tolerance = 2.0
    
    for i, cluster in enumerate(clusters, 1):
        # Get all fragments in this cluster
        cluster_frags = [f for f in fragments if f["left"] in cluster]
        
        # Get unique baselines
        baselines = sorted(set(f["baseline"] for f in cluster_frags))
        
        # Count unique baseline groups (with tolerance)
        unique_baseline_groups = []
        current_group_baseline = None
        
        for b in baselines:
            if current_group_baseline is None:
                current_group_baseline = b
                unique_baseline_groups.append(b)
            elif abs(b - current_group_baseline) > baseline_tolerance:
                current_group_baseline = b
                unique_baseline_groups.append(b)
        
        num_unique_lines = len(unique_baseline_groups)
        is_valid = num_unique_lines >= min_unique_baselines
        
        mean_x = sum(cluster) / len(cluster)
        print(f"\nCluster {i} (mean x={mean_x:.1f}):")
        print(f"  - Fragments: {len(cluster_frags)}")
        print(f"  - Unique baselines: {num_unique_lines}")
        print(f"  - Valid column: {'YES ✓' if is_valid else 'NO ✗ (line continuation or caption)'}")
        
        # Show some sample text
        if len(cluster_frags) > 0:
            print(f"  - Sample text: {cluster_frags[0]['text'][:60]}")
    
    # Identify the problem
    print("\n" + "=" * 80)
    print("ANALYSIS SUMMARY")
    print("=" * 80)
    
    print("\nThis page should be SINGLE COLUMN.")
    print("\nLikely issues:")
    print("1. Small inline fragments (symbols, subscripts) at different x positions")
    print("2. These fragments appear on only 1-2 lines (not a full column)")
    print("3. The vertical extent check should filter them out")
    print("4. If still getting wrong ColIDs, check:")
    print("   - Are inline fragments being counted separately?")
    print("   - Is the baseline calculation correct?")
    print("   - Are there other post-processing steps interfering?")
    
    # Check for multi-column indicators
    print("\n" + "=" * 80)
    print("EXPECTED COLUMN ASSIGNMENT")
    print("=" * 80)
    
    # Count fragments in main text area vs other areas
    main_text_left = 101
    main_text_indent = 128
    
    main_text_count = sum(1 for f in fragments if f["left"] in [main_text_left, main_text_indent])
    other_count = len(fragments) - main_text_count
    
    print(f"\nFragments at main text positions (101, 128): {main_text_count}")
    print(f"Fragments at other positions: {other_count}")
    print(f"\nSince main text dominates, all fragments should get:")
    print(f"  - ColID = 1 (single column)")
    print(f"  - Reading Block = 1 (all in same reading order)")

if __name__ == "__main__":
    analyze_positions()
