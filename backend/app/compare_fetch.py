from app.gdelt import fetch_latest_export_events
import requests, io, zipfile, csv

print('calling fetch_latest_export_events(limit=1000, only_country="UP")')
res = fetch_latest_export_events(1000, 'UP')
print('fetch_latest_export_events returned', len(res))

# now perform identical manual inspect
r = requests.get('http://data.gdeltproject.org/gdeltv2/lastupdate.txt', timeout=30)
export = None
for line in r.text.splitlines():
    if line.strip().endswith('.export.CSV.zip'):
        export = line.split()[-1]
        break
print('manual export url:', export)

z = requests.get(export, timeout=60)
with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
    name = [n for n in zf.namelist() if n.endswith('.export.CSV')][0]
    cnt = 0
    total = 0
    with zf.open(name) as fh:
        reader = csv.reader(io.TextIOWrapper(fh, encoding='utf-8', errors='replace'), delimiter='\t')
        for row in reader:
            total += 1
            if len(row) > 54 and row[54].strip() == 'UP':
                cnt += 1
    print('manual count total rows', total, 'UP', cnt)
