import re
from datetime import datetime, timezone
import requests

# Public FFWC pages used as best-effort live sources.
FFWC_URLS = [
    "https://ffwc.gov.bd/app/observed-water-level",
    "https://old.ffwc.gov.bd/ffwc_charts/waterlevelobs.php",
]
TIMEOUT = 2.5

def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", str(s).lower())

def _clean_html(text):
    text = re.sub(r"<script.*?</script>", " ", text, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)
    return text

def _parse_table(html, source_url):
    clean = _clean_html(html)
    rows = re.findall(r"<tr[^>]*>(.*?)</tr>", clean, flags=re.S | re.I)
    data = {}
    table_date = None
    for pattern in [
        r"TABLE OF OBSERVED WATER LEVELS\s*:?[ ]*([^<\r\n]+)",
        r"AS OF\s+([^<\r\n]+)",
        r"OBSERVED WATER LEVELS\s*:?[ ]*([^<\r\n]+)",
    ]:
        m = re.search(pattern, html, flags=re.I)
        if m:
            table_date = re.sub(r"\s+", " ", m.group(1)).strip()
            break
    for row in rows:
        cells = re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.S | re.I)
        vals=[re.sub(r"\s+", " ", re.sub(r"<.*?>", " ", c)).strip() for c in cells]
        vals=[v for v in vals if v]
        if len(vals)<4: continue
        river, station = vals[0], vals[1]
        nums=[]
        for v in vals[2:]:
            try: nums.append(float(v.replace(',','')))
            except Exception: pass
        if len(nums)<2: continue
        danger=nums[0]; current=nums[-1]
        if danger<=0 or current<-100 or current>100: continue
        data[(_norm(river),_norm(station))]={
            'river':river,'station':station,'danger':danger,'current':current,
            'source':'FFWC observed water level','source_url':source_url,'observed_at':table_date
        }
    if not data: raise RuntimeError('No usable rows parsed')
    return {'ok':True,'source':'FFWC','source_url':source_url,
            'table_date':table_date,'fetched_at':datetime.now(timezone.utc).isoformat(),'data':data}

def fetch_ffwc_current():
    errors=[]
    for url in FFWC_URLS:
        try:
            r=requests.get(url,timeout=TIMEOUT,headers={'User-Agent':'Mozilla/5.0 FloodGuardBD/3.0'})
            r.raise_for_status()
            return _parse_table(r.text,url)
        except Exception as exc:
            errors.append(f'{url}: {exc}')
    raise RuntimeError('Public FFWC feed unavailable')
