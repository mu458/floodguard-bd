from flask import Flask, render_template, jsonify, request, Response
from datetime import datetime, timedelta, timezone
import math, random, threading, time, statistics
from live_data import fetch_ffwc_current

app = Flask(__name__, template_folder='.')

MYMENSINGH_REAL = [
('2026-05-09 09:00:00',9.29),('2026-05-09 12:00:00',9.23),('2026-05-09 15:00:00',9.18),('2026-05-09 18:00:00',9.13),
('2026-05-10 06:00:00',8.87),('2026-05-10 09:00:00',8.82),('2026-05-10 12:00:00',8.75),('2026-05-10 15:00:00',8.69),('2026-05-10 18:00:00',8.64),
('2026-05-11 06:00:00',8.41),('2026-05-11 09:00:00',8.36),('2026-05-11 12:00:00',8.30),('2026-05-11 15:00:00',8.25),('2026-05-11 18:00:00',8.20),
('2026-05-12 06:00:00',8.04),('2026-05-12 09:00:00',7.99),('2026-05-12 12:00:00',7.96),('2026-05-12 15:00:00',7.92),('2026-05-12 18:00:00',7.88),
('2026-05-13 06:00:00',7.80),('2026-05-13 09:00:00',7.78),('2026-05-13 12:00:00',7.79),('2026-05-13 15:00:00',7.80),('2026-05-13 18:00:00',7.78),
('2026-05-14 06:00:00',7.76),('2026-05-14 09:00:00',7.76),('2026-05-14 12:00:00',7.75),('2026-05-14 15:00:00',7.75),('2026-05-14 18:00:00',7.74),
('2026-05-15 06:00:00',8.11),('2026-05-15 09:00:00',8.36),('2026-05-15 12:00:00',9.06),('2026-05-15 15:00:00',9.96),('2026-05-15 18:00:00',10.86),
('2026-05-16 06:00:00',11.64),('2026-05-16 09:00:00',11.68)]

STATIONS = {
 'mymensingh': {'name':'Mymensingh — Old Brahmaputra','district':'Mymensingh','division':'Mymensingh','river':'Old Brahmaputra','station':'Mymensingh','danger':12.05,'lat':24.747,'lon':90.420,'target':11.68},
 'jamalpur': {'name':'Jamalpur — Old Brahmaputra','district':'Jamalpur','division':'Mymensingh','river':'Old Brahmaputra','station':'Jamalpur','danger':16.55,'lat':24.937,'lon':89.937,'target':15.10},
 'sylhet': {'name':'Sylhet — Surma','district':'Sylhet','division':'Sylhet','river':'Surma','station':'Sylhet','danger':10.50,'lat':24.895,'lon':91.869,'target':10.15},
 'sunamganj': {'name':'Sunamganj — Surma','district':'Sunamganj','division':'Sylhet','river':'Surma','station':'Sunamganj','danger':7.20,'lat':25.066,'lon':91.395,'target':6.30},
 'kurigram': {'name':'Kurigram — Dharla','district':'Kurigram','division':'Rangpur','river':'Dharla','station':'Kurigram','danger':26.50,'lat':25.805,'lon':89.636,'target':27.05},
 'gaibandha': {'name':'Gaibandha — Ghaghat','district':'Gaibandha','division':'Rangpur','river':'Ghaghat','station':'Gaibandha','danger':21.25,'lat':25.329,'lon':89.542,'target':18.30},
 'sirajganj': {'name':'Sirajganj — Jamuna','district':'Sirajganj','division':'Rajshahi','river':'Jamuna','station':'Sirajganj','danger':13.35,'lat':24.453,'lon':89.700,'target':13.00},
 'rajshahi': {'name':'Rajshahi — Padma','district':'Rajshahi','division':'Rajshahi','river':'Padma','station':'Rajshahi','danger':18.50,'lat':24.374,'lon':88.604,'target':15.80},
}

# Latest known FFWC bulletin snapshots supplied for this project.
# These are used only when the public feed cannot be read; they are never labelled as live.
FFWC_BULLETIN_SNAPSHOT = {
    'mymensingh': {'current': 6.32, 'danger': 12.05, 'observed_at': '2026-09-09 09:00', 'source': 'FFWC bulletin snapshot'},
    'jamalpur': {'current': 12.14, 'danger': 16.55, 'observed_at': '2026-09-09 09:00', 'source': 'FFWC bulletin snapshot'},
}

LIVE_CACHE = {
    'payload': None,
    'expires': 0,
    'error': None,
    'state': 'idle',
    'last_attempt': None,
}
CACHE_SECONDS = 300
_cache_lock = threading.Lock()
_worker_lock = threading.Lock()
_worker_running = False

def _live_worker():
    global _worker_running
    try:
        with _cache_lock:
            LIVE_CACHE['state']='syncing'
            LIVE_CACHE['last_attempt']=datetime.now(timezone.utc).isoformat()
        payload = fetch_ffwc_current()
        with _cache_lock:
            LIVE_CACHE.update(payload=payload, expires=time.time()+CACHE_SECONDS, error=None, state='connected')
    except Exception as exc:
        with _cache_lock:
            LIVE_CACHE['error']=str(exc)
            LIVE_CACHE['state']='unavailable' if not LIVE_CACHE.get('payload') else 'stale'
    finally:
        with _worker_lock:
            _worker_running=False

def trigger_live_refresh(force=False):
    global _worker_running
    now=time.time()
    with _worker_lock:
        if _worker_running:
            return False
        if (not force and LIVE_CACHE.get('payload') and now < LIVE_CACHE.get('expires',0)):
            return False
        _worker_running=True
        threading.Thread(target=_live_worker, daemon=True).start()
        return True

def live_snapshot(force=False):
    # Never perform network I/O in a Flask request. Return cached data immediately.
    # Live refresh is handled by a background worker.
    with _cache_lock:
        payload = LIVE_CACHE.get('payload')
        state = LIVE_CACHE.get('state', 'idle')
    if payload:
        return payload
    # First load: use an empty live snapshot and let the background worker update it.
    return {'ok': False, 'source': 'background sync', 'source_url': 'https://ffwc.gov.bd/app/observed-water-level',
            'fetched_at': None, 'table_date': None, 'data': {}, 'state': state}

def re_key(x):
    return ''.join(ch for ch in str(x).lower() if ch.isalnum())


def live_for_station(key, force=False):
    st = STATIONS[key]
    snap = live_snapshot()
    data = snap.get('data', {})
    target = (re_key(st['river']), re_key(st['station']))
    hit = data.get(target)
    if hit:
        return {**hit, 'live': True}
    station_norm = re_key(st['station'])
    for (_, sta), v in data.items():
        if sta == station_norm:
            return {**v, 'live': True}
    snaprow=FFWC_BULLETIN_SNAPSHOT.get(key)
    if snaprow:
        return {'live': False, 'source': snaprow['source'], 'current': snaprow['current'], 'danger': snaprow['danger'], 'observed_at': snaprow['observed_at'], 'source_url': 'https://ffwc.gov.bd/app/daily-waterlevel-report', 'snapshot': True}
    return {'live': False, 'source': 'reference data', 'current': st['target'], 'danger': st['danger'], 'observed_at': None, 'source_url': snap.get('source_url'), 'snapshot': False}


def make_demo_history(key):
    if key == 'mymensingh':
        rows=[{'time':t,'level':v,'kind':'Historical reading'} for t,v in MYMENSINGH_REAL]
        start=datetime.strptime(MYMENSINGH_REAL[0][0],'%Y-%m-%d %H:%M:%S')-timedelta(hours=3*56)
        rng=random.Random(11)
        for i in range(56):
            dt=start+timedelta(hours=3*i)
            val=9.8-0.035*i+0.10*math.sin(i/3)+rng.uniform(-0.025,0.025)
            rows.append({'time':dt.strftime('%Y-%m-%d %H:%M:%S'),'level':val,'kind':'Historical extension'})
        rows.sort(key=lambda x:x['time'])
        return rows
    st=STATIONS[key]
    rng=random.Random(sum(ord(c) for c in key))
    end=datetime(2026,5,16,9)
    start=end-timedelta(hours=3*159)
    start_level=st['target']-rng.uniform(-0.35,0.55)
    rows=[]
    for i in range(160):
        dt=start+timedelta(hours=3*i)
        progress=i/159
        event=0
        if key in {'sylhet','kurigram','sirajganj'} and i>128: event=(i-128)*0.055
        if key=='sunamganj' and i>118: event=(i-118)*0.020
        level=start_level+(st['target']-start_level)*progress+0.12*math.sin(i/6)+0.05*math.sin(i/18)+event+rng.uniform(-0.045,0.045)
        rows.append({'time':dt.strftime('%Y-%m-%d %H:%M:%S'),'level':level,'kind':'Historical extension'})
    rows[-1]['level']=st['target']
    return rows


def risk_for(level, danger):
    ratio=level/danger if danger else 0
    if ratio >= 1.02: return 'SEVERE'
    if ratio >= .96: return 'FLOOD'
    if ratio >= .86: return 'WARNING'
    return 'NORMAL'


def predict_24h(current, previous, danger):
    slope = current - previous
    predicted = max(0, current + slope * 8)
    probability=max(2,min(98,round(100/(1+math.exp(-((predicted/danger)-.86)*18)))))
    return round(predicted,2),probability,risk_for(predicted,danger),round(slope,3)


def forecast_15_days(current, slope, danger):
    today=datetime.now().astimezone()
    out=[]
    for day in range(1,16):
        decay=0.80**(day-1)
        wave=0.10*math.sin(day/2)
        level=max(0,current+slope*8*day*decay+wave)
        level=round(level,2)
        prob=max(2,min(99,round(100/(1+math.exp(-((level/danger)-.86)*18)))))
        out.append({'date':(today+timedelta(days=day)).strftime('%Y-%m-%d'),'level':level,'probability':prob,'risk':risk_for(level,danger)})
    return out


def advice(risk):
    return {
      'NORMAL':['Continue monitoring official updates.','Keep phone, torch and power bank charged.','Know the nearest safe higher ground or shelter.'],
      'WARNING':['Check FFWC/BWDB and local-authority updates frequently.','Prepare water, dry food, medicines and important documents.','Move valuables and electrical items higher and plan an evacuation route.'],
      'FLOOD':['Avoid unnecessary travel near rivers and fast-moving water.','Move valuables, documents, livestock and essential supplies higher.','Prepare for evacuation if local authorities advise it.'],
      'SEVERE':['Follow official/local-authority instructions immediately.','Move to higher ground or a designated shelter when instructed.','Keep emergency supplies and essential medicines with you.']
    }[risk]


def package_station(key, force=False):
    st=STATIONS[key]
    live=live_for_station(key, force)
    current=float(live.get('current',st['target']))
    danger=float(live.get('danger',st['danger']))
    rows=make_demo_history(key)
    previous=float(rows[-1]['level'])
    pred,prob,risk,slope=predict_24h(current,previous,danger)
    forecast=forecast_15_days(current,slope,danger)
    snap=live_snapshot()
    return {
        'id':key,'name':st['name'],'district':st['district'],'division':st['division'],'river':st['river'],'station':st['station'],
        'current':round(current,2),'predicted':pred,'probability':prob,'risk':risk,'danger':round(danger,2),'lat':st['lat'],'lon':st['lon'],
        'trend_3h_cm':round(slope*100,1),'live':bool(live.get('live')),'source':live.get('source','FFWC' if live.get('live') else 'reference data'),
        'snapshot':bool(live.get('snapshot')),
        'source_url':live.get('source_url','https://ffwc.gov.bd/app/observed-water-level'),'observed_at':live.get('observed_at'),
        'fetched_at':snap.get('fetched_at'),'forecast15':forecast,'day15':forecast[-1]['level'],'day15risk':forecast[-1]['risk']
    }


def build_dashboard(key, force=False):
    st=STATIONS[key]
    live=live_for_station(key, force)
    current=float(live.get('current',st['target']))
    danger=float(live.get('danger',st['danger']))
    rows=make_demo_history(key)
    previous=float(rows[-1]['level'])
    pred,prob,risk,slope=predict_24h(current,previous,danger)
    forecast=forecast_15_days(current,slope,danger)
    hist=rows[-119:] + [{'time':datetime.now().astimezone().strftime('%Y-%m-%d %H:%M:%S'),'level':current,'kind':'FFWC live observation' if live.get('live') else 'Fallback demo reference'}]
    snap=live_snapshot()
    return {
      'station':{**st,'danger':danger,'source':live.get('source'),'source_url':live.get('source_url'),'live':bool(live.get('live')),'snapshot':bool(live.get('snapshot')),'observed_at':live.get('observed_at')},
      'current':round(current,2),'predicted':pred,'probability':prob,'risk':risk,'trend_per_3h':slope,'forecast15':forecast,'history':hist,
      'advice':advice(risk),'fetched_at':snap.get('fetched_at'),'table_date':snap.get('table_date'),
      'live_connected':bool(snap.get('ok')),'live_error':None if snap.get('ok') else LIVE_CACHE.get('error')
    }


def national_summary(force=False):
    zones=[package_station(k,force) for k in STATIONS]
    counts={r:sum(1 for z in zones if z['risk']==r) for r in ['NORMAL','WARNING','FLOOD','SEVERE']}
    rises=sorted(zones,key=lambda z:z['trend_3h_cm'],reverse=True)
    closest=sorted(zones,key=lambda z:(z['current']/z['danger']),reverse=True)
    return {'zones':zones,'counts':counts,'stations':len(zones),'live_stations':sum(z['live'] for z in zones),'top_rising':rises[:4],'closest_to_danger':closest[:4]}

@app.route('/')
def index():
    return render_template('index.html', stations=STATIONS)

@app.route('/api/zones')
def zones():
    return jsonify([package_station(k, request.args.get('force')=='1') for k in STATIONS])

@app.route('/api/dashboard')
def dashboard():
    key=request.args.get('station','mymensingh')
    if key not in STATIONS: key='mymensingh'
    return jsonify(build_dashboard(key, request.args.get('force')=='1'))

@app.route('/api/national')
def national():
    return jsonify(national_summary(request.args.get('force')=='1'))

@app.route('/api/live-refresh')
def live_refresh():
    started = trigger_live_refresh(force=request.args.get('force')=='1')
    snap = live_snapshot()
    return jsonify({'started': started, 'state': LIVE_CACHE.get('state','idle'), 'connected': bool(snap.get('ok')),
                    'fetched_at': snap.get('fetched_at'), 'table_date': snap.get('table_date')})

@app.route('/api/live-status')
def live_status():
    snap=live_snapshot(request.args.get('force')=='1')
    return jsonify({'connected':bool(snap.get('ok')),'source':snap.get('source'),'source_url':snap.get('source_url'),'fetched_at':snap.get('fetched_at'),'table_date':snap.get('table_date'),'cache_seconds':CACHE_SECONDS,'state':LIVE_CACHE.get('state','idle'),'error':None if snap.get('ok') else LIVE_CACHE.get('error')})

@app.route('/api/analytics')
def analytics():
    n=national_summary(request.args.get('force')=='1')
    levels=[z['current'] for z in n['zones']]
    return jsonify({'counts':n['counts'],'avg_level':round(statistics.mean(levels),2),'max_level':max(levels),'min_level':min(levels),'rising':n['top_rising'],'closest':n['closest_to_danger']})

@app.route('/api/report')
def report():
    n=national_summary(request.args.get('force')=='1')
    now=datetime.now().astimezone().strftime('%d %b %Y, %I:%M:%S %p')
    lines=["FLOODGUARD BD — FLOOD SITUATION REPORT","",f"Generated: {now}","Source: FFWC observed-water-level feed where available","","NATIONAL OVERVIEW",f"Stations monitored: {n['stations']}",f"Live stations: {n['live_stations']}",f"Normal: {n['counts']['NORMAL']}",f"Warning: {n['counts']['WARNING']}",f"Flood: {n['counts']['FLOOD']}",f"Severe: {n['counts']['SEVERE']}","","STATION STATUS"]
    for z in n['zones']:
        lines.append(f"{z['name']} | {z['current']:.2f} m | DL {z['danger']:.2f} m | {z['risk']} | {'FFWC LIVE' if z['live'] else 'Fallback reference'}")
    return Response('\n'.join(lines),mimetype='text/plain',headers={'Content-Disposition':'attachment; filename="FloodGuard_BD_Situation_Report.txt"'})

if __name__=='__main__':
    trigger_live_refresh(force=False)
    import os
    port = int(os.environ.get('PORT', '10000'))
    app.run(host='0.0.0.0', port=port, debug=False)
