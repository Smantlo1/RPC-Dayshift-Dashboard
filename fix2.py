"""Fix exporter.py by line-number surgery."""
import pathlib, ast, sys

p = pathlib.Path('exporter.py')
lines = p.read_text(encoding='utf-8').splitlines()

# Find the exact "if criticals:" block start index
start = None
for i, ln in enumerate(lines):
    if ln.strip() == 'if criticals:' and i > 100:
        start = i
        break

if start is None:
    sys.stderr.write('Could not find block\n')
    sys.exit(1)

# Find end: the "alerts_html +=" line that closes the block
end = None
for j in range(start+1, start+15):
    if 'alerts_html +=' in lines[j] and '<ul' in lines[j]:
        end = j
        break

sys.stderr.write(f'Block: lines {start+1}-{end+1}\n')

# Write the replacement lines (no f-strings with backslashes)
replacement = [
    '    if criticals:',
    '        _uo = \'<em style="color:#dc2626">UNOWNED</em>\'',
    '        def _crow(c):',
    '            flag = "\\U0001f6a8" if c.get("is_critical") else "\\u26d4"',
    '            owner_part = (" \u2014 " + c["owner"]) if c.get("owner") else (" " + _uo)',
    '            return (\'<li style="margin:4px 0">\' + flag +',
    '                    \' <strong>\' + c["text"] + \'</strong>\' + owner_part + \'</li>\')',
    '        items = "".join(_crow(c) for c in criticals[:6])',
    '        alerts_html += (\'<ul style="margin:0;padding-left:18px;font-size:13px;">\''
    '                        + items + \'</ul>\')',
]

lines[start:end+1] = replacement
result = '\n'.join(lines) + '\n'

# Verify it parses
try:
    ast.parse(result)
    sys.stderr.write('Syntax OK after patch\n')
except SyntaxError as e:
    sys.stderr.write(f'Still has syntax error: {e}\n')
    sys.exit(1)

p.write_text(result, encoding='utf-8')
sys.stderr.write('Written successfully\n')
