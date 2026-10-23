import os
import subprocess
from pathlib import Path

# Pure vector SVG for Academic Publication (ACL/EMNLP/NeurIPS style)
SVG_CONTENT = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 600" width="1200" height="600" style="background:#ffffff; font-family:'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, Helvetica, Arial, sans-serif;">
  <defs>
    <!-- Drop Shadow Filters -->
    <filter id="shadow" x="-5%" y="-5%" width="115%" height="115%">
      <feDropShadow dx="1" dy="2" stdDeviation="2.5" flood-color="#0f172a" flood-opacity="0.08"/>
    </filter>
    <filter id="badge-shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-color="#000000" flood-opacity="0.15"/>
    </filter>

    <!-- Arrow Markers -->
    <marker id="arrow-gray" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#475569"/>
    </marker>
    <marker id="arrow-blue" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#2563eb"/>
    </marker>
    <marker id="arrow-green" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#16a34a"/>
    </marker>
    <marker id="arrow-red" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#dc2626"/>
    </marker>
    <marker id="arrow-purple" viewBox="0 0 10 10" refX="7" refY="5" markerWidth="6" markerHeight="6" orient="auto-start-reverse">
      <path d="M 0 1.5 L 8 5 L 0 8.5 z" fill="#9333ea"/>
    </marker>
  </defs>

  <!-- ==================== 1. INPUT SECTION (LEFT) ==================== -->
  
  <!-- Discourse Thread Speech Bubble -->
  <g transform="translate(25, 60)" filter="url(#shadow)">
    <!-- Speech bubble body -->
    <path d="M 0 8 C 0 3.6, 3.6 0, 8 0 L 142 0 C 146.4 0, 150 3.6, 150 8 L 150 82 C 150 86.4, 146.4 90, 142 90 L 35 90 L 18 106 L 22 90 L 8 90 C 3.6 90, 0 86.4, 0 82 Z" fill="#ffffff" stroke="#334155" stroke-width="1.6"/>
    <text x="75" y="22" text-anchor="middle" font-size="11.5" font-weight="700" fill="#0f172a">Discourse Context</text>
    <line x1="15" y1="28" x2="135" y2="28" stroke="#e2e8f0" stroke-width="1"/>
    <text x="18" y="44" font-size="10" font-family="monospace" fill="#2563eb">T: Headline context</text>
    <text x="18" y="60" font-size="10" font-family="monospace" fill="#64748b">P: Parent comment</text>
    <text x="18" y="78" font-size="10.5" font-family="monospace" font-weight="700" fill="#dc2626">C: Target comment</text>
  </g>

  <!-- User / Human Avatar with Laptop -->
  <g transform="translate(65, 175)">
    <!-- Face / Hair -->
    <ellipse cx="25" cy="18" rx="13" ry="13" fill="#fed7aa"/>
    <path d="M 12 18 C 12 8, 38 8, 38 18 C 38 11, 33 5, 25 5 C 17 5, 12 11, 12 18 Z" fill="#78350f"/>
    <circle cx="21" cy="18" r="1.5" fill="#451a03"/>
    <circle cx="29" cy="18" r="1.5" fill="#451a03"/>
    <path d="M 22 23 Q 25 25.5 28 23" fill="none" stroke="#451a03" stroke-width="1.2" stroke-linecap="round"/>
    <!-- Body -->
    <path d="M 10 38 C 10 29, 40 29, 40 38 L 40 44 L 10 44 Z" fill="#3b82f6"/>
    <!-- Laptop -->
    <rect x="5" y="36" width="40" height="18" rx="2" fill="#cbd5e1" stroke="#64748b" stroke-width="1"/>
    <path d="M 1 54 L 49 54 L 45 58 L 5 58 Z" fill="#94a3b8"/>
    <circle cx="25" cy="45" r="3" fill="#ffffff" opacity="0.9"/>
  </g>

  <!-- Database Cylinder: Taxonomy & Argument Patterns -->
  <g transform="translate(25, 275)" filter="url(#shadow)">
    <!-- Base -->
    <ellipse cx="75" cy="85" rx="55" ry="14" fill="#e2e8f0" stroke="#475569" stroke-width="1.5"/>
    <rect x="20" y="22" width="110" height="63" fill="#f8fafc" stroke="#475569" stroke-width="1.5"/>
    <ellipse cx="75" cy="45" rx="55" ry="13" fill="none" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3,3"/>
    <ellipse cx="75" cy="65" rx="55" ry="13" fill="none" stroke="#94a3b8" stroke-width="1" stroke-dasharray="3,3"/>
    <!-- Top -->
    <ellipse cx="75" cy="22" rx="55" ry="14" fill="#ffffff" stroke="#475569" stroke-width="1.5"/>
    
    <!-- Mini Taxonomy Network inside top -->
    <circle cx="58" cy="19" r="3.5" fill="#3b82f6"/>
    <circle cx="92" cy="18" r="3.5" fill="#8b5cf6"/>
    <circle cx="75" cy="26" r="3.5" fill="#ef4444"/>
    <line x1="58" y1="19" x2="92" y2="18" stroke="#cbd5e1" stroke-width="1.2"/>
    <line x1="58" y1="19" x2="75" y2="26" stroke="#cbd5e1" stroke-width="1.2"/>
    <line x1="92" y1="18" x2="75" y2="26" stroke="#cbd5e1" stroke-width="1.2"/>
    
    <text x="75" y="112" text-anchor="middle" font-size="11" font-weight="700" fill="#1e293b">Knowledge Base</text>
    <text x="75" y="126" text-anchor="middle" font-size="9.5" fill="#64748b">CoCoLoFa 8 Classes</text>
    <text x="75" y="139" text-anchor="middle" font-size="9.5" fill="#64748b">&amp; ArgMining Patterns</text>
  </g>

  <!-- Connectors into Prosecutor -->
  <path d="M 175 110 L 195 110 L 195 160 L 210 160" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#arrow-gray)"/>
  <path d="M 135 320 L 195 320 L 195 180 L 210 180" fill="none" stroke="#475569" stroke-width="1.6" marker-end="url(#arrow-gray)"/>

  <!-- ==================== 2. PROSECUTOR AGENT (SOFT BLUE) ==================== -->
  <g transform="translate(218, 95)" filter="url(#shadow)">
    <!-- Box -->
    <rect x="0" y="0" width="185" height="155" rx="8" fill="#eff6ff" stroke="#3b82f6" stroke-width="1.8"/>
    <!-- Banner -->
    <path d="M 0 8 C 0 3.6, 3.6 0, 8 0 L 177 0 C 181.4 0, 185 3.6, 185 8 L 185 32 L 0 32 Z" fill="#dbeafe"/>
    
    <!-- Mini Robot Avatar -->
    <g transform="translate(12, 5)">
      <line x1="11" y1="2" x2="11" y2="6" stroke="#2563eb" stroke-width="1.4"/>
      <circle cx="11" cy="2" r="1.3" fill="#2563eb"/>
      <rect x="2" y="6" width="18" height="14" rx="2.5" fill="#93c5fd" stroke="#1d4ed8" stroke-width="1.1"/>
      <circle cx="6.5" cy="11.5" r="1.6" fill="#1e3a8a"/>
      <circle cx="15.5" cy="11.5" r="1.6" fill="#1e3a8a"/>
      <path d="M 8 16 Q 11 18 14 16" fill="none" stroke="#1e3a8a" stroke-width="1.1" stroke-linecap="round"/>
    </g>

    <text x="42" y="21" font-size="13" font-weight="700" fill="#1e40af">Prosecutor</text>
    
    <!-- Content -->
    <text x="12" y="52" font-size="11" font-weight="600" fill="#0f172a">• Cue Scan &amp; Premise Isol.</text>
    <text x="12" y="70" font-size="10" fill="#475569">  Separates warrant &amp; claim</text>
    <text x="12" y="92" font-size="11" font-weight="600" fill="#0f172a">• Top-2 Fallacy Indictment</text>
    <text x="12" y="110" font-size="10" fill="#475569">  Candidate C₁, Runner-up C₂</text>
    <text x="12" y="132" font-size="11" font-weight="600" fill="#0f172a">• Verbatim Quote Lock (q₁)</text>
  </g>

  <!-- Indictment Data Packet (Dotted Box) -->
  <g transform="translate(223, 275)" filter="url(#shadow)">
    <rect x="0" y="0" width="175" height="52" rx="5" fill="#ffffff" stroke="#2563eb" stroke-width="1.3" stroke-dasharray="3,3"/>
    <text x="10" y="17" font-size="10.5" font-weight="700" fill="#1d4ed8">Indictment Package:</text>
    <text x="10" y="32" font-size="10" font-family="monospace" fill="#0f172a">cand_class: C₁</text>
    <text x="10" y="45" font-size="10" font-family="monospace" fill="#475569">quote: "..." ∈ C</text>
    <circle cx="158" cy="16" r="7.5" fill="#22c55e"/>
    <text x="158" y="20" text-anchor="middle" font-size="9" font-weight="700" fill="#ffffff">✓</text>
  </g>
  <path d="M 310 250 L 310 272" fill="none" stroke="#2563eb" stroke-width="1.5" marker-end="url(#arrow-blue)"/>

  <!-- Arrow Prosecutor -> Defender -->
  <path d="M 403 172 L 445 172" fill="none" stroke="#475569" stroke-width="1.8" marker-end="url(#arrow-gray)"/>

  <!-- ==================== 3. DEFENDER AGENT (SOFT PURPLE) ==================== -->
  <g transform="translate(452, 95)" filter="url(#shadow)">
    <!-- Box -->
    <rect x="0" y="0" width="190" height="155" rx="8" fill="#faf5ff" stroke="#a855f7" stroke-width="1.8"/>
    <!-- Banner -->
    <path d="M 0 8 C 0 3.6, 3.6 0, 8 0 L 182 0 C 186.4 0, 190 3.6, 190 8 L 190 32 L 0 32 Z" fill="#f3e8ff"/>
    
    <!-- Mini Robot Avatar -->
    <g transform="translate(12, 5)">
      <line x1="11" y1="2" x2="11" y2="6" stroke="#9333ea" stroke-width="1.4"/>
      <circle cx="11" cy="2" r="1.3" fill="#9333ea"/>
      <rect x="2" y="6" width="18" height="14" rx="2.5" fill="#d8b4fe" stroke="#7e22ce" stroke-width="1.1"/>
      <circle cx="6.5" cy="11.5" r="1.6" fill="#581c87"/>
      <circle cx="15.5" cy="11.5" r="1.6" fill="#581c87"/>
      <path d="M 8 16 Q 11 18 14 16" fill="none" stroke="#581c87" stroke-width="1.1" stroke-linecap="round"/>
    </g>

    <text x="42" y="21" font-size="13" font-weight="700" fill="#6b21a8">Defender</text>
    
    <!-- Content -->
    <text x="12" y="52" font-size="11" font-weight="600" fill="#0f172a">• Principle of Charity</text>
    <text x="12" y="70" font-size="10" fill="#475569">  Steelman plausible warrants</text>
    <text x="12" y="92" font-size="11" font-weight="600" fill="#0f172a">• Counter-Plea Advocacy</text>
    <text x="12" y="110" font-size="10" fill="#475569">  Alternative C_alt &amp; quote q_alt</text>
    <text x="12" y="132" font-size="11" font-weight="600" fill="#0f172a">• Strategic Concession Gate</text>
  </g>

  <!-- ==================== DEFENDER BRANCH 1: CONCEDE ==================== -->
  <path d="M 547 250 L 547 318" fill="none" stroke="#16a34a" stroke-width="2" marker-end="url(#arrow-green)"/>
  <rect x="555" y="272" width="75" height="20" rx="3" fill="#dcfce7" stroke="#16a34a" stroke-width="0.9"/>
  <text x="592" y="286" text-anchor="middle" font-size="10" font-weight="700" fill="#15803d">Concede</text>

  <!-- Early Exit / Direct Confirmation Box -->
  <g transform="translate(465, 325)" filter="url(#shadow)">
    <rect x="0" y="0" width="165" height="48" rx="6" fill="#f0fdf4" stroke="#22c55e" stroke-width="1.6"/>
    <circle cx="20" cy="24" r="10" fill="#22c55e"/>
    <text x="20" y="28" text-anchor="middle" font-size="12" font-weight="700" fill="#ffffff">✓</text>
    <text x="38" y="20" font-size="11" font-weight="700" fill="#15803d">Direct Exit</text>
    <text x="38" y="36" font-size="10" fill="#166534">Confirm Cand. C₁</text>
  </g>

  <!-- Fast-Path Route to Final Output -->
  <path d="M 630 349 L 980 349 L 980 310" fill="none" stroke="#16a34a" stroke-width="1.8" stroke-dasharray="4,3" marker-end="url(#arrow-green)"/>
  <rect x="735" y="339" width="160" height="19" rx="3" fill="#dcfce7"/>
  <text x="815" y="352" text-anchor="middle" font-size="10" font-weight="600" fill="#15803d">Fast-Path: Uncontested Consensus</text>

  <!-- ==================== DEFENDER BRANCH 2: CONTEST ==================== -->
  <path d="M 642 145 L 685 145 L 685 105 L 705 105" fill="none" stroke="#dc2626" stroke-width="2" marker-end="url(#arrow-red)"/>
  <rect x="640" y="115" width="55" height="20" rx="3" fill="#fee2e2" stroke="#dc2626" stroke-width="0.9"/>
  <text x="667" y="129" text-anchor="middle" font-size="10" font-weight="700" fill="#b91c1c">Contest</text>

  <!-- Defense Plea Dotted Box -->
  <g transform="translate(525, 16)" filter="url(#shadow)">
    <rect x="0" y="0" width="170" height="52" rx="5" fill="#ffffff" stroke="#dc2626" stroke-width="1.3" stroke-dasharray="3,3"/>
    <text x="10" y="16" font-size="10.5" font-weight="700" fill="#b91c1c">Contested Defense Plea:</text>
    <text x="10" y="31" font-size="10" font-family="monospace" fill="#0f172a">alt_class: C_alt (≠ C₁)</text>
    <text x="10" y="44" font-size="10" font-family="monospace" fill="#475569">counter_quote: "..."</text>
    <circle cx="153" cy="16" r="7.5" fill="#ef4444"/>
    <text x="153" y="20" text-anchor="middle" font-size="9" font-weight="700" fill="#ffffff">⚔</text>
  </g>
  <path d="M 547 95 L 547 72" fill="none" stroke="#dc2626" stroke-width="1.4" marker-end="url(#arrow-red)"/>
  <path d="M 695 42 L 712 42" fill="none" stroke="#dc2626" stroke-width="1.6" marker-end="url(#arrow-red)"/>

  <!-- ==================== 4. DIALECTICAL ARBITER (SOFT RED) ==================== -->
  <g transform="translate(712, 18)" filter="url(#shadow)">
    <!-- Box -->
    <rect x="0" y="0" width="230" height="195" rx="8" fill="#fff5f5" stroke="#ef4444" stroke-width="1.8"/>
    <!-- Banner -->
    <path d="M 0 8 C 0 3.6, 3.6 0, 8 0 L 222 0 C 226.4 0, 230 3.6, 230 8 L 230 32 L 0 32 Z" fill="#fee2e2"/>
    
    <!-- Mini Robot Avatar (Judge) -->
    <g transform="translate(12, 5)">
      <line x1="11" y1="2" x2="11" y2="6" stroke="#b91c1c" stroke-width="1.4"/>
      <circle cx="11" cy="2" r="1.3" fill="#b91c1c"/>
      <rect x="2" y="6" width="18" height="14" rx="2.5" fill="#fca5a5" stroke="#b91c1c" stroke-width="1.1"/>
      <circle cx="6.5" cy="11.5" r="1.6" fill="#7f1d1d"/>
      <circle cx="15.5" cy="11.5" r="1.6" fill="#7f1d1d"/>
      <line x1="8" y1="16" x2="14" y2="16" stroke="#7f1d1d" stroke-width="1.3"/>
    </g>

    <text x="42" y="21" font-size="13" font-weight="700" fill="#991b1b">Dialectical Arbiter</text>
    
    <!-- Dual-run permutation subpanel -->
    <text x="12" y="50" font-size="11" font-weight="700" fill="#0f172a">• Order-Permuted Adjudication</text>
    <rect x="12" y="58" width="206" height="46" rx="4" fill="#ffffff" stroke="#f87171" stroke-width="1"/>
    <text x="18" y="74" font-size="9.5" font-family="monospace" fill="#0f172a"><tspan font-weight="700" fill="#2563eb">Run A:</tspan> Opt1: C₁  vs  Opt2: C_alt</text>
    <text x="18" y="92" font-size="9.5" font-family="monospace" fill="#0f172a"><tspan font-weight="700" fill="#7c3aed">Run B:</tspan> Opt1: C_alt vs Opt2: C₁</text>

    <!-- Burden of Proof subpanel -->
    <text x="12" y="122" font-size="11" font-weight="700" fill="#0f172a">• Unanimous Burden of Proof</text>
    <rect x="12" y="130" width="206" height="52" rx="4" fill="#fef2f2" stroke="#fca5a5" stroke-width="1"/>
    <text x="18" y="146" font-size="9.5" fill="#7f1d1d">If Run A = C_alt <tspan font-weight="700">AND</tspan> Run B = C_alt:</text>
    <text x="26" y="160" font-size="9.5" font-weight="700" fill="#15803d">⟹ Flip to Defense (C_alt)</text>
    <text x="18" y="174" font-size="9.5" fill="#64748b">Else: <tspan font-weight="700" fill="#1e40af">Uphold Prosecutor (C₁)</tspan></text>
  </g>

  <!-- ==================== 5. VERIFIER & SCHEMA GUARD (SOFT YELLOW) ==================== -->
  <g transform="translate(712, 230)" filter="url(#shadow)">
    <!-- Box -->
    <rect x="0" y="0" width="230" height="98" rx="8" fill="#fffbeb" stroke="#f59e0b" stroke-width="1.8"/>
    <!-- Banner -->
    <path d="M 0 8 C 0 3.6, 3.6 0, 8 0 L 222 0 C 226.4 0, 230 3.6, 230 8 L 230 30 L 0 30 Z" fill="#fef3c7"/>
    
    <!-- Mini Robot / Shield Avatar -->
    <g transform="translate(12, 4)">
      <rect x="2" y="5" width="18" height="14" rx="2.5" fill="#fde68a" stroke="#d97706" stroke-width="1.1"/>
      <path d="M 11 7 L 16 9.5 L 16 14 C 16 16.5 11 18.5 11 18.5 C 11 18.5 6 16.5 6 14 L 6 9.5 Z" fill="#f59e0b"/>
      <path d="M 9 12.5 L 11 14.5 L 14 10.5" fill="none" stroke="#ffffff" stroke-width="1.1" stroke-linecap="round"/>
    </g>

    <text x="42" y="20" font-size="12.5" font-weight="700" fill="#92400e">Verifier &amp; Guard</text>
    
    <!-- Content -->
    <text x="12" y="47" font-size="10" fill="#78350f">• Verbatim Substring Match Check</text>
    <text x="12" y="64" font-size="10" fill="#78350f">• Closed-Set Label Space Validation</text>
    <text x="12" y="81" font-size="10" fill="#78350f">• Format &amp; Score Audit Serialization</text>
  </g>

  <!-- Arrow Arbiter -> Verifier -->
  <path d="M 827 213 L 827 226" fill="none" stroke="#475569" stroke-width="1.8" marker-end="url(#arrow-gray)"/>

  <!-- Feedback Re-try Loop (from Verifier back to Defender/Prosecutor) -->
  <path d="M 712 280 L 655 280 L 655 220 L 642 220" fill="none" stroke="#dc2626" stroke-width="1.5" stroke-dasharray="3,3" marker-end="url(#arrow-red)"/>
  <rect x="645" y="235" width="65" height="18" rx="3" fill="#fee2e2"/>
  <text x="677" y="247" text-anchor="middle" font-size="9" font-weight="700" fill="#dc2626">Re-prompt</text>

  <!-- ==================== 6. FINAL OUTPUT SECTION (SOFT GREEN) ==================== -->
  <!-- Arrow from Verifier to Final Output -->
  <path d="M 942 280 L 972 280" fill="none" stroke="#16a34a" stroke-width="2.2" marker-end="url(#arrow-green)"/>
  <circle cx="957" cy="280" r="9" fill="#22c55e" filter="url(#badge-shadow)"/>
  <text x="957" y="284" text-anchor="middle" font-size="10" font-weight="700" fill="#ffffff">✓</text>
  <text x="957" y="300" text-anchor="middle" font-size="9" font-weight="700" fill="#15803d">Valid</text>

  <!-- Final Verdict Card -->
  <g transform="translate(980, 115)" filter="url(#shadow)">
    <!-- Box -->
    <rect x="0" y="0" width="195" height="185" rx="8" fill="#f0fdf4" stroke="#16a34a" stroke-width="2"/>
    <path d="M 0 8 C 0 3.6, 3.6 0, 8 0 L 187 0 C 191.4 0, 195 3.6, 195 8 L 195 34 L 0 34 Z" fill="#dcfce7"/>
    
    <!-- Star Icon -->
    <circle cx="20" cy="17" r="9" fill="#16a34a"/>
    <text x="20" y="21.5" text-anchor="middle" font-size="11" font-weight="700" fill="#ffffff">★</text>
    
    <text x="38" y="22" font-size="13" font-weight="700" fill="#14532d">Final Verdict</text>
    
    <!-- Card Inner -->
    <g transform="translate(10, 44)">
      <rect x="0" y="0" width="175" height="128" rx="4" fill="#ffffff" stroke="#86efac" stroke-width="1.2" stroke-dasharray="3,3"/>
      
      <text x="10" y="18" font-size="9" font-weight="700" fill="#64748b">PREDICTED CLASS:</text>
      <text x="10" y="36" font-size="11.5" font-weight="800" font-family="monospace" fill="#047857">ŷ ∈ Y_8 Fallacy</text>
      
      <line x1="10" y1="46" x2="165" y2="46" stroke="#f1f5f9" stroke-width="1"/>
      
      <text x="10" y="60" font-size="9" font-weight="700" fill="#64748b">CONFIDENCE SCORE:</text>
      <text x="10" y="76" font-size="11" font-weight="700" fill="#0284c7">0.00 – 1.00 Score</text>
      
      <line x1="10" y1="86" x2="165" y2="86" stroke="#f1f5f9" stroke-width="1"/>
      
      <text x="10" y="100" font-size="9" font-weight="700" fill="#64748b">GROUNDED EVIDENCE:</text>
      <text x="10" y="116" font-size="9.5" font-family="monospace" fill="#334155">Verbatim Quote Span</text>
    </g>
  </g>

  <!-- ==================== 7. BOTTOM CAPTION (ACADEMIC LATEX STYLE) ==================== -->
  <g transform="translate(30, 485)">
    <text x="0" y="16" font-family="'Times New Roman', Times, 'Computer Modern', Georgia, serif" font-size="13.5" font-weight="700" fill="#0f172a">Figure 1: Overall Architecture of the Adversarial Dialectical Debate Framework.</text>
    <text x="0" y="36" font-family="'Times New Roman', Times, 'Computer Modern', Georgia, serif" font-size="12" fill="#1e293b">
      The <tspan font-weight="700" fill="#1e40af">Prosecutor</tspan> scans rhetorical cues and outputs a defect indictment locked to verbatim text evidence. The <tspan font-weight="700" fill="#6b21a8">Defender</tspan> evaluates contextual warrants under the
    </text>
    <text x="0" y="55" font-family="'Times New Roman', Times, 'Computer Modern', Georgia, serif" font-size="12" fill="#1e293b">
      Principle of Charity, either <tspan font-weight="700" fill="#15803d">conceding</tspan> (early exit on uncontested agreement) or <tspan font-weight="700" fill="#b91c1c">contesting</tspan> with a steelmanned alternative class. Contested cases trigger
    </text>
    <text x="0" y="74" font-family="'Times New Roman', Times, 'Computer Modern', Georgia, serif" font-size="12" fill="#1e293b">
      dual-run order-permuted pairwise adjudication by the <tspan font-weight="700" fill="#991b1b">Dialectical Arbiter</tspan> under an asymmetric unanimous burden of proof, verified by programmatic schema guards.
    </text>
  </g>
</svg>'''

# Preview HTML for interactive viewing and SVG download
HTML_PREVIEW = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Adversarial Dialectical Debate Architecture</title>
  <style>
    body {{
      margin: 0;
      padding: 30px;
      background: #f1f5f9;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
    }}
    .container {{
      background: #ffffff;
      padding: 24px;
      border-radius: 12px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.1), 0 8px 10px -6px rgba(0, 0, 0, 0.1);
      max-width: 1240px;
    }}
    h1 {{
      font-size: 20px;
      color: #0f172a;
      margin-top: 0;
      margin-bottom: 16px;
      text-align: center;
    }}
    svg {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .actions {{
      margin-top: 20px;
      display: flex;
      gap: 12px;
      justify-content: center;
    }}
    button {{
      background: #2563eb;
      color: white;
      border: none;
      padding: 10px 20px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      font-size: 14px;
      transition: background 0.2s;
    }}
    button:hover {{
      background: #1d4ed8;
    }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Adversarial Dialectical Debate Architecture for Logical Fallacy Classification</h1>
    {SVG_CONTENT}
    <div class="actions">
      <button onclick="downloadSVG()">Download Vector SVG (Overleaf)</button>
    </div>
  </div>

  <script>
    function downloadSVG() {{
      const svg = document.querySelector('svg').outerHTML;
      const blob = new Blob([svg], {{type: 'image/svg+xml'}});
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'adversarial_debate_architecture.svg';
      a.click();
      URL.revokeObjectURL(url);
    }}
  </script>
</body>
</html>'''

# Clean render HTML with 0 padding for exact headless Chrome screenshotting
HTML_RENDER = f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <style>
    * {{ box-sizing: border-box; }}
    html, body {{
      margin: 0;
      padding: 0;
      background: #ffffff;
      width: 1200px;
      height: 600px;
      overflow: hidden;
    }}
    svg {{
      width: 1200px;
      height: 600px;
      display: block;
    }}
  </style>
</head>
<body>
  {SVG_CONTENT}
</body>
</html>'''

def main():
    figures_dir = Path('figures')
    figures_dir.mkdir(parents=True, exist_ok=True)
    
    # 1. Save Vector SVG
    svg_path = figures_dir / 'adversarial_debate_architecture.svg'
    svg_path.write_text(SVG_CONTENT, encoding='utf-8')
    print(f"Generated SVG: {svg_path.resolve()}")
    
    # 2. Save Interactive Preview HTML
    html_preview_path = figures_dir / 'preview_architecture.html'
    html_preview_path.write_text(HTML_PREVIEW, encoding='utf-8')
    print(f"Generated HTML preview: {html_preview_path.resolve()}")

    # 3. Save Clean Render HTML
    html_render_path = figures_dir / 'render_clean.html'
    html_render_path.write_text(HTML_RENDER, encoding='utf-8')

    # 4. Render 300 DPI (2x Device Scale Factor) PNG via headless Chrome
    chrome_path = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
    png_path = figures_dir / 'adversarial_debate_architecture.png'
    if os.path.exists(chrome_path):
        cmd = [
            chrome_path,
            '--headless=new',
            '--disable-gpu',
            '--force-device-scale-factor=2',
            '--window-size=1200,600',
            f'--screenshot={png_path.resolve()}',
            f'file:///{html_render_path.resolve()}'
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if png_path.exists() and png_path.stat().st_size > 0:
            print(f"Successfully rendered High-Res PNG (2x): {png_path.resolve()} ({png_path.stat().st_size} bytes)")
        else:
            print("Chrome screenshot failed:", res.stderr)
    else:
        print("Chrome not found for headless screenshot; SVG is ready.")

if __name__ == '__main__':
    main()
