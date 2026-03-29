import os
from pathlib import Path


def _is_docker_runtime() -> bool:
    if os.path.exists('/.dockerenv'):
        return True
    try:
        with open('/proc/1/cgroup', 'r', encoding='utf-8') as f:
            content = f.read()
        return 'docker' in content or 'containerd' in content or 'kubepods' in content
    except Exception:
        return False


def _resolve_data_dir() -> str:
    docker_data_dir = '/app/data'
    if _is_docker_runtime():
        return docker_data_dir
    if os.path.isdir('/app') and os.access('/app', os.W_OK):
        return docker_data_dir
    project_root = Path(__file__).resolve().parent.parent.parent
    return str(project_root / 'data')


DATA_DIR = _resolve_data_dir()
CONFIG_FILE = os.path.join(DATA_DIR, 'servers.json')
SUBS_FILE = os.path.join(DATA_DIR, 'subscriptions.json')
NODES_CACHE_FILE = os.path.join(DATA_DIR, 'nodes_cache.json')
ADMIN_CONFIG_FILE = os.path.join(DATA_DIR, 'admin_config.json')
GLOBAL_SSH_KEY_FILE = os.path.join(DATA_DIR, 'global_ssh_key')

AUTO_REGISTER_SECRET = os.getenv('XUI_SECRET_KEY', 'sijuly_secret_key_default')
ADMIN_USER = os.getenv('XUI_USERNAME', 'admin')
ADMIN_PASS = os.getenv('XUI_PASSWORD', 'admin')

SYNC_COOLDOWN_SECONDS = 300
PAGE_SIZE = 30
SYNC_COOLDOWN = 1800

AUTO_COUNTRY_MAP = {
    '🇨🇳': '🇨🇳 中国', 'China': '🇨🇳 中国', '中国': '🇨🇳 中国', 'CN': '🇨🇳 中国', 'PRC': '🇨🇳 中国',
    '🇭🇰': '🇭🇰 香港', 'HK': '🇭🇰 香港', 'Hong Kong': '🇭🇰 香港', 'Hong Kong SAR': '🇭🇰 香港',
    '🇲🇴': '🇲🇴 澳门', 'MO': '🇲🇴 澳门', 'Macau': '🇲🇴 澳门', 'Macao': '🇲🇴 澳门',
    '🇹🇼': '🇹🇼 台湾', 'TW': '🇹🇼 台湾', 'Taiwan': '🇹🇼 台湾', 'Republic of China': '🇹🇼 台湾',
    '🇯🇵': '🇯🇵 日本', 'JP': '🇯🇵 日本', 'Japan': '🇯🇵 日本', 'Tokyo': '🇯🇵 日本', 'Osaka': '🇯🇵 日本',
    '🇸🇬': '🇸🇬 新加坡', 'SG': '🇸🇬 新加坡', 'Singapore': '🇸🇬 新加坡',
    '🇰🇷': '🇰🇷 韩国', 'KR': '🇰🇷 韩国', 'Korea': '🇰🇷 韩国', 'South Korea': '🇰🇷 韩国', 'Republic of Korea': '🇰🇷 韩国', '韩国': '🇰🇷 韩国', 'Seoul': '🇰🇷 韩国',
    '🇺🇸': '🇺🇸 美国', 'US': '🇺🇸 美国', 'USA': '🇺🇸 美国', 'United States': '🇺🇸 美国', 'America': '🇺🇸 美国',
    '🇬🇧': '🇬🇧 英国', 'UK': '🇬🇧 英国', 'GB': '🇬🇧 英国', 'United Kingdom': '🇬🇧 英国', 'London': '🇬🇧 英国',
    '🇩🇪': '🇩🇪 德国', 'DE': '🇩🇪 德国', 'Germany': '🇩🇪 德国', 'Frankfurt': '🇩🇪 德国',
}

LOCATION_COORDS = {
    '🇨🇳': (35.86, 104.19), 'China': (35.86, 104.19), '中国': (35.86, 104.19),
    '🇭🇰': (22.31, 114.16), 'HK': (22.31, 114.16), 'Hong Kong': (22.31, 114.16), '香港': (22.31, 114.16),
    '🇹🇼': (23.69, 120.96), 'TW': (23.69, 120.96), 'Taiwan': (23.69, 120.96), '台湾': (23.69, 120.96),
    '🇯🇵': (36.20, 138.25), 'JP': (36.20, 138.25), 'Japan': (36.20, 138.25), '日本': (36.20, 138.25),
    'Tokyo': (35.68, 139.76), '东京': (35.68, 139.76), 'Osaka': (34.69, 135.50), '大阪': (34.69, 135.50),
    '🇸🇬': (1.35, 103.81), 'SG': (1.35, 103.81), 'Singapore': (1.35, 103.81), '新加坡': (1.35, 103.81),
    '🇰🇷': (35.90, 127.76), 'KR': (35.90, 127.76), 'Korea': (35.90, 127.76), '韩国': (35.90, 127.76),
    'Seoul': (37.56, 126.97), '首尔': (37.56, 126.97),
    '🇺🇸': (37.09, -95.71), 'US': (37.09, -95.71), 'USA': (37.09, -95.71), 'United States': (37.09, -95.71), '美国': (37.09, -95.71),
    '🇬🇧': (55.37, -3.43), 'UK': (55.37, -3.43), 'United Kingdom': (55.37, -3.43), '英国': (55.37, -3.43),
    '🇩🇪': (51.16, 10.45), 'DE': (51.16, 10.45), 'Germany': (51.16, 10.45), '德国': (51.16, 10.45),
}

MATCH_MAP = {
    '🇨🇱': 'Chile', 'CHILE': 'Chile',
    '🇧🇷': 'Brazil', 'BRAZIL': 'Brazil', 'BRA': 'Brazil', 'SAO PAULO': 'Brazil',
    '🇦🇷': 'Argentina', 'ARGENTINA': 'Argentina', 'ARG': 'Argentina',
    '🇨🇴': 'Colombia', 'COLOMBIA': 'Colombia', 'COL': 'Colombia',
    '🇵🇪': 'Peru', 'PERU': 'Peru',
    '🇺🇸': 'United States', 'USA': 'United States', 'UNITED STATES': 'United States', 'AMERICA': 'United States',
    '🇨🇦': 'Canada', 'CANADA': 'Canada', 'CAN': 'Canada',
    '🇲🇽': 'Mexico', 'MEXICO': 'Mexico', 'MEX': 'Mexico',
    '🇬🇧': 'United Kingdom', 'UK': 'United Kingdom', 'GB': 'United Kingdom', 'UNITED KINGDOM': 'United Kingdom', 'LONDON': 'United Kingdom',
    '🇩🇪': 'Germany', 'GERMANY': 'Germany', 'DEU': 'Germany', 'FRANKFURT': 'Germany',
}

XHTTP_INSTALL_SCRIPT_TEMPLATE = r"""
#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
export PATH=$PATH:/usr/local/bin

sed -i 's/\r$//' "$0"

if [ -f /etc/debian_version ]; then
    apt-get update -y >/dev/null 2>&1
    apt-get install -y net-tools lsof curl unzip jq uuid-runtime openssl psmisc dnsutils >/dev/null 2>&1
elif [ -f /etc/redhat-release ]; then
    yum install -y net-tools lsof curl unzip jq psmisc bind-utils >/dev/null 2>&1
fi

log() { echo -e "\033[32m[DEBUG]\033[0m $1"; }
err() { echo -e "\033[31m[ERROR]\033[0m $1"; }

DOMAIN="$1"
if [ -z "$DOMAIN" ]; then err "域名参数缺失"; exit 1; fi

log "========== 开始部署 XHTTP (V76 稳定版) =========="
log "目标域名: $DOMAIN"
"""

HYSTERIA_INSTALL_SCRIPT_TEMPLATE = r"""
#!/bin/bash
PASSWORD="{password}"
SNI="{sni}"
ENABLE_PORT_HOPPING="{enable_hopping}"
PORT_RANGE_START="{port_range_start}"
PORT_RANGE_END="{port_range_end}"
"""

SNELL_INSTALL_SCRIPT_TEMPLATE = r"""
#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
PORT="{port}"
PSK="{psk}"
TARGET_IP="{target_ip}"
"""

PROBE_INSTALL_SCRIPT = r"""
bash -c '
[ "$(id -u)" -eq 0 ] || { command -v sudo >/dev/null && exec sudo bash "$0" "$@"; echo "Root required"; exit 1; }
'
"""
