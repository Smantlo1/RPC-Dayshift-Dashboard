"""Fix the f-string backslash issue in exporter.py (Python < 3.12 restriction)."""
import pathlib, re, sys

src = pathlib.Path('exporter.py').read_text(encoding='utf-8')

old_block = """    if criticals:
        items = \"\".join(
            f'<li style=\"margin:4px 0\">'
            f'{\"\N{ROTATING LIGHT}\" if c.get(\"is_critical\") else \"\N{NO ENTRY}\"} '
            f'<strong>{c[\"text\"]}</strong>'
            f'{\"\u00a0\u2014\u00a0\" + c[\"owner\"] if c.get(\"owner\") else \" <em style=\\'color:#dc2626\\'>UNOWNED</em>\"}'
            f\"</li>\"
            for c in criticals[:6]
        )
        alerts_html += f'<ul style=\"margin:0;padding-left:18px;font-size:13px;\">{items}</ul>'"""

# Line-based approach — find and replace lines 130-140 specifically
lines = src.splitlines()

# Find "if criticals:" within the alerts block (around line 130)
start = None
for i, line in enumerate(lines):
    if '    if criticals:' in line and i > 125:
        start = i
        break

if start is None:
    print("Could not find 'if criticals:' block. Searching...")
    for i, line in enumerate(lines):
        if 'if criticals:' in line:
            print(f"  Line {i+1}: {line!r}")
    sys.exit(1)

# Find the end of this block (the alerts_html += ... line)
end = start
for j in range(start, min(start + 15, len(lines))):
    if 'alerts_html +=' in lines[j] and '<ul' in lines[j]:
        end = j
        break

print(f"Found block at lines {start+1}–{end+1}")
print("Block:")
for k in range(start, end+1):
    print(f"  {k+1}: {lines[k]!r}")

new_block = '''    if criticals:
        _uo = \'<em style="color:#dc2626">UNOWNED</em>\'
        def _crow(c):
            f = "\\U0001f6a8" if c.get("is_critical") else "\\u26d4"
            op = (" \u2014 " + c["owner"]) if c.get("owner") else (" " + _uo)
            return f\'<li style="margin:4px 0">{f} <strong>{c["text"]}</strong>{op}</li>\'
        items = "".join(_crow(c) for c in criticals[:6])
        alerts_html += f\'<ul style="margin:0;padding-left:18px;font-size:13px;">{items}</ul>\''''

lines[start:end+1] = new_block.splitlines()
result = "\n".join(lines) + "\n"
pathlib.Path('exporter.py').write_text(result, encoding='utf-8')
print("Patched exporter.py successfully.")
