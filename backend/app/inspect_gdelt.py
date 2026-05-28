import requests, io, zipfile
r = requests.get('http://data.gdeltproject.org/gdeltv2/lastupdate.txt', timeout=30)
lines = r.text.splitlines()
print('lastupdate sample:', lines[:5])
export = None
for line in lines:
    if line.strip().endswith('.export.CSV.zip'):
        export = line.split()[-1]
        break
print('export url:', export)
z = requests.get(export, timeout=60)
with zipfile.ZipFile(io.BytesIO(z.content)) as zf:
    for name in zf.namelist():
        if name.endswith('.export.CSV'):
            print('csv name:', name)
            with zf.open(name) as fh:
                for i in range(3):
                    raw = fh.readline()
                    text = raw.decode('utf-8', errors='replace')
                    print('--- raw bytes len', len(raw))
                    print(text[:800])
                    print('cols tab:', len(text.split('\t')))
                    print('cols comma:', len(text.split(',')))
            break
    # now count countries in ActionGeo_CountryCode (col index 55 -> idx 54)
    from collections import Counter
    cnt = Counter()
    with zf.open(name) as fh:
        import csv
        for row in csv.reader(io.TextIOWrapper(fh, encoding='utf-8', errors='replace'), delimiter='\t'):
            country = row[54].strip() if len(row) > 54 else ''
            cnt[country] += 1
    print('top countries (sample):', cnt.most_common(10))
    print('UP count:', cnt.get('UP', 0))
    # write UP events to /app/data/events.json for frontend consumption
    up_events = []
    with zf.open(name) as fh:
        import csv
        for row in csv.reader(io.TextIOWrapper(fh, encoding='utf-8', errors='replace'), delimiter='\t'):
            if len(row) <= 54:
                continue
            country = row[54].strip()
            if country != 'UP':
                continue
            try:
                lat = float(row[52].strip())
                lon = float(row[53].strip())
            except Exception:
                continue
            if lat == 0.0 and lon == 0.0:
                continue
            try:
                evt_id = int(row[0])
            except Exception:
                evt_id = hash('\t'.join(row)) & 0xFFFFFFFF
            event_code = ''
            for token in row[:30]:
                t = token.strip()
                if t.isdigit() and len(t) <= 4 and t != row[0]:
                    event_code = t
                    break
            sourceurl = row[-1].strip() if row else ''
            up_events.append({
                'id': evt_id,
                'event_code': event_code,
                'sourceurl': sourceurl,
                'title': sourceurl or 'GDELT Event',
                'lat': lat,
                'lon': lon,
                'country': country,
            })
    import os, json
    os.makedirs('/app/data', exist_ok=True)
    with open('/app/data/events.json', 'w', encoding='utf-8') as f:
        json.dump(up_events, f, ensure_ascii=False)
    print('wrote /app/data/events.json with', len(up_events), 'UP events')
