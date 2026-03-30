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
# 1. 提升权限
[ "$(id -u)" -eq 0 ] || { command -v sudo >/dev/null && exec sudo bash "$0" "$@"; echo "Root required"; exit 1; }

# 2. 安装基础依赖
if [ -f /etc/debian_version ]; then
    apt-get update -y >/dev/null 2>&1
    apt-get install -y python3 iputils-ping util-linux sqlite3 >/dev/null 2>&1
elif [ -f /etc/redhat-release ]; then
    yum install -y python3 iputils util-linux sqlite3 >/dev/null 2>&1
elif [ -f /etc/alpine-release ]; then
    apk add python3 iputils util-linux sqlite3 >/dev/null 2>&1
fi

# 3. 写入 Python 脚本
cat > /root/x_fusion_agent.py << "PYTHON_EOF"
import time, json, os, socket, sys, subprocess, re, platform, sqlite3
import urllib.request, urllib.error
import ssl

MANAGER_URL = "__MANAGER_URL__/api/probe/push"
TOKEN = "__TOKEN__"
SERVER_URL = "__SERVER_URL__"

PING_TARGETS = {
"电信": "__PING_CT__",
"联通": "__PING_CU__",
"移动": "__PING_CM__"
}

ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

def get_cpu_model():
    model = "Unknown"
    try:
        try:
            out = subprocess.check_output("lscpu", shell=True).decode()
            for line in out.split("\n"):
                if "Model name:" in line: return line.split(":")[1].strip()
        except: pass
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line: return line.split(":")[1].strip()
                if "Hardware" in line: return line.split(":")[1].strip()
    except: pass
    return model

def get_os_distro():
    try:
        if os.path.exists("/etc/os-release"):
            with open("/etc/os-release") as f:
                for line in f:
                    if line.startswith("PRETTY_NAME="):
                        return line.split("=")[1].strip().strip("\"")
    except: pass
    try: return platform.platform()
    except: return "Linux (Unknown)"

STATIC_CACHE = {
    "cpu_model": get_cpu_model(),
    "arch": platform.machine(),
    "os": get_os_distro(),
    "virt": "Unknown"
}
try:
    v = subprocess.check_output("systemd-detect-virt", shell=True).decode().strip()
    if v and v != "none": STATIC_CACHE["virt"] = v
except: pass

def get_ping(target):
    try:
        ip = target.split("://")[-1].split(":")[0]
        cmd = "ping -c 1 -W 1 " + ip
        res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if res.returncode == 0:
            match = re.search(r"time=([\d.]+)", res.stdout.decode())
            if match: return int(float(match.group(1)))
    except: pass
    return -1

def get_network_bytes():
    r, t = 0, 0
    try:
        with open("/proc/net/dev") as f:
            lines = f.readlines()[2:]
            for l in lines:
                cols = l.split(":")
                if len(cols)<2: continue
                parts = cols[1].split()
                if len(parts)>=9 and cols[0].strip() != "lo":
                    r += int(parts[0])
                    t += int(parts[8])
    except: pass
    return r, t

# 读取 X-UI 数据库 
def get_xui_rows():
    db_path = "/etc/x-ui/x-ui.db"
    if not os.path.exists(db_path): return None
    
    try:
        # 使用 URI 模式打开，mode=ro (只读)，防止锁死数据库影响面板写入
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        cursor = conn.cursor()
        # 查询关键字段，尽可能匹配 API 返回的格式
        cursor.execute("SELECT id, up, down, total, remark, enable, protocol, port, settings, stream_settings, expiry_time, listen FROM inbounds")
        rows = cursor.fetchall()
        
        inbounds = []
        for row in rows:
            # 数据清洗与组装
            node = {
                "id": row[0],
                "up": row[1],
                "down": row[2],
                "total": row[3],
                "remark": row[4],
                "enable": True if row[5] == 1 else False,
                "protocol": row[6],
                "port": row[7],
                "settings": row[8],
                "streamSettings": row[9],
                "expiryTime": row[10],
                "listen": row[11]
            }
            inbounds.append(node)
        conn.close()
        return inbounds
    except:
        return None

def get_info():
    global SERVER_URL
    data = {"token": TOKEN, "static": STATIC_CACHE}
    
    if not SERVER_URL:
        try:
            with urllib.request.urlopen("http://checkip.amazonaws.com", timeout=5, context=ssl_ctx) as r:
                my_ip = r.read().decode().strip()
                SERVER_URL = "http://" + my_ip + ":54322"
        except: pass
    data["server_url"] = SERVER_URL

    try:
        net_in_1, net_out_1 = get_network_bytes()
        with open("/proc/stat") as f:
            fs = [float(x) for x in f.readline().split()[1:5]]
            tot1, idle1 = sum(fs), fs[3]
        
        time.sleep(1)
        
        net_in_2, net_out_2 = get_network_bytes()
        with open("/proc/stat") as f:
            fs = [float(x) for x in f.readline().split()[1:5]]
            tot2, idle2 = sum(fs), fs[3]
            
        data["cpu_usage"] = round((1 - (idle2-idle1)/(tot2-tot1)) * 100, 1)
        data["cpu_cores"] = os.cpu_count() or 1
        
        data["net_speed_in"] = net_in_2 - net_in_1
        data["net_speed_out"] = net_out_2 - net_out_1
        data["net_total_in"] = net_in_2
        data["net_total_out"] = net_out_2

        with open("/proc/loadavg") as f: data["load_1"] = float(f.read().split()[0])
        
        with open("/proc/meminfo") as f:
            m = {}
            for l in f:
                p = l.split()
                if len(p)>=2: m[p[0].rstrip(":")] = int(p[1])
        
        tot = m.get("MemTotal", 1)
        avail = m.get("MemAvailable", m.get("MemFree", 0))
        data["mem_total"] = round(tot/1024/1024, 2)
        data["mem_usage"] = round(((tot-avail)/tot)*100, 1)
        data["swap_total"] = round(m.get("SwapTotal", 0)/1024/1024, 2)
        data["swap_free"] = round(m.get("SwapFree", 0)/1024/1024, 2)

        st = os.statvfs("/")
        data["disk_total"] = round((st.f_blocks * st.f_frsize)/1024/1024/1024, 2)
        free = st.f_bavail * st.f_frsize
        total = st.f_blocks * st.f_frsize
        data["disk_usage"] = round(((total-free)/total)*100, 1)

        with open("/proc/uptime") as f: u = float(f.read().split()[0])
        d = int(u // 86400); h = int((u % 86400) // 3600); m = int((u % 3600) // 60)
        data["uptime"] = "%d天 %d时 %d分" % (d, h, m)

        data["pings"] = {k: get_ping(v) for k, v in PING_TARGETS.items()}
        
        xui = get_xui_rows()
        if xui is not None:
            data["xui_data"] = xui

    except: pass
    return data

def push():
    while True:
        try:
            js = json.dumps(get_info()).encode("utf-8")
            req = urllib.request.Request(MANAGER_URL, data=js, headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=10, context=ssl_ctx) as r: pass
        except: pass
        time.sleep(5)

if __name__ == "__main__":
    push()
PYTHON_EOF

# 4. 创建服务
cat > /etc/systemd/system/x-fusion-agent.service << SERVICE_EOF
[Unit]
Description=X-Fusion Probe Agent
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 /root/x_fusion_agent.py
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SERVICE_EOF

# 5. 启动
systemctl daemon-reload
systemctl enable x-fusion-agent
systemctl restart x-fusion-agent
exit 0
'
"""
