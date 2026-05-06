import ast, pathlib, sys
files = ['main.py', 'exporter.py', 'routers/publish.py']
ok = True
for f in files:
    try:
        ast.parse(pathlib.Path(f).read_text(encoding='utf-8'))
        sys.stderr.write(f'OK: {f}\n')
    except Exception as e:
        sys.stderr.write(f'ERROR {f}: {e}\n')
        ok = False
sys.exit(0 if ok else 1)
