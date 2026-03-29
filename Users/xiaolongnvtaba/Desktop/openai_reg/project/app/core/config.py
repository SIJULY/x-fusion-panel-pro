import os


DATA_DIR = '/app/data'

CONFIG_FILE = os.path.join(DATA_DIR, 'servers.json')
SUBS_FILE = os.path.join(DATA_DIR, 'subscriptions.json')
NODES_CACHE_FILE = os.path.join(DATA_DIR, 'nodes_cache.json')
ADMIN_CONFIG_FILE = os.path.join(DATA_DIR, 'admin_config.json')
GLOBAL_SSH_KEY_FILE = os.path.join(DATA_DIR, 'global_ssh_key')

AUTO_REGISTER_SECRET = os.getenv('XUI_SECRET_KEY', 'sijuly_secret_key_default')
ADMIN_USER = os.getenv('XUI_USERNAME', 'admin')
ADMIN_PASS = os.getenv('XUI_PASSWORD', 'admin')

LOCATION_COORDS = {
    '🇨🇳': (35.86, 104.19), 'China': (35.86, 104.19), '中国': (35.86, 104.19),
    '🇭🇰': (22.31, 114.16), 'HK': (22.31, 114.16), 'Hong Kong': (22.31, 114.16), '香港': (22.31, 114.16),
    '🇹🇼': (23.69, 120.96), 'TW': (23.69, 120.96), 'Taiwan': (23.69, 120.96), '台湾': (23.69, 120.96),
    '🇯🇵': (36.20, 138.25), 'JP': (36.20, 138.25), 'Japan': (36.20, 138.25), '日本': (36.20, 138.25),
    'Tokyo': (35.68, 139.76), '东京': (35.68, 139.76), 'Osaka': (34.69, 135.50), '大阪': (34.69, 135.50),
    '🇸🇬': (1.35, 103.81), 'SG': (1.35, 103.81), 'Singapore': (1.35, 103.81), '新加坡': (1.35, 103.81),
    '🇰🇷': (35.90, 127.76), 'KR': (35.90, 127.76), 'Korea': (35.90, 127.76), '韩国': (35.90, 127.76),
    'Seoul': (37.56, 126.97), '首尔': (37.56, 126.97),
    '🇮🇳': (20.59, 78.96), 'IN': (20.59, 78.96), 'India': (20.59, 78.96), '印度': (20.59, 78.96),
    '🇮🇩': (-0.78, 113.92), 'ID': (-0.78, 113.92), 'Indonesia': (-0.78, 113.92), '印尼': (-0.78, 113.92),
    '🇲🇾': (4.21, 101.97), 'MY': (4.21, 101.97), 'Malaysia': (4.21, 101.97), '马来西亚': (4.21, 101.97),
    '🇹🇭': (15.87, 100.99), 'TH': (15.87, 100.99), 'Thailand': (15.87, 100.99), '泰国': (15.87, 100.99),
    'Bangkok': (13.75, 100.50), '曼谷': (13.75, 100.50),
    '🇻🇳': (14.05, 108.27), 'VN': (14.05, 108.27), 'Vietnam': (14.05, 108.27), '越南': (14.05, 108.27),
    '🇵🇭': (12.87, 121.77), 'PH': (12.87, 121.77), 'Philippines': (12.87, 121.77), '菲律宾': (12.87, 121.77),
    '🇮🇱': (31.04, 34.85), 'IL': (31.04, 34.85), 'Israel': (31.04, 34.85), '以色列': (31.04, 34.85),
    '🇹🇷': (38.96, 35.24), 'TR': (38.96, 35.24), 'Turkey': (38.96, 35.24), '土耳其': (38.96, 35.24),
    '🇦🇪': (23.42, 53.84), 'AE': (23.42, 53.84), 'UAE': (23.42, 53.84), '阿联酋': (23.42, 53.84),
    'Dubai': (25.20, 55.27), '迪拜': (25.20, 55.27),
    '🇺🇸': (37.09, -95.71), 'US': (37.09, -95.71), 'USA': (37.09, -95.71), 'United States': (37.09, -95.71), '美国': (37.09, -95.71),
    'San Jose': (37.33, -121.88), '圣何塞': (37.33, -121.88), 'Los Angeles': (34.05, -118.24), '洛杉矶': (34.05, -118.24),
    'Phoenix': (33.44, -112.07), '凤凰城': (33.44, -112.07),
    '🇨🇦': (56.13, -106.34), 'CA': (56.13, -106.34), 'Canada': (56.13, -106.34), '加拿大': (56.13, -106.34),
    '🇧🇷': (-14.23, -51.92), 'BR': (-14.23, -51.92), 'Brazil': (-14.23, -51.92), '巴西': (-14.23, -51.92),
    '🇲🇽': (23.63, -102.55), 'MX': (23.63, -102.55), 'Mexico': (23.63, -102.55), '墨西哥': (23.63, -102.55),
    '🇨🇱': (-35.67, -71.54), 'CL': (-35.67, -71.54), 'Chile': (-35.67, -71.54), '智利': (-35.67, -71.54),
    '🇦🇷': (-38.41, -63.61), 'AR': (-38.41, -63.61), 'Argentina': (-38.41, -63.61), '阿根廷': (-38.41, -63.61),
    '🇬🇧': (55.37, -3.43), 'UK': (55.37, -3.43), 'United Kingdom': (55.37, -3.43), '英国': (55.37, -3.43),
    'London': (51.50, -0.12), '伦敦': (51.50, -0.12),
    '🇩🇪': (51.16, 10.45), 'DE': (51.16, 10.45), 'Germany': (51.16, 10.45), '德国': (51.16, 10.45),
    'Frankfurt': (50.11, 8.68), '法兰克福': (50.11, 8.68),
    '🇫🇷': (46.22, 2.21), 'FR': (46.22, 2.21), 'France': (46.22, 2.21), '法国': (46.22, 2.21),
    'Paris': (48.85, 2.35), '巴黎': (48.85, 2.35),
    '🇳🇱': (52.13, 5.29), 'NL': (52.13, 5.29), 'Netherlands': (52.13, 5.29), '荷兰': (52.13, 5.29),
    'Amsterdam': (52.36, 4.90), '阿姆斯特丹': (52.36, 4.90),
    '🇷🇺': (61.52, 105.31), 'RU': (61.52, 105.31), 'Russia': (61.52, 105.31), '俄罗斯': (61.52, 105.31),
    'Moscow': (55.75, 37.61), '莫斯科': (55.75, 37.61),
    '🇮🇹': (41.87, 12.56), 'IT': (41.87, 12.56), 'Italy': (41.87, 12.56), '意大利': (41.87, 12.56),
    'Milan': (45.46, 9.19), '米兰': (45.46, 9.19),
    '🇪🇸': (40.46, -3.74), 'ES': (40.46, -3.74), 'Spain': (40.46, -3.74), '西班牙': (40.46, -3.74),
    'Madrid': (40.41, -3.70), '马德里': (40.41, -3.70),
    '🇸🇪': (60.12, 18.64), 'SE': (60.12, 18.64), 'Sweden': (60.12, 18.64), '瑞典': (60.12, 18.64),
    'Stockholm': (59.32, 18.06), '斯德哥尔摩': (59.32, 18.06),
    '🇨🇭': (46.81, 8.22), 'CH': (46.81, 8.22), 'Switzerland': (46.81, 8.22), '瑞士': (46.81, 8.22),
    'Zurich': (47.37, 8.54), '苏黎世': (47.37, 8.54),
    '🇦🇺': (-25.27, 133.77), 'AU': (-25.27, 133.77), 'Australia': (-25.27, 133.77), '澳大利亚': (-25.27, 133.77), '澳洲': (-25.27, 133.77),
    'Sydney': (-33.86, 151.20), '悉尼': (-33.86, 151.20),
    '🇿🇦': (-30.55, 22.93), 'ZA': (-30.55, 22.93), 'South Africa': (-30.55, 22.93), '南非': (-30.55, 22.93),
    'Johannesburg': (-26.20, 28.04), '约翰内斯堡': (-26.20, 28.04),
}

GLOBAL_SSH_KEY_FILE = 'data/global_ssh_key'

XHTTP_INSTALL_SCRIPT_TEMPLATE = r"""
#!/bin/bash
export DEBIAN_FRONTEND=noninteractive
export PATH=$PATH:/usr/local/bin

# 0. 自我清洗 (防止 Windows 换行符 \r 导致脚本执行异常)
sed -i 's/\r$//' "$0"

# 1. 基础环境检查与依赖安装
if [ -f /etc/debian_version ]; then
    apt-get update -y >/dev/null 2>&1
    apt-get install -y net-tools lsof curl unzip jq uuid-runtime openssl psmisc dnsutils >/dev/null 2>&1
elif [ -f /etc/redhat-release ]; then
    yum install -y net-tools lsof curl unzip jq psmisc bind-utils >/dev/null 2>&1
fi

# 定义日志
log() { echo -e "\033[32m[DEBUG]\033[0m $1"; }
err() { echo -e "\033[31m[ERROR]\033[0m $1"; }

DOMAIN="$1"
if [ -z "$DOMAIN" ]; then err "域名参数缺失"; exit 1; fi

log "========== 开始部署 XHTTP (V76 稳定版) =========="
log "目标域名: $DOMAIN"

# 2. 端口强制清理 (霸道模式)
if netstat -tlpn | grep -q ":80 "; then
    log "⚠️ 清理 80 端口..."
    fuser -k 80/tcp >/dev/null 2>&1; killall -9 nginx >/dev/null 2>&1; killall -9 xray >/dev/null 2>&1
    sleep 1
fi
if netstat -tlpn | grep -q ":443 "; then
    log "⚠️ 清理 443 端口..."
    fuser -k 443/tcp >/dev/null 2>&1
    sleep 1
fi

PORT_REALITY=443
PORT_XHTTP=80

# 3. 安装/更新 Xray
log "安装最新版 Xray..."
xray_bin="/usr/local/bin/xray"
rm -f "$xray_bin"
arch=$(uname -m); case "$arch" in x86_64) a="64";; aarch64) a="arm64-v8a";; esac
curl -fsSL https://github.com/XTLS/Xray-core/releases/latest/download/Xray-linux-${a}.zip -o /tmp/xray.zip
unzip -qo /tmp/xray.zip -d /tmp/xray
install -m 755 /tmp/xray/xray "$xray_bin"

# 4. 生成密钥与ID
KEYS=$($xray_bin x25519)
PRI_KEY=$(echo "$KEYS" | grep -i "Private" | awk '{print $NF}')
PUB_KEY=$(echo "$KEYS" | grep -i "Public" | awk '{print $NF}')
[ -z "$PUB_KEY" ] && { PRI_KEY=$(echo "$KEYS" | head -n1 | awk '{print $NF}'); PUB_KEY=$(echo "$KEYS" | tail -n1 | awk '{print $NF}'); }

UUID_XHTTP=$(cat /proc/sys/kernel/random/uuid)
UUID_REALITY=$(cat /proc/sys/kernel/random/uuid)
XHTTP_PATH="/$(echo "$UUID_XHTTP" | cut -d- -f1 | tr -d '\n')"
SHORT_ID=$(openssl rand -hex 4)

REALITY_SNI="www.icloud.com"
YOUXUAN_DOMAIN="www.visa.com.hk"

mkdir -p /usr/local/etc/xray
CONFIG_FILE="/usr/local/etc/xray/config.json"

# 5. 写入配置文件 (使用 EOF 块，避免转义错误)
cat > $CONFIG_FILE <<EOF
{
  "log": { "loglevel": "warning" },
  "inbounds": [
    {
      "port": $PORT_XHTTP,
      "protocol": "vless",
      "settings": { "clients": [{ "id": "$UUID_XHTTP" }], "decryption": "none" },
      "streamSettings": { "network": "xhttp", "security": "none", "xhttpSettings": { "path": "$XHTTP_PATH", "mode": "auto" } }
    },
    {
      "port": $PORT_REALITY,
      "protocol": "vless",
      "settings": {
        "clients": [{ "id": "$UUID_REALITY", "flow": "xtls-rprx-vision" }],
        "decryption": "none",
        "fallbacks": [{ "dest": $PORT_XHTTP }]
      },
      "streamSettings": {
        "network": "tcp",
        "security": "reality",
        "realitySettings": { "privateKey": "$PRI_KEY", "serverNames": ["$REALITY_SNI"], "shortIds": ["$SHORT_ID"], "target": "$REALITY_SNI:443" }
      }
    }
  ],
  "outbounds": [{ "protocol": "freedom" }]
}
EOF

# 6. 启动服务
cat > /etc/systemd/system/xray.service <<EOF
[Unit]
Description=Xray Service
After=network.target
[Service]
ExecStart=$xray_bin run -c $CONFIG_FILE
Restart=on-failure
LimitNOFILE=1048576
[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable xray >/dev/null 2>&1
systemctl restart xray
sleep 2

# 7. 检查 DNS (诊断)
log "正在检查域名解析: $DOMAIN"
nslookup $DOMAIN 8.8.8.8 >/dev/null 2>&1
if [ $? -ne 0 ]; then
    log "⚠️ 警告: 域名 $DOMAIN 尚未在全球 DNS 生效，连接可能会失败。请稍等几分钟。"
else
    log "✅ 域名解析正常。"
fi

# 8. 生成链接 (JSON 构造优化)
VPS_IP=$(curl -fsSL https://api.ipify.org)

# 使用 cat 生成 JSON，避免 Python 字符串转义干扰
EXTRA_JSON_RAW=$(cat <<EOF
{
  "downloadSettings": {
    "address": "$VPS_IP",
    "port": $PORT_REALITY,
    "network": "xhttp",
    "xhttpSettings": { "path": "$XHTTP_PATH", "mode": "auto" },
    "security": "reality",
    "realitySettings": {
      "serverName": "$REALITY_SNI",
      "fingerprint": "chrome",
      "show": false,
      "publicKey": "$PUB_KEY",
      "shortId": "$SHORT_ID",
      "spiderX": "/",
      "mldsa65Verify": ""
    }
  }
}
EOF
)

# 压缩并编码 JSON
ENC_EXTRA=$(echo "$EXTRA_JSON_RAW" | jq -c . | jq -sRr @uri)
ENC_PATH=$(printf '%s' "$XHTTP_PATH" | jq -sRr @uri)

LINK="vless://${UUID_XHTTP}@${YOUXUAN_DOMAIN}:443?encryption=none&security=tls&sni=${DOMAIN}&type=xhttp&host=${DOMAIN}&path=${ENC_PATH}&mode=auto&extra=${ENC_EXTRA}#XHTTP-Reality"

echo "DEPLOY_SUCCESS_LINK: $LINK"
"""

XHTTP_UNINSTALL_SCRIPT = r"""
#!/bin/bash
# 1. 停止服务
systemctl stop xray
systemctl disable xray

# 2. 删除服务文件
rm -f /etc/systemd/system/xray.service
systemctl daemon-reload

# 3. 删除配置文件 (保留 bin 文件以防 X-UI 共用)
rm -rf /usr/local/etc/xray

echo "Xray Service Uninstalled (Binary kept safe)"
"""

HYSTERIA_INSTALL_SCRIPT_TEMPLATE = r"""
#!/bin/bash
# 1. 接收参数
PASSWORD="{password}"
SNI="{sni}"
ENABLE_PORT_HOPPING="{enable_hopping}"
PORT_RANGE_START="{port_range_start}"
PORT_RANGE_END="{port_range_end}"

# 2. 环境清理与依赖安装 (修复核心：同时安装 iptables 和 net-tools)
if [ -f /etc/debian_version ]; then
    apt-get update -y
    # net-tools 包含 netstat，iptables 用于端口跳跃
    apt-get install -y iptables net-tools
elif [ -f /etc/redhat-release ]; then
    yum install -y iptables net-tools
fi

systemctl stop hysteria-server.service 2>/dev/null
rm -rf /etc/hysteria
bash <(curl -fsSL https://get.hy2.sh/)

# 3. 证书生成 (自签)
mkdir -p /etc/hysteria
openssl req -x509 -nodes -newkey ec:<(openssl ecparam -name prime256v1) \
  -keyout /etc/hysteria/server.key \
  -out /etc/hysteria/server.crt \
  -subj "/CN=$SNI" \
  -days 3650
chown hysteria /etc/hysteria/server.key
chown hysteria /etc/hysteria/server.crt

# 4. 端口检测 (现在有了 net-tools，这里就不会报错了)
HY2_PORT=443
if netstat -ulpn | grep -q ":443 "; then
    echo "⚠️ UDP 443 占用，切换至 8443"
    HY2_PORT=8443
fi

# 5. 写入配置
cat << EOF > /etc/hysteria/config.yaml
listen: :$HY2_PORT
tls:
  cert: /etc/hysteria/server.crt
  key: /etc/hysteria/server.key
auth:
  type: password
  password: $PASSWORD
masquerade:
  type: proxy
  proxy:
    url: https://$SNI
    rewriteHost: true
quic:
  initStreamReceiveWindow: 26843545
  maxStreamReceiveWindow: 26843545
  initConnReceiveWindow: 67108864
  maxConnReceiveWindow: 67108864
EOF

# 6. 端口跳跃 (iptables 转发)
if [ "$ENABLE_PORT_HOPPING" == "true" ]; then
    # 清理旧规则
    iptables -t nat -D PREROUTING -p udp --dport $PORT_RANGE_START:$PORT_RANGE_END -j REDIRECT --to-ports $HY2_PORT 2>/dev/null || true
    # 添加新规则 (不限制网卡，强制生效)
    iptables -t nat -A PREROUTING -p udp --dport $PORT_RANGE_START:$PORT_RANGE_END -j REDIRECT --to-ports $HY2_PORT
    
    mkdir -p /etc/iptables
    if command -v iptables-save >/dev/null; then
        iptables-save > /etc/iptables/rules.v4
    fi
fi

# 7. 启动
systemctl enable --now hysteria-server.service
sleep 2

# 8. 输出链接
if systemctl is-active --quiet hysteria-server.service; then
    PUBLIC_IP=$(curl -s https://api.ipify.org)
    
    CLIENT_PORT=$HY2_PORT
    MPORT_PARAM=""
    
    if [ "$ENABLE_PORT_HOPPING" == "true" ]; then
        if command -v shuf > /dev/null; then
            CLIENT_PORT=$(shuf -i $PORT_RANGE_START-$PORT_RANGE_END -n 1)
        else
            RANGE=$(($PORT_RANGE_END - $PORT_RANGE_START + 1))
            CLIENT_PORT=$(($PORT_RANGE_START + $RANDOM % $RANGE))
        fi
        MPORT_PARAM="&mport=$PORT_RANGE_START-$PORT_RANGE_END"
    fi

    LINK="hy2://$PASSWORD@$PUBLIC_IP:$CLIENT_PORT?peer=$SNI&insecure=1&sni=$SNI$MPORT_PARAM#Hy2-Node"
    echo "HYSTERIA_DEPLOY_SUCCESS_LINK: $LINK"
else
    echo "HYSTERIA_DEPLOY_FAILED"
fi
"""

SNELL_INSTALL_SCRIPT_TEMPLATE = r"""
#!/bin/bash
export DEBIAN_FRONTEND=noninteractive

# 接收参数
PORT="{port}"
PSK="{psk}"
TARGET_IP="{target_ip}"

# 1. 安装基础依赖
if [ -f /etc/debian_version ]; then
    apt-get update -y >/dev/null 2>&1
    apt-get install -y curl unzip iptables >/dev/null 2>&1
elif [ -f /etc/redhat-release ]; then
    yum install -y curl unzip iptables >/dev/null 2>&1
fi

# 2. 检测系统架构
ARCH=$(uname -m)
case "$ARCH" in
    x86_64) S_ARCH="amd64" ;;
    aarch64|arm64) S_ARCH="aarch64" ;;
    *) echo "不支持的架构: $ARCH"; exit 1 ;;
esac

# 3. 停止旧服务并清理环境
systemctl stop snell 2>/dev/null
rm -rf /usr/local/bin/snell-server

# 4. 安全下载 (使用 curl -f 遇到 404 直接失败)
DOWNLOAD_URL="https://dl.nssurge.com/snell/snell-server-v5.0.1-linux-${S_ARCH}.zip"

echo "正在下载: $DOWNLOAD_URL"
curl -fsSL "$DOWNLOAD_URL" -o /tmp/snell.zip
if [ $? -ne 0 ]; then echo "❌ 下载失败，请检查网络或版本是否已更新"; exit 1; fi

unzip -o /tmp/snell.zip -d /usr/local/bin/ >/dev/null 2>&1
if [ ! -f /usr/local/bin/snell-server ]; then echo "❌ 解压失败，未找到二进制文件"; exit 1; fi

chmod +x /usr/local/bin/snell-server
rm -f /tmp/snell.zip

# 5. 生成配置文件
mkdir -p /etc/snell
cat > /etc/snell/snell-server.conf << EOF
[snell-server]
listen = 0.0.0.0:$PORT
psk = $PSK
ipv6 = false
EOF

# 6. 配置防火墙放行
if command -v ufw >/dev/null 2>&1; then
    ufw allow $PORT/tcp >/dev/null 2>&1
    ufw allow $PORT/udp >/dev/null 2>&1
fi
if command -v iptables >/dev/null 2>&1; then
    iptables -I INPUT -p tcp --dport $PORT -j ACCEPT
    iptables -I INPUT -p udp --dport $PORT -j ACCEPT
    netfilter-persistent save >/dev/null 2>&1 || service iptables save >/dev/null 2>&1
fi

# 7. 配置 Systemd 守护进程
cat > /etc/systemd/system/snell.service << EOF
[Unit]
Description=Snell Proxy Service
After=network.target

[Service]
Type=simple
LimitNOFILE=32768
ExecStart=/usr/local/bin/snell-server -c /etc/snell/snell-server.conf
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# 8. 启动服务并验证
systemctl daemon-reload
systemctl enable --now snell >/dev/null 2>&1
sleep 1.5

# 9. 核心修复：检查进程是否真的在运行
if systemctl is-active --quiet snell; then
    # 尝试获取公网IP，如果超时失败，则使用Python传入的兜底IP
    PUBLIC_IP=$(curl -s --max-time 3 https://api.ipify.org)
    [ -z "$PUBLIC_IP" ] && PUBLIC_IP="$TARGET_IP"
    
    echo "SNELL_DEPLOY_SUCCESS_LINK: snell://$PSK@$PUBLIC_IP:$PORT?version=5#Snell-Node"
else
    echo "❌ 服务启动失败！可能端口被占用，请执行 journalctl -u snell 查看原因。"
    exit 1
fi
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
                "settings": row[8],         # 数据库里存的是 JSON 字符串，直接传给后端
                "streamSettings": row[9],   # 同上
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
        
        # 采集等待
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
        
        #  获取 X-UI 本地数据并随包推送 
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
        time.sleep(5) # 降低频率，5秒推送一次

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

SYNC_COOLDOWN_SECONDS = 300

AUTO_COUNTRY_MAP = {
    # --- 亚太地区 ---
    '🇨🇳': '🇨🇳 中国', 'China': '🇨🇳 中国', '中国': '🇨🇳 中国', 'CN': '🇨🇳 中国', 'PRC': '🇨🇳 中国',
    '🇭🇰': '🇭🇰 香港', 'HK': '🇭🇰 香港', 'Hong Kong': '🇭🇰 香港', 'Hong Kong SAR': '🇭🇰 香港',
    '🇲🇴': '🇲🇴 澳门', 'MO': '🇲🇴 澳门', 'Macau': '🇲🇴 澳门', 'Macao': '🇲🇴 澳门',
    '🇹🇼': '🇹🇼 台湾', 'TW': '🇹🇼 台湾', 'Taiwan': '🇹🇼 台湾', 'Republic of China': '🇹🇼 台湾',
    '🇯🇵': '🇯🇵 日本', 'JP': '🇯🇵 日本', 'Japan': '🇯🇵 日本', 'Tokyo': '🇯🇵 日本', 'Osaka': '🇯🇵 日本',
    '🇸🇬': '🇸🇬 新加坡', 'SG': '🇸🇬 新加坡', 'Singapore': '🇸🇬 新加坡',
    '🇰🇷': '🇰🇷 韩国', 'KR': '🇰🇷 韩国', 'Korea': '🇰🇷 韩国', 'South Korea': '🇰🇷 韩国', 'Republic of Korea': '🇰🇷 韩国', '韩国': '🇰🇷 韩国', 'Seoul': '🇰🇷 韩国',
    '🇰🇵': '🇰🇵 朝鲜', 'KP': '🇰🇵 朝鲜', 'North Korea': '🇰🇵 朝鲜', '朝鲜': '🇰🇵 朝鲜',
    '🇮🇳': '🇮🇳 印度', 'IN': '🇮🇳 印度', 'India': '🇮🇳 印度', 'Mumbai': '🇮🇳 印度',
    '🇮🇩': '🇮🇩 印度尼西亚', 'ID': '🇮🇩 印度尼西亚', 'Indonesia': '🇮🇩 印度尼西亚', '印尼': '🇮🇩 印度尼西亚', '印度尼西亚': '🇮🇩 印度尼西亚', 'Jakarta': '🇮🇩 印度尼西亚',
    '🇲🇾': '🇲🇾 马来西亚', 'MY': '🇲🇾 马来西亚', 'Malaysia': '🇲🇾 马来西亚', '马来西亚': '🇲🇾 马来西亚',
    '🇹🇭': '🇹🇭 泰国', 'TH': '🇹🇭 泰国', 'Thailand': '🇹🇭 泰国', '泰国': '🇹🇭 泰国', 'Bangkok': '🇹🇭 泰国',
    '🇻🇳': '🇻🇳 越南', 'VN': '🇻🇳 越南', 'Vietnam': '🇻🇳 越南', 'Viet Nam': '🇻🇳 越南', '越南': '🇻🇳 越南',
    '🇵🇭': '🇵🇭 菲律宾', 'PH': '🇵🇭 菲律宾', 'Philippines': '🇵🇭 菲律宾', '菲律宾': '🇵🇭 菲律宾',
    '🇦🇺': '🇦🇺 澳大利亚', 'AU': '🇦🇺 澳大利亚', 'Australia': '🇦🇺 澳大利亚', '澳大利亚': '🇦🇺 澳大利亚', '澳洲': '🇦🇺 澳大利亚', 'Sydney': '🇦🇺 澳大利亚',
    '🇳🇿': '🇳🇿 新西兰', 'NZ': '🇳🇿 新西兰', 'New Zealand': '🇳🇿 新西兰', '新西兰': '🇳🇿 新西兰',

    # --- 北美地区 ---
    '🇺🇸': '🇺🇸 美国', 'USA': '🇺🇸 美国', 'US': '🇺🇸 美国', 'United States': '🇺🇸 美国', 'America': '🇺🇸 美国', '美国': '🇺🇸 美国',
    '🇨🇦': '🇨🇦 加拿大', 'CA': '🇨🇦 加拿大', 'Canada': '🇨🇦 加拿大', '加拿大': '🇨🇦 加拿大', 'Toronto': '🇨🇦 加拿大',
    '🇲🇽': '🇲🇽 墨西哥', 'MX': '🇲🇽 墨西哥', 'Mexico': '🇲🇽 墨西哥', '墨西哥': '🇲🇽 墨西哥',

    # --- 南美地区 ---
    '🇧🇷': '🇧🇷 巴西', 'BR': '🇧🇷 巴西', 'Brazil': '🇧🇷 巴西', '巴西': '🇧🇷 巴西', 'Sao Paulo': '🇧🇷 巴西',
    '🇨🇱': '🇨🇱 智利', 'CL': '🇨🇱 智利', 'Chile': '🇨🇱 智利', '智利': '🇨🇱 智利',
    '🇦🇷': '🇦🇷 阿根廷', 'AR': '🇦🇷 阿根廷', 'Argentina': '🇦🇷 阿根廷', '阿根廷': '🇦🇷 阿根廷',
    '🇨🇴': '🇨🇴 哥伦比亚', 'CO': '🇨🇴 哥伦比亚', 'Colombia': '🇨🇴 哥伦比亚', '哥伦比亚': '🇨🇴 哥伦比亚',
    '🇵🇪': '🇵🇪 秘鲁', 'PE': '🇵🇪 秘鲁', 'Peru': '🇵🇪 秘鲁', '秘鲁': '🇵🇪 秘鲁',

    # --- 欧洲地区 ---
    '🇬🇧': '🇬🇧 英国', 'UK': '🇬🇧 英国', 'GB': '🇬🇧 英国', 'United Kingdom': '🇬🇧 英国', 'Great Britain': '🇬🇧 英国', 'England': '🇬🇧 英国', '英国': '🇬🇧 英国', 'London': '🇬🇧 英国',
    '🇩🇪': '🇩🇪 德国', 'DE': '🇩🇪 德国', 'Germany': '🇩🇪 德国', '德国': '🇩🇪 德国', 'Frankfurt': '🇩🇪 德国',
    '🇫🇷': '🇫🇷 法国', 'FR': '🇫🇷 法国', 'France': '🇫🇷 法国', '法国': '🇫🇷 法国', 'Paris': '🇫🇷 法国',
    '🇳🇱': '🇳🇱 荷兰', 'NL': '🇳🇱 荷兰', 'Netherlands': '🇳🇱 荷兰', 'The Netherlands': '🇳🇱 荷兰', '荷兰': '🇳🇱 荷兰', 'Amsterdam': '🇳🇱 荷兰',
    '🇷🇺': '🇷🇺 俄罗斯', 'RU': '🇷🇺 俄罗斯', 'Russia': '🇷🇺 俄罗斯', 'Russian Federation': '🇷🇺 俄罗斯', '俄罗斯': '🇷🇺 俄罗斯', 'Moscow': '🇷🇺 俄罗斯',
    '🇮🇹': '🇮🇹 意大利', 'IT': '🇮🇹 意大利', 'Italy': '🇮🇹 意大利', '意大利': '🇮🇹 意大利', 'Milan': '🇮🇹 意大利',
    '🇪🇸': '🇪🇸 西班牙', 'ES': '🇪🇸 西班牙', 'Spain': '🇪🇸 西班牙', '西班牙': '🇪🇸 西班牙', 'Madrid': '🇪🇸 西班牙',
    '🇸🇪': '🇸🇪 瑞典', 'SE': '🇸🇪 瑞典', 'Sweden': '🇸🇪 瑞典', '瑞典': '🇸🇪 瑞典', 'Stockholm': '🇸🇪 瑞典',
    '🇨🇭': '🇨🇭 瑞士', 'CH': '🇨🇭 瑞士', 'Switzerland': '🇨🇭 瑞士', '瑞士': '🇨🇭 瑞士', 'Zurich': '🇨🇭 瑞士',
    '🇵🇱': '🇵🇱 波兰', 'PL': '🇵🇱 波兰', 'Poland': '🇵🇱 波兰', '波兰': '🇵🇱 波兰',
    '🇮🇪': '🇮🇪 爱尔兰', 'IE': '🇮🇪 爱尔兰', 'Ireland': '🇮🇪 爱尔兰', '爱尔兰': '🇮🇪 爱尔兰',
    '🇺🇦': '🇺🇦 乌克兰', 'UA': '🇺🇦 乌克兰', 'Ukraine': '🇺🇦 乌克兰', '乌克兰': '🇺🇦 乌克兰',
    '🇹🇷': '🇹🇷 土耳其', 'TR': '🇹🇷 土耳其', 'Turkey': '🇹🇷 土耳其', '土耳其': '🇹🇷 土耳其', 'Istanbul': '🇹🇷 土耳其',

    # --- 中东与非洲 ---
    '🇦🇪': '🇦🇪 阿联酋', 'AE': '🇦🇪 阿联酋', 'UAE': '🇦🇪 阿联酋', 'United Arab Emirates': '🇦🇪 阿联酋', '阿联酋': '🇦🇪 阿联酋', '阿拉伯联合酋长国': '🇦🇪 阿联酋', 'Dubai': '🇦🇪 阿联酋',
    '🇮🇱': '🇮🇱 以色列', 'IL': '🇮🇱 以色列', 'Israel': '🇮🇱 以色列', '以色列': '🇮🇱 以色列',
    '🇿🇦': '🇿🇦 南非', 'ZA': '🇿🇦 南非', 'South Africa': '🇿🇦 南非', '南非': '🇿🇦 南非', 'Johannesburg': '🇿🇦 南非',
    '🇸🇦': '🇸🇦 沙特', 'SA': '🇸🇦 沙特', 'Saudi Arabia': '🇸🇦 沙特', 'Kingdom of Saudi Arabia': '🇸🇦 沙特', '沙特': '🇸🇦 沙特', '沙特阿拉伯': '🇸🇦 沙特',
    '🇮🇷': '🇮🇷 伊朗', 'IR': '🇮🇷 伊朗', 'Iran': '🇮🇷 伊朗', '伊朗': '🇮🇷 伊朗',
    '🇪🇬': '🇪🇬 埃及', 'EG': '🇪🇬 埃及', 'Egypt': '🇪🇬 埃及', '埃及': '🇪🇬 埃及',
    '🇳🇬': '🇳🇬 尼日利亚', 'NG': '🇳🇬 尼日利亚', 'Nigeria': '🇳🇬 尼日利亚', '尼日利亚': '🇳🇬 尼日利亚',
}

GLOBE_STRUCTURE = r"""
<style>
    /* 容器填满父级 */
    #earth-container {
        width: 100%;
        height: 100%;
        position: relative;
        overflow: hidden;
        border-radius: 12px;
        background-color: #100C2A; /* 深色背景 */
    }
    
    /* 统计面板 */
    .earth-stats {
        position: absolute;
        top: 20px;
        left: 20px;
        color: rgba(255, 255, 255, 0.8);
        font-family: 'Consolas', monospace;
        font-size: 12px;
        z-index: 10;
        background: rgba(0, 20, 40, 0.6);
        padding: 10px 15px;
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 6px;
        backdrop-filter: blur(4px);
        pointer-events: none;
    }
    .earth-stats span { color: #00ffff; font-weight: bold; }
</style>

<div id="earth-container">
    <div class="earth-stats">
        <div>ACTIVE NODES: <span id="node-count">0</span></div>
        <div>REGIONS: <span id="region-count">0</span></div>
    </div>
    <div id="earth-render-area" style="width:100%; height:100%;"></div>
</div>
"""

GLOBE_JS_LOGIC = r"""
(function() {
    // 1. 获取仪表盘专用容器
    var container = document.getElementById('earth-render-area');
    if (!container) return;
    
    // 2. 初始化数据
    var serverData = window.DASHBOARD_DATA || [];
    
    // 3. 定义默认坐标 (北京)，如果定位成功会被覆盖
    var myLat = 39.9;
    var myLon = 116.4;

    // ✨✨✨ 修复核心：定义国旗字体 ✨✨✨
    var emojiFont = '"Twemoji Country Flags", "Noto Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", sans-serif';

    // 更新统计数字
    var nodeCountEl = document.getElementById('node-count');
    var regionCountEl = document.getElementById('region-count');
    function updateStats(data) {
        if(nodeCountEl) nodeCountEl.textContent = data.length;
        const uniqueRegions = new Set(data.map(s => s.name));
        if(regionCountEl) regionCountEl.textContent = uniqueRegions.size;
    }
    updateStats(serverData);

    // 初始化 ECharts
    var existing = echarts.getInstanceByDom(container);
    if (existing) existing.dispose();
    var myChart = echarts.init(container);

    // 4. 获取浏览器定位
    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            myLat = position.coords.latitude;
            myLon = position.coords.longitude;
            var option = buildOption(window.cachedWorldJson, serverData, myLat, myLon);
            myChart.setOption(option);
        });
    }

    // 5. 定义仪表盘专用的更新函数
    window.updateDashboardMap = function(newData) {
        if (!window.cachedWorldJson || !myChart) return;
        serverData = newData;
        updateStats(newData);
        var option = buildOption(window.cachedWorldJson, newData, myLat, myLon);
        myChart.setOption(option);
    };

    // 定义高亮区域
    const searchKeys = {
        '🇺🇸': 'United States', '🇨🇳': 'China', '🇭🇰': 'China', '🇹🇼': 'China', '🇯🇵': 'Japan', '🇰🇷': 'Korea',
        '🇸🇬': 'Singapore', '🇬🇧': 'United Kingdom', '🇩🇪': 'Germany', '🇫🇷': 'France', '🇷🇺': 'Russia',
        '🇨🇦': 'Canada', '🇦🇺': 'Australia', '🇮🇳': 'India', '🇧🇷': 'Brazil'
    };

    function buildOption(mapGeoJSON, data, userLat, userLon) {
        const mapFeatureNames = mapGeoJSON.features.map(f => f.properties.name);
        const activeMapNames = new Set();

        data.forEach(s => {
            let keyword = null;
            for (let key in searchKeys) {
                if ((s.name && s.name.includes(key))) {
                    keyword = searchKeys[key];
                    break;
                }
            }
            if (keyword && mapFeatureNames.includes(keyword)) {
                activeMapNames.add(keyword);
            }
        });

        const highlightRegions = Array.from(activeMapNames).map(name => ({
            name: name,
            itemStyle: { areaColor: '#0055ff', borderColor: '#00ffff', borderWidth: 1.5, opacity: 0.9 }
        }));

        const scatterData = data.map(s => ({
            name: s.name, value: [s.lon, s.lat], itemStyle: { color: '#00ffff' }
        }));
        
        scatterData.push({
            name: "ME", value: [userLon, userLat], itemStyle: { color: '#FFD700' },
            symbolSize: 15, label: { show: true, position: 'top', formatter: 'My PC', color: '#FFD700' }
        });

        const linesData = data.map(s => ({
            coords: [[s.lon, s.lat], [userLon, userLat]]
        }));

        return {
            backgroundColor: '#100C2A', 
            geo: {
                map: 'world', roam: false, zoom: 1.2, center: [15, 10],
                label: { show: false },
                itemStyle: { areaColor: '#1B2631', borderColor: '#404a59', borderWidth: 1 },
                emphasis: { itemStyle: { areaColor: '#2a333d' }, label: { show: false } },
                regions: highlightRegions 
            },
            series: [
                {
                    type: 'lines', coordinateSystem: 'geo', zlevel: 2,
                    effect: { show: true, period: 4, trailLength: 0.5, color: '#00ffff', symbol: 'arrow', symbolSize: 6 },
                    lineStyle: { color: '#00ffff', width: 1, opacity: 0, curveness: 0.2 },
                    data: linesData
                },
                {
                    type: 'scatter', coordinateSystem: 'geo', zlevel: 3, symbol: 'circle', symbolSize: 12,
                    itemStyle: { color: '#00ffff', shadowBlur: 10, shadowColor: '#333' },
                    
                    // ✨✨✨ 重点：在这里应用了字体 ✨✨✨
                    label: { 
                        show: true, 
                        position: 'right', 
                        formatter: '{b}', 
                        color: '#fff', 
                        fontSize: 16, 
                        fontWeight: 'bold',
                        fontFamily: emojiFont  // <--- 修复这一行
                    },
                    
                    data: scatterData
                }
            ]
        };
    }

    fetch('/static/world.json')
        .then(response => response.json())
        .then(worldJson => {
            echarts.registerMap('world', worldJson);
            window.cachedWorldJson = worldJson;
            var option = buildOption(worldJson, serverData, myLat, myLon);
            myChart.setOption(option);
            
            window.addEventListener('resize', () => myChart.resize());
            new ResizeObserver(() => myChart.resize()).observe(container);
        });
})();
"""

MATCH_MAP = {
    # --- 南美 ---
    '🇨🇱': 'Chile', 'CHILE': 'Chile',
    '🇧🇷': 'Brazil', 'BRAZIL': 'Brazil', 'BRA': 'Brazil', 'SAO PAULO': 'Brazil',
    '🇦🇷': 'Argentina', 'ARGENTINA': 'Argentina', 'ARG': 'Argentina',
    '🇨🇴': 'Colombia', 'COLOMBIA': 'Colombia', 'COL': 'Colombia',
    '🇵🇪': 'Peru', 'PERU': 'Peru',
    # --- 北美 ---
    '🇺🇸': 'United States', 'USA': 'United States', 'UNITED STATES': 'United States', 'AMERICA': 'United States',
    '🇨🇦': 'Canada', 'CANADA': 'Canada', 'CAN': 'Canada',
    '🇲🇽': 'Mexico', 'MEXICO': 'Mexico', 'MEX': 'Mexico',
    # --- 欧洲 ---
    '🇬🇧': 'United Kingdom', 'UK': 'United Kingdom', 'GB': 'United Kingdom', 'UNITED KINGDOM': 'United Kingdom', 'LONDON': 'United Kingdom',
    '🇩🇪': 'Germany', 'GERMANY': 'Germany', 'DEU': 'Germany', 'FRANKFURT': 'Germany',
    '🇫🇷': 'France', 'FRANCE': 'France', 'FRA': 'France', 'PARIS': 'France',
    '🇳🇱': 'Netherlands', 'NETHERLANDS': 'Netherlands', 'NLD': 'Netherlands', 'AMSTERDAM': 'Netherlands',
    '🇷🇺': 'Russia', 'RUSSIA': 'Russia', 'RUS': 'Russia',
    '🇮🇹': 'Italy', 'ITALY': 'Italy', 'ITA': 'Italy', 'MILAN': 'Italy',
    '🇪🇸': 'Spain', 'SPAIN': 'Spain', 'ESP': 'Spain', 'MADRID': 'Spain',
    '🇵🇱': 'Poland', 'POLAND': 'Poland', 'POL': 'Poland',
    '🇺🇦': 'Ukraine', 'UKRAINE': 'Ukraine', 'UKR': 'Ukraine',
    '🇸🇪': 'Sweden', 'SWEDEN': 'Sweden', 'SWE': 'Sweden',
    '🇨🇭': 'Switzerland', 'SWITZERLAND': 'Switzerland', 'CHE': 'Switzerland',
    '🇹🇷': 'Turkey', 'TURKEY': 'Turkey', 'TUR': 'Turkey',
    '🇮🇪': 'Ireland', 'IRELAND': 'Ireland', 'IRL': 'Ireland',
    '🇫🇮': 'Finland', 'FINLAND': 'Finland', 'FIN': 'Finland',
    '🇳🇴': 'Norway', 'NORWAY': 'Norway', 'NOR': 'Norway',
    '🇦🇹': 'Austria', 'AUSTRIA': 'Austria', 'AUT': 'Austria',
    '🇧🇪': 'Belgium', 'BELGIUM': 'Belgium', 'BEL': 'Belgium',
    '🇵🇹': 'Portugal', 'PORTUGAL': 'Portugal', 'PRT': 'Portugal',
    '🇬🇷': 'Greece', 'GREECE': 'Greece', 'GRC': 'Greece',
    # --- 亚太 ---
    '🇨🇳': 'China', 'CHINA': 'China', 'CHN': 'China', 'CN': 'China',
    '🇭🇰': 'China', 'HONG KONG': 'China', 'HK': 'China',
    '🇲🇴': 'China', 'MACAU': 'China', 'MO': 'China',
    '🇹🇼': 'China', 'TAIWAN': 'China', 'TW': 'China',
    '🇯🇵': 'Japan', 'JAPAN': 'Japan', 'JPN': 'Japan', 'TOKYO': 'Japan', 'OSAKA': 'Japan',
    '🇰🇷': 'South Korea', 'KOREA': 'South Korea', 'KOR': 'South Korea', 'SEOUL': 'South Korea',
    '🇸🇬': 'Singapore', 'SINGAPORE': 'Singapore', 'SGP': 'Singapore', 'SG': 'Singapore',
    '🇮🇳': 'India', 'INDIA': 'India', 'IND': 'India', 'MUMBAI': 'India',
    '🇦🇺': 'Australia', 'AUSTRALIA': 'Australia', 'AUS': 'Australia', 'SYDNEY': 'Australia',
    '🇳🇿': 'New Zealand', 'NEW ZEALAND': 'New Zealand', 'NZL': 'New Zealand',
    '🇻🇳': 'Vietnam', 'VIETNAM': 'Vietnam', 'VNM': 'Vietnam',
    '🇹🇭': 'Thailand', 'THAILAND': 'Thailand', 'THA': 'Thailand', 'BANGKOK': 'Thailand',
    '🇲🇾': 'Malaysia', 'MALAYSIA': 'Malaysia', 'MYS': 'Malaysia',
    '🇮🇩': 'Indonesia', 'INDONESIA': 'Indonesia', 'IDN': 'Indonesia', 'JAKARTA': 'Indonesia',
    '🇵🇭': 'Philippines', 'PHILIPPINES': 'Philippines', 'PHL': 'Philippines',
    '🇰🇭': 'Cambodia', 'CAMBODIA': 'Cambodia', 'KHM': 'Cambodia',
    # --- 中东/非洲 ---
    '🇦🇪': 'United Arab Emirates', 'UAE': 'United Arab Emirates', 'DUBAI': 'United Arab Emirates',
    '🇿🇦': 'South Africa', 'SOUTH AFRICA': 'South Africa', 'ZAF': 'South Africa',
    '🇸🇦': 'Saudi Arabia', 'SAUDI ARABIA': 'Saudi Arabia', 'SAU': 'Saudi Arabia',
    '🇮🇱': 'Israel', 'ISRAEL': 'Israel', 'ISR': 'Israel',
    '🇪🇬': 'Egypt', 'EGYPT': 'Egypt', 'EGY': 'Egypt',
    '🇮🇷': 'Iran', 'IRAN': 'Iran', 'IRN': 'Iran',
    '🇳🇬': 'Nigeria', 'NIGERIA': 'Nigeria', 'NGA': 'Nigeria'
}

PAGE_SIZE = 30
SYNC_COOLDOWN = 1800
