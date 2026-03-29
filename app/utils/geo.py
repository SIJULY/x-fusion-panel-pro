import requests
from nicegui import run

from app.core.config import AUTO_COUNTRY_MAP, LOCATION_COORDS, MATCH_MAP
from app.core.state import IP_GEO_CACHE


def fetch_geo_from_ip(host):
    try:
        clean_host = host.split('://')[-1].split(':')[0]
        if clean_host.startswith('192.168.') or clean_host.startswith('10.') or clean_host == '127.0.0.1':
            return None
        if clean_host in IP_GEO_CACHE:
            return IP_GEO_CACHE[clean_host]

        with requests.Session() as s:
            url = f"http://ip-api.com/json/{clean_host}?lang=zh-CN&fields=status,lat,lon,country,regionName,city"
            r = s.get(url, timeout=3)
            if r.status_code == 200:
                data = r.json()
                if data.get('status') == 'success':
                    result = (data['lat'], data['lon'], data['country'], data.get('regionName', '未知'))
                    IP_GEO_CACHE[clean_host] = result
                    return result
    except:
        pass
    return None


def get_coords_from_name(name):
    for k in sorted(LOCATION_COORDS.keys(), key=len, reverse=True):
        if k in name:
            return LOCATION_COORDS[k]
    return None


def get_flag_for_country(country_name):
    if not country_name:
        return "🏳️ 未知"

    for k, v in AUTO_COUNTRY_MAP.items():
        if k.upper() == country_name.upper() or k in country_name:
            return v

    for v in AUTO_COUNTRY_MAP.values():
        if country_name in v:
            return v

    return f"🏳️ {country_name}"


async def auto_prepend_flag(name, url):
    """
    检查名字是否已经包含任意已知国旗。
    - 如果包含：直接返回原名（尊重用户填写或面板自带的国旗）。
    - 如果不包含：根据 IP 归属地自动添加。
    """
    if not name:
        return name

    for v in AUTO_COUNTRY_MAP.values():
        flag_icon = v.split(' ')[0]
        if flag_icon in name:
            return name

    try:
        geo_info = await run.io_bound(fetch_geo_from_ip, url)
        if not geo_info:
            return name

        country_name = geo_info[2]
        flag_group = get_flag_for_country(country_name)
        flag_icon = flag_group.split(' ')[0]

        if flag_icon in name:
            return name

        return f"{flag_icon} {name}"
    except Exception:
        return name


def detect_country_group(name, server_config=None):
    if server_config:
        saved_group = server_config.get('group')
        if saved_group and saved_group.strip() and saved_group not in ['默认分组', '自动注册', '未分组', '自动导入', '🏳️ 其他地区', '其他地区']:
            for v in AUTO_COUNTRY_MAP.values():
                if saved_group in v or v in saved_group:
                    return v
            return saved_group

    name_upper = name.upper()
    sorted_keys = sorted(AUTO_COUNTRY_MAP.keys(), key=len, reverse=True)

    import re

    for key in sorted_keys:
        val = AUTO_COUNTRY_MAP[key]

        if key in name_upper:
            if len(key) <= 3 and key.isalpha():
                pattern = r'(?<![A-Z0-9])' + re.escape(key) + r'(?![A-Z0-9])'
                if re.search(pattern, name_upper):
                    return val
            else:
                return val

    if server_config and server_config.get('_detected_region'):
        detected = server_config['_detected_region'].upper()
        for key, val in AUTO_COUNTRY_MAP.items():
            if key.upper() == detected or key.upper() in detected:
                return val

    return '🏳️ 其他地区'


def get_echarts_region_name(name_raw):
    if not name_raw:
        return None
    name = name_raw.upper()
    sorted_keys = sorted(MATCH_MAP.keys(), key=len, reverse=True)
    for key in sorted_keys:
        if key in name:
            return MATCH_MAP[key]
    return None
