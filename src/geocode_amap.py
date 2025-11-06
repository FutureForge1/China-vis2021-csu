import sqlite3
import os
import requests
import time
from typing import Optional, Dict
from .config import AMAP_CACHE_DB, AMAP_KEY

# 采用高德地图API逆地图编码，已弃用等待未来有机会使用

def _ensure_db(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30)
    cur = conn.cursor()
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS amap_cache (
            id INTEGER PRIMARY KEY,
            lat5 REAL,
            lon5 REAL,
            province TEXT,
            city TEXT,
            formatted_address TEXT,
            ts INTEGER,
            UNIQUE(lat5, lon5)
        )
        """
    )
    conn.commit()
    return conn


def _round5(v: float) -> float:
    return round(float(v), 5)


def lookup_cache(conn: sqlite3.Connection, lat: float, lon: float) -> Optional[Dict]:
    lat5 = _round5(lat)
    lon5 = _round5(lon)
    cur = conn.cursor()
    cur.execute("SELECT province, city, formatted_address, ts FROM amap_cache WHERE lat5=? AND lon5=?", (lat5, lon5))
    row = cur.fetchone()
    if row:
        return {'province': row[0], 'city': row[1], 'formatted_address': row[2], 'ts': row[3]}
    return None


def save_cache(conn: sqlite3.Connection, lat: float, lon: float, province: str, city: str, formatted: str):
    lat5 = _round5(lat)
    lon5 = _round5(lon)
    cur = conn.cursor()
    ts = int(time.time())
    try:
        cur.execute("INSERT OR REPLACE INTO amap_cache (lat5, lon5, province, city, formatted_address, ts) VALUES (?, ?, ?, ?, ?, ?)",
                    (lat5, lon5, province, city, formatted, ts))
        conn.commit()
    except Exception:
        conn.rollback()


def reverse_geocode_once(lat: float, lon: float, key: Optional[str] = None, timeout: int = 5) -> Dict:
    """Call AMap reverse geocode API for a single coord. Returns dict with province/city/formatted_address.
    May raise requests exceptions on network failures.
    """
    if key is None:
        key = AMAP_KEY
    url = 'https://restapi.amap.com/v3/geocode/regeo'
    params = {
        'key': key,
        'location': f'{lon},{lat}',
        'extensions': 'base',
        'radius': 100,
        'batch': 'false',
        'roadlevel': 0
    }
    # Use a Session that ignores environment proxies (trust_env=False)
    # This prevents issues when a system/HTTP proxy interferes with TLS SNI
    # and raises "check_hostname requires server_hostname" as seen on some setups.
    session = requests.Session()
    session.trust_env = False
    r = session.get(url, params=params, timeout=timeout)
    r.raise_for_status()
    data = r.json()
    if data.get('status') != '1':
        raise RuntimeError(f"AMap API error: {data}")
    regeocode = data.get('regeocode') or {}
    address_component = regeocode.get('addressComponent') or {}
    province = address_component.get('province') or ''
    city = address_component.get('city') or ''
    # For municipalities city may be empty; use province in that case
    if isinstance(city, list):
        city = city[0] if city else ''
    if not city:
        # some responses put city as '', but have 'province' and 'district'
        city = address_component.get('district') or province
    formatted = regeocode.get('formatted_address') or ''
    return {'province': province, 'city': city, 'formatted_address': formatted}


def get_or_query(lat: float, lon: float, key: Optional[str] = None, cache_db: Optional[str] = None, retry: int = 3, backoff: float = 0.5) -> Dict:
    """Lookup cache then query AMap if missing. Returns dict with province/city/formatted_address and cached flag."""
    if cache_db is None:
        cache_db = AMAP_CACHE_DB
    conn = _ensure_db(cache_db)
    try:
        row = lookup_cache(conn, lat, lon)
        if row:
            row['cached'] = True
            return row

        last_exc = None
        for attempt in range(retry):
            try:
                res = reverse_geocode_once(lat, lon, key=key)
                save_cache(conn, lat, lon, res.get('province',''), res.get('city',''), res.get('formatted_address',''))
                res['cached'] = False
                return res
            except Exception as e:
                last_exc = e
                time.sleep(backoff * (2 ** attempt))
        raise last_exc
    finally:
        try:
            conn.close()
        except Exception:
            pass
