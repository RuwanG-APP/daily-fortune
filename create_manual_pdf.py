"""Generate a beautiful, printable A4 PDF for DAILY_FORTUNE_THEORY_MANUAL."""

import os
import subprocess
import tempfile
from pathlib import Path
from fortune_engine.pdf_export import find_browser_binary

HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="si">
<head>
<meta charset="utf-8">
<title>Daily Fortune — පූර්ණ ජ්‍යෝතිෂ න්‍යාය සහ ගණනය කිරීමේ අත්පොත</title>
<style>
  @page {
    size: A4 portrait;
    margin: 12mm 12mm 12mm 12mm;
  }

  * {
    box-sizing: border-box;
  }

  body {
    font-family: 'Iskoola Pota', 'Nirmala UI', 'Noto Sans Sinhala', 'Segoe UI', sans-serif;
    color: #1e293b;
    line-height: 1.48;
    font-size: 9.5pt;
    margin: 0;
    padding: 0;
    background: #ffffff;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }

  /* Running Header & Footer for Print */
  .doc-header {
    border-bottom: 1px solid #cbd5e1;
    padding-bottom: 4px;
    margin-bottom: 12px;
    display: flex;
    justify-content: space-between;
    font-size: 8pt;
    color: #64748b;
    font-weight: 600;
  }

  /* Cover Header */
  .cover-card {
    background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 60%, #311042 100%);
    color: #ffffff;
    padding: 18px 22px;
    border-radius: 10px;
    margin-bottom: 14px;
    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    border: 1px solid #4338ca;
  }

  .cover-top {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .cover-brand {
    display: inline-block;
    background: rgba(255, 255, 255, 0.15);
    color: #fde047;
    font-size: 8.5pt;
    font-weight: 700;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 999px;
    border: 1px solid rgba(253, 224, 71, 0.3);
  }

  .cover-badge {
    font-size: 8pt;
    color: #cbd5e1;
  }

  h1.main-title {
    font-size: 17pt;
    font-weight: 800;
    line-height: 1.25;
    margin: 0 0 4px 0;
    color: #ffffff;
  }

  .sub-title {
    font-size: 9.5pt;
    color: #cbd5e1;
    margin: 0 0 10px 0;
    font-weight: 500;
    font-style: italic;
  }

  .objective-box {
    background: rgba(255, 255, 255, 0.1);
    border-left: 3.5px solid #facc15;
    padding: 8px 12px;
    border-radius: 0 6px 6px 0;
    font-size: 9pt;
    color: #f1f5f9;
    line-height: 1.5;
  }

  .objective-box strong {
    color: #fde047;
  }

  /* Section Headings */
  h2 {
    color: #0f172a;
    font-size: 12pt;
    font-weight: 800;
    margin: 14px 0 5px 0;
    padding-bottom: 4px;
    border-bottom: 1.5px solid #e2e8f0;
    break-after: avoid;
    display: flex;
    align-items: center;
  }

  h2::before {
    content: "";
    display: inline-block;
    width: 5px;
    height: 15px;
    background: #4f46e5;
    border-radius: 2px;
    margin-right: 6px;
  }

  h3 {
    color: #334155;
    font-size: 10.5pt;
    font-weight: 700;
    margin: 10px 0 4px 0;
    break-after: avoid;
  }

  p {
    margin: 0 0 8px 0;
    text-align: justify;
  }

  /* Pillar Box Diagram */
  .diagram-container {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 8px;
    padding: 12px 14px;
    margin: 8px 0 10px 0;
    break-inside: avoid;
  }

  .diagram-title {
    text-align: center;
    font-weight: 700;
    font-size: 9pt;
    color: #475569;
    margin-bottom: 8px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .pillars-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 8px;
  }

  .pillar-card {
    background: #ffffff;
    border: 1px solid #cbd5e1;
    border-top: 3px solid #4f46e5;
    border-radius: 6px;
    padding: 8px 6px;
    text-align: center;
    box-shadow: 0 1px 2px rgba(0,0,0,0.04);
  }

  .pillar-num {
    font-size: 7.5pt;
    font-weight: 800;
    color: #4f46e5;
    text-transform: uppercase;
  }

  .pillar-name {
    font-size: 8.5pt;
    font-weight: 700;
    color: #0f172a;
    margin: 2px 0 3px 0;
  }

  .pillar-desc {
    font-size: 7.5pt;
    color: #64748b;
    line-height: 1.3;
  }

  .synthesis-bar {
    background: linear-gradient(90deg, #4f46e5, #7c3aed);
    color: #ffffff;
    text-align: center;
    padding: 6px 10px;
    border-radius: 5px;
    font-weight: 700;
    font-size: 8.5pt;
  }

  /* Tables */
  table {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0 12px 0;
    font-size: 9pt;
    break-inside: avoid;
    box-shadow: 0 1px 2px rgba(0,0,0,0.03);
    border-radius: 5px;
    overflow: hidden;
  }

  thead {
    background: #0f172a;
    color: #ffffff;
  }

  th {
    padding: 6px 8px;
    text-align: left;
    font-weight: 700;
    font-size: 8.5pt;
    border-bottom: 1.5px solid #334155;
  }

  td {
    padding: 5px 8px;
    border-bottom: 1px solid #e2e8f0;
    vertical-align: middle;
  }

  tr:nth-child(even) td {
    background: #f8fafc;
  }

  tr:last-child td {
    border-bottom: 1px solid #cbd5e1;
  }

  /* Formula Box */
  .formula-box {
    background: #f1f5f9;
    border: 1px dashed #64748b;
    border-left: 3.5px solid #4f46e5;
    padding: 8px 12px;
    border-radius: 5px;
    margin: 8px 0 10px 0;
    font-size: 9pt;
    font-weight: 600;
    color: #0f172a;
    break-inside: avoid;
  }

  .formula-title {
    font-size: 8pt;
    color: #4f46e5;
    text-transform: uppercase;
    font-weight: 800;
    margin-bottom: 2px;
  }

  .formula-text {
    font-family: 'Consolas', 'Courier New', monospace, 'Nirmala UI';
    font-size: 9pt;
    color: #1e1b4b;
    background: #ffffff;
    padding: 4px 8px;
    border-radius: 4px;
    border: 1px solid #cbd5e1;
    display: inline-block;
    margin-top: 3px;
  }

  /* Badges */
  .badge {
    display: inline-block;
    padding: 2px 7px;
    border-radius: 999px;
    font-weight: 700;
    font-size: 8pt;
    white-space: nowrap;
    text-align: center;
  }

  .badge-supreme { background: linear-gradient(135deg, #065f46, #047857); color: #fef08a; border: 1px solid #d97706; }
  .badge-vgood   { background: #059669; color: #ffffff; }
  .badge-good    { background: #dcfce7; color: #166534; border: 1px solid #86efac; }
  .badge-neutral { background: #fef3c7; color: #92400e; border: 1px solid #fcd34d; }
  .badge-bad     { background: #ffedd5; color: #c2410c; border: 1px solid #fdba74; }
  .badge-vbad    { background: #dc2626; color: #ffffff; }

  /* Callouts */
  .callout-note {
    background: #eff6ff;
    border-left: 3.5px solid #2563eb;
    padding: 8px 12px;
    border-radius: 0 5px 5px 0;
    margin: 8px 0 10px 0;
    font-size: 9pt;
    color: #1e3a8a;
    break-inside: avoid;
  }

  .callout-alert {
    background: #fef2f2;
    border-left: 3.5px solid #ef4444;
    padding: 8px 12px;
    border-radius: 0 5px 5px 0;
    margin: 8px 0 10px 0;
    font-size: 9pt;
    color: #991b1b;
    break-inside: avoid;
  }

  .callout-success {
    background: #f0fdf4;
    border-left: 3.5px solid #16a34a;
    padding: 8px 12px;
    border-radius: 0 5px 5px 0;
    margin: 8px 0 10px 0;
    font-size: 9pt;
    color: #14532d;
    break-inside: avoid;
  }

  /* Q&A Cards */
  .qa-card {
    background: #f8fafc;
    border: 1px solid #e2e8f0;
    border-radius: 6px;
    padding: 9px 12px;
    margin-bottom: 8px;
    break-inside: avoid;
  }

  .qa-q {
    font-weight: 700;
    color: #0f172a;
    font-size: 9.5pt;
    margin-bottom: 4px;
    display: flex;
    align-items: baseline;
  }

  .qa-q span {
    background: #4f46e5;
    color: white;
    font-size: 7pt;
    font-weight: 800;
    padding: 1px 5px;
    border-radius: 3px;
    margin-right: 5px;
  }

  .qa-a {
    color: #334155;
    font-size: 9pt;
    line-height: 1.5;
    border-left: 2px solid #cbd5e1;
    padding-left: 8px;
    margin-left: 3px;
  }

  /* List Styling */
  ol, ul {
    margin: 0 0 8px 0;
    padding-left: 18px;
  }

  li {
    margin-bottom: 3px;
    line-height: 1.5;
  }
</style>
</head>
<body>

  <!-- COVER HEADER -->
  <div class="cover-card">
    <div class="cover-top">
      <span class="cover-brand">Daily Fortune • Complete Astrological Guide</span>
      <span class="cover-badge">ලංකා පංචාංග ලිත & පංච පක්ෂි ශාස්ත්‍රය</span>
    </div>
    <h1 class="main-title">Daily Fortune — පූර්ණ ජ්‍යෝතිෂ න්‍යාය සහ ගණනය කිරීමේ අත්පොත</h1>
    <div class="sub-title">Astrological Theory & Manual Calculation Guide (Pancha Pakshi, Nava Tara Chakra & Kala Hora)</div>
    <div class="objective-box">
      <strong>පරමාර්ථය:</strong> කෙනෙකුගේ උපන් දිනය, වේලාව සහ ස්ථානය ලබා දුන් විට, <strong>Daily Fortune</strong> මෘදුකාංගය මගින් සෑම මිනිත්තුවක් පාසාම සුභ/අසුභ තත්වය ගණනය කර සරල කාලසටහනක් (6-Tier Schedule) ලබාදෙන ආකාරය, ලංකා පංචාංග ග්‍රහස්පුට ලිත සහ පුරාණ ජ්‍යෝතිෂ මූලධර්ම ඇසුරෙන් අතින් (Manually) ගණනය කරන අයුරු සම්පූර්ණයෙන්ම තේරුම් ගැනීම.
    </div>
  </div>

  <!-- 1. හැඳින්වීම -->
  <h2>1. හැඳින්වීම: Daily Fortune ක්‍රමයේ මූලික රහස</h2>
  <p>
    සාමාන්‍ය පත්තරයක හෝ රූපවාහිනියේ කියවෙන "ලග්න පලාපල" ලෝකයේ සිටින මිලියන ගණනක් වන එකම ලග්නයේ සියලු දෙනාටම එක හා සමානව කියවෙන පොදු අනාවැකියකි. නමුත් <strong>Daily Fortune</strong> යනු එවැනි සාමාන්‍ය දෙයක් නොවේ.
  </p>
  <p>
    මෙය පුද්ගලයෙකුගේ <strong>ජීව-රිද්මය (Personal Astrological Bio-Rhythm)</strong> පදනම් කරගත් පුද්ගලාරෝපිත කාල සටහනකි. පුරාණ ඉසිවර මතය අනුව මිනිසාගේ ශරීරයේ සහ මනසේ ශක්ති මට්ටම දවසේ විවිධ හෝරාවන් වලදී ඉහළ යාම සහ පහළ යාම සිදුවේ. අතීතයේ සිට මෙරට සිටි ප්‍රවීණ ජ්‍යෝතිෂවේදීන් තම සමීපතමයින්ට පමණක් සාදා දුන් මෙම රහස් ක්‍රමවේදය ගොඩනැගී ඇත්තේ ප්‍රධාන කුළුණු 4ක් මතය:
  </p>

  <!-- 4 Pillars Diagram -->
  <div class="diagram-container">
    <div class="diagram-title">Daily Fortune ගණනය කිරීමේ ප්‍රධාන කුළුණු 4</div>
    <div class="pillars-grid">
      <div class="pillar-card">
        <div class="pillar-num">Pillar 1</div>
        <div class="pillar-name">පංච පක්ෂි ශාස්ත්‍රය</div>
        <div class="pillar-desc">ජන්ම පක්ෂියා සහ දවසේ ක්‍රියාකාරීත්වය (රජ, භෝජන, ගමන, නිදි, මරණ)</div>
      </div>
      <div class="pillar-card">
        <div class="pillar-num">Pillar 2</div>
        <div class="pillar-name">නව තාරා චක්‍රය</div>
        <div class="pillar-desc">දවසේ සඳු සිටින නැකත vs උපන් නැකත (සම්පත්, ක්ෂේම, සාධක, වධ)</div>
      </div>
      <div class="pillar-card">
        <div class="pillar-num">Pillar 3</div>
        <div class="pillar-name">කාල හෝරා බලය</div>
        <div class="pillar-desc">හෝරා 24 හා උපන් ලග්නාධිපති අතර මිත්‍ර/සතුරු ශක්තිය</div>
      </div>
      <div class="pillar-card">
        <div class="pillar-num">Pillar 4</div>
        <div class="pillar-name">පංචාංග ලිතේ දෝෂ</div>
        <div class="pillar-desc">රාහු කාලය, නැකත් වර්ජ්‍ය, විෂ්ටි, අමෘත හා අභිජිත් මුහුර්ථය</div>
      </div>
    </div>
    <div class="synthesis-bar">
      ⬇ ගණිතමය ලකුණු සංස්ලේෂණය (Score: 0 – 100) ➔ සරල ශ්‍රේණි 6 කින් යුත් කාලසටහන
    </div>
  </div>

  <!-- 2. පියවර 1 -->
  <h2>2. පියවර 1: උපන් වේලාවෙන් "ජන්ම සාධක" අතින් සොයාගන්නා හැටි</h2>
  <p>
    කෙනෙකු තමන්ගේ උපන් දිනය, උපන් වේලාව සහ උපන් ස්ථානය ලබා දුන් විට ජ්‍යෝතිෂවේදියෙකු ලංකා පංචාංග ලිත ඇසුරෙන් පහත සාධක සොයා ගනී:
  </p>

  <h3>(අ) අයනාංශය සහ චන්ද්‍ර ස්පුටය (Moon's Sidereal Longitude)</h3>
  <ul>
    <li>උපන් වේලාවේදී අහසේ සඳු (චන්ද්‍රයා) ගමන් කරමින් සිටි නිශ්චිත අංශක ප්‍රමාණය (ස්පුටය) ලිතේ දෛනික ග්‍රහස්පුට සටහනෙන් සොයා ගැනේ (ලහිරි / චිත්‍රපක්ෂ අයනාංශය).</li>
    <li>මුළු අහස අංශක 360ක් වන අතර, එය නැකත් 27කට බෙදූ විට <strong>එක් නැකතක ප්‍රමාණය අංශක 13 කලා 20ක් (13° 20')</strong> වේ.</li>
    <li>එක් නැකතක් පාද 4කට බෙදූ විට <strong>එක් පාදයක ප්‍රමාණය අංශක 3 කලා 20ක් (3° 20')</strong> වේ.</li>
    <li>චන්ද්‍ර ස්පුටය අංශක 13° 20' න් බෙදූ විට ජන්ම නැකතත් (1 සිට 27 දක්වා), ශේෂයෙන් නැකත් පාදයත් (1 සිට 4 දක්වා) ලැබේ.</li>
  </ul>

  <h3>(ආ) පුර පක්ෂයද අව පක්ෂයද යන්න තීරණය කිරීම (Shukla / Krishna Paksha)</h3>
  <ul>
    <li>සූර්යයාගේ සිට චන්ද්‍රයා ඉදිරියෙන් අංශක 0° සිට 180° දක්වා නම් = <strong>පුර පක්ෂය (Shukla Paksha)</strong></li>
    <li>සූර්යයාගේ සිට චන්ද්‍රයා අංශක 180° සිට 360° දක්වා නම් = <strong>අව පක්ෂය (Krishna Paksha)</strong></li>
  </ul>

  <h3>(ඇ) ජන්ම පක්ෂියා (Pancha Pakshi) සොයාගැනීම</h3>
  <p>
    පංච පක්ෂි ශාස්ත්‍රයේ පක්ෂීන් 5 දෙනෙකි: <strong>1. භේරුණ්ඩ (Vulture), 2. බක/පිඟාන (Owl), 3. කපුටා (Crow), 4. කුකුළා (Cock), 5. මයුරා (Peacock)</strong>.
  </p>

  <table>
    <thead>
      <tr>
        <th style="width: 25%;">පක්ෂියා (Bird)</th>
        <th style="width: 37%;">පුර පක්ෂයේ උපන් නැකත් (Shukla)</th>
        <th style="width: 38%;">අව පක්ෂයේ උපන් නැකත් (Krishna)</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>භේරුණ්ඩ (Vulture)</strong></td>
        <td>1. අස්විද සිට 5. මුවසිරස දක්වා</td>
        <td>22. සුවණ සිට 27. රේවතී දක්වා</td>
      </tr>
      <tr>
        <td><strong>බක / බස්සා (Owl)</strong></td>
        <td>6. අද සිට 11. පුවපල් දක්වා</td>
        <td>17. අනුර සිට 21. උතුරුසල දක්වා</td>
      </tr>
      <tr>
        <td><strong>කපුටා (Crow)</strong></td>
        <td>12. උත්රපල් සිට 16. විසා දක්වා</td>
        <td>12. උත්රපල් සිට 16. විසා දක්වා</td>
      </tr>
      <tr>
        <td><strong>කුකුළා (Cock)</strong></td>
        <td>17. අනුර සිට 21. උතුරුසල දක්වා</td>
        <td>6. අද සිට 11. පුවපල් දක්වා</td>
      </tr>
      <tr>
        <td><strong>මයුරා (Peacock)</strong></td>
        <td>22. සුවණ සිට 27. රේවතී දක්වා</td>
        <td>1. අස්විද සිට 5. මුවසිරස දක්වා</td>
      </tr>
    </tbody>
  </table>

  <div class="callout-note">
    <strong>උදාහරණයක්:</strong> යමෙකු පුර පක්ෂයේ රෙහෙන (4 වන) නැකතින් උපන්නේ නම්, ඉහත වගුවට අනුව ඔහුගේ ජන්ම පක්ෂියා <strong>භේරුණ්ඩ</strong> වේ.
  </div>

  <!-- 3. පියවර 2 -->
  <h2>3. පියවර 2: දවසේ වේලාව කොටස් වලට බෙදීම (Daily Time Division)</h2>
  <p>
    ජ්‍යෝතිෂයේ දවස ගණනය කරන්නේ මධ්‍යම රාත්‍රී 12:00 න් නොව <strong>ඉර උදාවූ මොහොතේ (Sunrise)</strong> සිට පසුදා ඉර උදාව දක්වාය.
  </p>
  <ul>
    <li><strong>දහවල් කාලය (Daytime):</strong> සූර්යෝදයේ සිට සූර්යාස්තය දක්වා.</li>
    <li><strong>රාත්‍රී කාලය (Nighttime):</strong> සූර්යාස්තයේ සිට පසුදා සූර්යෝදය දක්වා.</li>
  </ul>

  <p>
    දහවල් කාලය හරියටම <strong>සමාන කොටස් 5 කට (යාම 5)</strong> බෙදනු ලැබේ. රාත්‍රී කාලයද ඒ අයුරින්ම <strong>සමාන යාම 5 කට</strong> බෙදනු ලැබේ:
  </p>

  <div class="formula-box">
    <div class="formula-title">පංච පක්ෂි යාම ගණනය කිරීමේ සූත්‍රය:</div>
    <div class="formula-text">එක් යාමයක දිග = දහවල් මුළු කාලය ÷ 5 = පැය 2 විනාඩි 24යි (සාමාන්‍යයෙන් විනාඩි 144යි)</div>
  </div>

  <!-- 4. පියවර 3 -->
  <h2>4. පියවර 3: පංච පක්ෂි අවස්ථා 5 සහ අතුරු අවස්ථා (Main & Sub Activities)</h2>
  <p>
    පක්ෂියෙකුට එක් දිනකදී හිමිවන අවස්ථා 5කි. මිනිසාගේ ජීව ශක්තිය සහ මානසික ඒකාග්‍රතාවය මේ අනුව වෙනස් වේ:
  </p>

  <table>
    <thead>
      <tr>
        <th style="width: 20%;">අවස්ථාව</th>
        <th style="width: 60%;">අර්ථය හා බලපෑම</th>
        <th style="width: 20%; text-align: center;">ලකුණු මට්ටම</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td><strong>1. රජ (Rule)</strong></td>
        <td>පූර්ණ බලය, ජයග්‍රහණය, ගෞරවය, වැදගත් තීරණ සාර්ථක වීම</td>
        <td style="text-align: center; color: #166534; font-weight: 800;">+17 (ඉතා ඉහළ)</td>
      </tr>
      <tr>
        <td><strong>2. භෝජන (Eat)</strong></td>
        <td>සතුට, ධන ලාභ, ප්‍රබෝධය, ආහාර පාන සහ සුභ ආරංචි ලැබීම</td>
        <td style="text-align: center; color: #047857; font-weight: 800;">+12 (ඉහළ)</td>
      </tr>
      <tr>
        <td><strong>3. ගමන (Walk)</strong></td>
        <td>චලනය, සාමාන්‍ය ගමන් බිමන්, මධ්‍යස්ථ ප්‍රතිඵල</td>
        <td style="text-align: center; color: #0284c7; font-weight: 800;">+3 (මධ්‍යස්ථ)</td>
      </tr>
      <tr>
        <td><strong>4. නිදි (Sleep)</strong></td>
        <td>අලස බව, උදාසීන බව, ප්‍රමාදය, වැදගත් කාර්යයන් අසාර්ථක වීම</td>
        <td style="text-align: center; color: #c2410c; font-weight: 800;">-10 (අඩු)</td>
      </tr>
      <tr>
        <td><strong>5. මරණ (Die)</strong></td>
        <td>පූර්ණ අක්‍රියතාවය, පාඩු, බාධක, ආරවුල්, අනතුරුදායක බව</td>
        <td style="text-align: center; color: #dc2626; font-weight: 800;">-19 (ඉතා අඩු)</td>
      </tr>
    </tbody>
  </table>

  <h3>යාමයක් තුළ අතුරු අවස්ථා 5 (Sub-Periods):</h3>
  <p>
    එක් යාමයක් විනාඩි 144ක් වන අතර, එම විනාඩි 144 ඇතුළතද නැවත පක්ෂීන් 5 දෙනාගේ අතුරු ක්‍රියා 5ක් සිදුවේ. අතුරු අවස්ථාවන් වල කාල පරාසය එක සමාන නොවේ:
  </p>
  <ul>
    <li><strong>රජ අතුරු කාලය:</strong> විනාඩි 48 &nbsp;|&nbsp; <strong>ගමන අතුරු කාලය:</strong> විනාඩි 36 &nbsp;|&nbsp; <strong>භෝජන අතුරු කාලය:</strong> විනාඩි 30 &nbsp;|&nbsp; <strong>නිදි අතුරු කාලය:</strong> විනාඩි 18 &nbsp;|&nbsp; <strong>මරණ අතුරු කාලය:</strong> විනාඩි 12</li>
  </ul>

  <div class="callout-success">
    <strong>Daily Fortune රහස:</strong> ප්‍රධාන යාමයෙන් රජ හෝ භෝජන ලබා සිටින මොහොතක, අතුරු කාලයෙනුත් රජ හෝ භෝජන ලැබෙන මිනිත්තු කිහිපය පුද්ගලයෙකුට ලොතරැයියක් ඇදෙනවාක් මෙන් <strong>අතිශය වාසනාවන්ත (Supreme)</strong> අවස්ථාවකි!
  </div>

  <!-- 5. පියවර 4 -->
  <h2>5. පියවර 4: නව තාරා චක්‍රය (Daily Transit Nava Tara Chakra)</h2>
  <p>
    දවසේ ඕනෑම මොහොතක අහසේ චන්ද්‍රයා ගමන් කරන නැකත, කෙනෙකුගේ උපන් නැකත සමඟ සසඳන ක්‍රමය <strong>නව තාරා චක්‍රය</strong> නම් වේ.
  </p>

  <div class="formula-box">
    <div class="formula-title">නව තාරා අංකය සෙවීමේ සූත්‍රය:</div>
    <div class="formula-text">තාරා අංකය = [ (දවසේ සඳු නැකත - ජන්ම නැකත) % 27 % 9 ] + 1</div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width: 10%; text-align: center;">අංකය</th>
        <th style="width: 25%;">තාරාවේ නම (Tara)</th>
        <th style="width: 50%;">ඵලය හා තත්වය</th>
        <th style="width: 15%; text-align: center;">ලකුණු</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="text-align: center; font-weight: 700;">1</td>
        <td><strong>ජන්ම (Janma)</strong></td>
        <td>ශරීර වෙහෙස, සාමාන්‍ය බාධක</td>
        <td style="text-align: center; color: #64748b; font-weight: 700;">-3</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 700;">2</td>
        <td><strong>සම්පත් (Sampath)</strong></td>
        <td>ධනය, ලාභය, ව්‍යාපාර දියුණුව, වාසනාව</td>
        <td style="text-align: center; color: #166534; font-weight: 800;">+14</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 700;">3</td>
        <td><strong>විපත් (Vipat)</strong></td>
        <td>අනතුරු, පාඩු, බලාපොරොත්තු කඩවීම</td>
        <td style="text-align: center; color: #dc2626; font-weight: 800;">-15</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 700;">4</td>
        <td><strong>ක්ෂේම (Kshema)</strong></td>
        <td>ආරක්ෂාව, සතුට, නිරෝගීභාවය</td>
        <td style="text-align: center; color: #166534; font-weight: 800;">+11</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 700;">5</td>
        <td><strong>ප්‍රත්‍යාරි (Pratyak)</strong></td>
        <td>සතුරන් ඇතිවීම, විරෝධතා, නඩුහබ</td>
        <td style="text-align: center; color: #c2410c; font-weight: 800;">-13</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 700;">6</td>
        <td><strong>සාධක (Sadhaka)</strong></td>
        <td>අරමුණු ඉටුවීම, ජයග්‍රහණය, විභාග ජය</td>
        <td style="text-align: center; color: #166534; font-weight: 800;">+13</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 700;">7</td>
        <td><strong>වධ / නෛධන (Vadha)</strong></td>
        <td>අතිශය අසුභයි, විපත්ති, මාරක බාධක</td>
        <td style="text-align: center; color: #b91c1c; font-weight: 800;">-22</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 700;">8</td>
        <td><strong>මිත්‍ර (Mitra)</strong></td>
        <td>සහයෝගය, මිතුරන්ගෙන් උදව්, ප්‍රීතිය</td>
        <td style="text-align: center; color: #166534; font-weight: 800;">+12</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 700;">9</td>
        <td><strong>පරම මිත්‍ර (Parama Mitra)</strong></td>
        <td>උසස්ම සුභ ඵල, ප්‍රධාන ගනුදෙනු වලට සුදුසුයි</td>
        <td style="text-align: center; color: #047857; font-weight: 800;">+16</td>
      </tr>
    </tbody>
  </table>

  <div class="callout-alert">
    <strong>දැඩි අවවාදයයි:</strong> 7 වන තාරාව හෙවත් <strong>"වධ තාරාව"</strong> ලබන කාලය තුළ වෙනත් කුමන සුභ යෝග තිබුණද එම කාලය කිසිවිටෙකත් "ඉතාමත් සුභ" (Supreme) මට්ටමට පත් නොවේ.
  </div>

  <!-- 6. පියවර 5 -->
  <h2>6. පියවර 5: කාල හෝරා (24 Horas) සහ චන්ද්‍රබලය</h2>
  <p>
    <strong>හෝරා 24 (Chaldean Order):</strong> දවසේ සෑම පැයකටම අධිපති ග්‍රහයෙකු සිටී. හෝරා ක්‍රියාත්මක වන්නේ අහසේ කක්ෂ වේගය අනුවය: <strong>සෙනසුරු ➔ ගුරු ➔ කුජ ➔ රවි ➔ සිකුරු ➔ බුධ ➔ සඳු</strong>. උපන් කේන්ද්‍රයේ ලග්නාධිපතිට මිත්‍ර ග්‍රහ හෝරාවකදී සුභ ලකුණු වැඩිවන අතර සතුරු හෝරාවකදී ලකුණු අඩුවේ.
  </p>
  <p>
    <strong>චන්ද්‍රබලය සහ චන්ද්‍රාෂ්ටමය:</strong> උපන් රාශියේ සිට 1, 3, 6, 7, 10, 11 හි සඳු ගමන් කරන විට සුභ චන්ද්‍රබලය (+8 සිට +10) ලැබේ. නමුත් <strong>8 වැන්නේ සඳු ගමන් කරන කාලය (චන්ද්‍රාෂ්ටමය)</strong> දැඩි මානසික පීඩා ගෙන දෙන බැවින් ලකුණු -22 කින් අඩු කෙරේ.
  </p>

  <!-- 7. පියවර 6 -->
  <h2>7. පියවර 6: ලංකා පංචාංග ලිතේ විශේෂ දෝෂ සහ ශුභ මුහුර්ථ</h2>
  <ol>
    <li><strong>රාහු කාලය (Rahu Kaalam):</strong> දහවල් කාලයෙන් 1/8ක් (පැය 1 1/2ක්). ලකුණු -28කින් පහත බසින අතර උපරිම ලකුණු සීමාව (Hard Cap) 38කට සීමා කෙරේ. කිසිවිටෙකත් සුභ විය නොහැක!</li>
    <li><strong>නැකත් වර්ජ්‍ය කාලය (Varjyam / Visha Ghatis):</strong> සෑම නැකතකටම අදාළ විෂ ඝටී 4ක (පැය 1 විනාඩි 36ක) විනාශකාරී කාලය. ලකුණු -24 කි.</li>
    <li><strong>විෂ්ටි කරණය (Vishti Karana / Bhadra):</strong> කරණ 11න් අසුභම කරණයයි. ලකුණු -22 දක්වා අඩු වේ.</li>
    <li><strong>යමගණ්ඩය සහ ගුලික කාලය:</strong> අසුභ කාල පරාසයන් (-12 සිට -15).</li>
    <li><strong>අමෘත ඝටී / අභිජිත් මුහුර්ථය:</strong> දවසේ මැද භාගයේ (දහවල් 11:36 - 12:24) යෙදෙන අභිජිත් මුහුර්ථය සහ ලිතේ එන අමෘත කාලයෙන් අතිරේක +14 සිට +18 දක්වා සුභ ලකුණු ලැබේ.</li>
  </ol>

  <!-- 8. පියවර 7 -->
  <h2>8. පියවර 7: අවසාන 6-Tier ශ්‍රේණිය (The 6-Grade Synthesis)</h2>
  <p>
    Daily Fortune ඇල්ගොරිතමය ඉහත සියලුම සාධක ගණිතමය ලකුණු ක්‍රමයකට ගෙන එයි:
  </p>

  <div class="formula-box">
    <div class="formula-title">ලකුණු එකතු කිරීමේ සූත්‍රය:</div>
    <div class="formula-text">මුළු ලකුණු වෙනස (Δ) = පක්ෂි ලකුණු + තාරා බලය + චන්ද්‍ර බලය + හෝරා බලය + ලිතේ යෝග/දෝෂ</div>
    <div class="formula-text" style="margin-top: 4px;">අවසාන ලකුණ (Score) = 50 + (Δ × 0.72)  [දෝෂ ඇත්නම් Hard-Cap සීමා යෙදේ]</div>
  </div>

  <table>
    <thead>
      <tr>
        <th style="width: 15%; text-align: center;">ලකුණු</th>
        <th style="width: 25%;">පෙනෙන තත්වය</th>
        <th style="width: 60%;">තේරුම සහ කළ යුතු දේ</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td style="text-align: center; font-weight: 800;">86 – 100</td>
        <td><span class="badge badge-supreme">★ ඉතාමත් සුභ</span></td>
        <td>ඉහළම වාසනාවන්ත වේලාව. මංගල කටයුතු, ගිවිසුම් අත්සන් කිරීම, රැකියා සම්මුඛ පරීක්ෂණ, ආයෝජන වලට අතිශය සුදුසුයි.</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 800;">73 – 85</td>
        <td><span class="badge badge-vgood">ඉතා සුභ</span></td>
        <td>ඉතා යහපත් ප්‍රතිඵල දෙන කාලයකි. නව වැඩ ඇරඹීමට, මුදල් ගනුදෙනු වලට, සාකච්ඡා වලට සුදුසුයි.</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 800;">58 – 72</td>
        <td><span class="badge badge-good">සුභ</span></td>
        <td>සාර්ථක ප්‍රතිඵල ලැබේ. එදිනෙදා වැදගත් රාජකාරි කර ගැනීමට සුදුසුයි.</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 800;">42 – 57</td>
        <td><span class="badge badge-neutral">සාමාන්‍ය</span></td>
        <td>සුභ හෝ අසුභ ප්‍රබල නැත. සාමාන්‍ය දවසේ වැඩ කරගෙන යාමට බාධාවක් නැත.</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 800;">25 – 41</td>
        <td><span class="badge badge-bad">අසුභ</span></td>
        <td>බාධක, ප්‍රමාදයන් ඇතිවේ. වැදගත් තීරණ ගැනීමෙන් වළකින්න.</td>
      </tr>
      <tr>
        <td style="text-align: center; font-weight: 800;">0 – 24</td>
        <td><span class="badge badge-vbad">ඉතා අසුභ</span></td>
        <td>රාහු කාලය, මරණ අවස්ථාව හෝ වධ තාරාව ක්‍රියාත්මක වේ. පාඩු, රණ්ඩු සරුවල් විය හැක. කිසිදු සුභ වැඩක් නොකරන්න.</td>
      </tr>
    </tbody>
  </table>

  <!-- 9. විකිණීමේ උපදෙස් -->
  <h2>9. පාරිභෝගිකයින්ට මෙය විකුණන විට පැහැදිලි කරන ආකාරය (Sales & FAQ Guide)</h2>

  <div class="qa-card">
    <div class="qa-q"><span>Q1</span> "මොකක්ද මේ ඇප් එකේ තියෙන වෙනස? පත්තර වලත් රාශි පලාපල තියෙන්නේ?"</div>
    <div class="qa-a">
      "පත්තරේ තියෙන්නේ ලෝකයේ ඉන්න කෝටි ගණනක් මේෂ ලග්න හිමියන්ටම පොදු අනාවැකියක්. ඒකෙන් ඔබට අද දවසේ ගිවිසුමක් අත්සන් කරන්න, ඉන්ටවීව් එකකට යන්න හොඳම වෙලාව හොයාගන්න බැහැ. නමුත් <strong>Daily Fortune</strong> කියන්නේ ඔබේම උපන් වේලාවට, ඔබේම උපන් නැකතට සහ ජන්ම පක්ෂියාට අනුව හැදෙන <strong>පුද්ගලික ජෛව-කාලසටහනක් (Personal Bio-Rhythm Schedule)</strong>. ලිතේ තියෙන රාහු කාලය, හෝරාව, තාරා බලය සේරම එකතු කරලා ඔබටම විතරක් ඔබේ දවස කළමනාකරණය කරගන්න දෙන විද්‍යාත්මක උපදේශකයෙක්."
    </div>
  </div>

  <div class="qa-card">
    <div class="qa-q"><span>Q2</span> "මම කේන්දර ගැන දන්නේ නැහැ, මට මේකෙන් තේරෙයිද?"</div>
    <div class="qa-a">
      "අනිවාර්යයෙන්ම! සාමාන්‍ය කෙනෙකුට කපුටු, කුකුළු, වධ තාරා, විෂ්ටි කරණ කියලා ජ්‍යෝතිෂ වචන කිව්වම තේරෙන්නේ නැහැ. ඔළුව අවුල් වෙනවා. ඒ නිසයි අපි මේක හදලා තියෙන්නේ පොඩි ළමයෙකුට වුණත් බැලූ බැල්මට තේරෙන සරල වර්ණ 6 කින් (කොළ පාට නම් හොඳයි, රතු පාට නම් වැඩේ නවත්තන්න). ඔබට තියෙන්නේ ඔබේ දවස පටන් ගන්න කලින් ෆෝන් එකෙන් අද දවසේ 'ඉතාමත් සුභ' වෙලාව සහ 'අසුභ' වෙලාව බලාගෙන ඒ අනුව දවසේ වැඩ ටික ප්ලෑන් කරගන්න විතරයි."
    </div>
  </div>

  <div class="qa-card">
    <div class="qa-q"><span>Q3</span> "ජ්‍යෝතිෂවේදියෙක් ඇහුවොත්: මේක ලංකාවේ ක්‍රමයට ගැලපෙනවද?"</div>
    <div class="qa-a">
      "100%ක්ම ගැලපෙනවා. මේ මෘදුකාංගය පිටුපස ක්‍රියාත්මක වන්නේ ලංකා පංචාංග ග්‍රහස්පුට ලිතේ නිවැරදි සූර්ය උදාව, චිත්‍රපක්ෂ (ලහිරි) අයනාංශය, පුරාණ පංච පක්ෂි ශාස්ත්‍රය, නව තාරා චක්‍රය, කාල හෝරා සහ රාහු කාලයයි. ප්‍රවීණ ජ්‍යෝතිෂවේදියෙකුට පැය 3ක් තිස්සේ ලිත පෙරළලා අමාරුවෙන් හදන්න වෙන චාර්ට් එක මේ ඇප් එක තත්පර 1 කින් සකසා දෙනවා."
    </div>
  </div>

  <!-- 10. සාරාංශය -->
  <h2>10. සාරාංශය (Summary)</h2>
  <div class="callout-note" style="background: #f8fafc; border-left-color: #4f46e5; color: #1e293b;">
    <strong>Daily Fortune</strong> යනු අනුමාන අනාවැකි කියන ඇප් එකක් නොවේ. එය:<br>
    <strong>1. නිරවද්‍ය තාරකා විද්‍යාව (High-Precision Astronomy)</strong> &nbsp;•&nbsp;
    <strong>2. පුරාණ පංචාංග ගණිතය (Classical Panchanga Mathematics)</strong> &nbsp;•&nbsp;
    <strong>3. පංච පක්ෂි ජීව-ශක්ති විද්‍යාව (Bio-Rhythmic Energy Timing)</strong><br>
    එක්තැන් කොට, නවීන ලෝකයේ මිනිසුන්ට තමන්ගේ දවසේ ජයග්‍රහණය උදාකර ගැනීමට සාදාදුන් අසමසම ප්‍රායෝගික මෙවලමකි!
  </div>

</body>
</html>
"""


def main():
    browser = find_browser_binary()
    if not browser:
        print("ERROR: Chrome/Edge browser not found.")
        return 1

    out_pdf_proj = Path(r"K:\STAR\DailyFortune\DAILY_FORTUNE_THEORY_MANUAL.pdf")
    out_pdf_brain = Path(r"C:\Users\Ruwan\.gemini\antigravity\brain\bf1b3e8d-9d59-4a5a-8247-0d53ddb7c423\DAILY_FORTUNE_THEORY_MANUAL.pdf")

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        html_file = tmp / "manual.html"
        pdf_file = tmp / "manual.pdf"
        user_data = tmp / "chrome_profile"

        html_file.write_text(HTML_TEMPLATE, encoding="utf-8")

        cmd = [
            browser,
            "--headless=new",
            "--disable-gpu",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-extensions",
            "--no-pdf-header-footer",
            f"--user-data-dir={user_data}",
            f"--print-to-pdf={pdf_file}",
            html_file.as_uri(),
        ]
        print("Rendering PDF via:", browser)
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=40)
        if proc.returncode != 0 or not pdf_file.is_file():
            print("Failed:", proc.stderr or proc.stdout)
            return 1

        pdf_bytes = pdf_file.read_bytes()
        out_pdf_proj.write_bytes(pdf_bytes)
        out_pdf_brain.write_bytes(pdf_bytes)
        print(f"SUCCESS: Generated {len(pdf_bytes):,} bytes PDF at:")
        print(f"  -> {out_pdf_proj}")
        print(f"  -> {out_pdf_brain}")

    return 0


if __name__ == "__main__":
    import sys
    sys.exit(main())
