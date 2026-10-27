import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

with open(os.path.join(BASE_DIR, 'drawio_urls.txt'), 'r', encoding='utf-8') as f:
    lines = [l.strip() for l in f if l.strip()]

cdfg_url = lines[0].split('=', 1)[1]
fsm_url = lines[1].split('=', 1)[1]

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Open Diagrams in Draw.io (1-Click)</title>
  <style>
    body {{
      background: #0b0f19;
      color: #f8fafc;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 100vh;
      margin: 0;
      padding: 20px;
    }}
    .card {{
      background: #1e293b;
      border: 1px solid #334155;
      border-radius: 16px;
      padding: 36px;
      max-width: 640px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 40px rgba(0,0,0,0.6);
    }}
    h1 {{ font-size: 24px; margin-bottom: 12px; color: #38bdf8; }}
    p {{ color: #94a3b8; font-size: 14px; line-height: 1.6; margin-bottom: 24px; }}
    .btn-container {{ display: flex; flex-direction: column; gap: 16px; }}
    .btn {{
      display: block;
      background: #0284c7;
      color: white;
      text-decoration: none;
      padding: 16px 24px;
      border-radius: 10px;
      font-weight: 700;
      font-size: 16px;
      transition: all 0.2s ease;
      box-shadow: 0 4px 14px rgba(2, 132, 199, 0.4);
    }}
    .btn:hover {{ background: #0369a1; transform: translateY(-2px); }}
    .btn-fsm {{ background: #059669; box-shadow: 0 4px 14px rgba(5, 150, 105, 0.4); }}
    .btn-fsm:hover {{ background: #047857; }}
    .footer-note {{ margin-top: 24px; font-size: 12px; color: #64748b; line-height: 1.5; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>📐 1-Click Launch in Draw.io</h1>
    <p>Neeche diye gaye buttons par click kijiye — draw.io automatically browser me diagram load kar dega:</p>
    <div class="btn-container">
      <a class="btn" target="_blank" href="{cdfg_url}">📊 1. Open CDFG Diagram in Draw.io</a>
      <a class="btn btn-fsm" target="_blank" href="{fsm_url}">🔄 2. Open Moore FSM Diagram in Draw.io</a>
    </div>
    <div class="footer-note">
      Aapka diagram poora vector, editable aur standard draw.io blocks me load hoga.<br>
      Aap text edit kar sakte hain, zoom kar sakte hain, ya <b>File &rarr; Export as &rarr; PNG/PDF</b> kar sakte hain.
    </div>
  </div>
</body>
</html>
"""

with open(os.path.join(BASE_DIR, 'open_drawio.html'), 'w', encoding='utf-8') as f:
    f.write(html)
print('Updated open_drawio.html successfully!')
