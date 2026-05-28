import requests, io, zipfile, csv
r = requests.get('http://data.gdeltproject.org/gdeltv2/lastupdate.txt', timeout=30)
export = [l for l in r.text.splitlines() if l.strip().endswith('.export.CSV.zip')][0].split()[-1]
z = requests.get(export, timeout=60)
with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
    name = [n for n in zf.namelist() if n.endswith('.export.CSV')][0]
    print('csv name:', name)
    with zf.open(name) as fh:
        t = io.TextIOWrapper(fh, encoding='utf-8', errors='replace')
        reader = csv.reader(t, delimiter='\t')
        up = []
        for i,row in enumerate(reader):
            if len(row)>54 and row[54].strip()=='UP':
                up.append(row)
            if len(up)>=10:
                break
    print('found', len(up), 'sample UP rows')
    for r in up:
        print('len', len(r))
        print('idx50-56:', [r[i] if i<len(r) else '<MISSING>' for i in range(50,57)])
