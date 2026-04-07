#!/bin/bash

# 取消 set -e，改用手动逻辑检查，防止脚本莫名其妙中断
# set -e 

PROJECT_NAME="x-fusion-panel"
INSTALL_DIR="/root/${PROJECT_NAME}"
GIT_REPO_URL="https://github.com/SIJULY/x-fusion-panel-pro.git"
IMAGE_NAME="sijuly0713/x-fusion-panel-pro:latest"

# 颜色
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
PLAIN="\033[0m"

echo -e "${BLUE}=========================================${PLAIN}"
echo -e "${BLUE}    X-Fusion Panel 修复版一键脚本        ${PLAIN}"
echo -e "${BLUE}=========================================${PLAIN}"

# 1. 检查 Root
if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[错误]${PLAIN} 请用 root 用户运行"
    exit 1
fi

# 2. 交互逻辑 (增加 /dev/tty 强制定向，防止管道失效)
echo -e "${YELLOW}请选择操作:${PLAIN}"
echo "1) 安装/更新"
echo "2) 卸载"
echo "0) 退出"
printf "选择 [1]: "
read -r choice < /dev/tty
choice=${choice:-1}

if [ "$choice" == "0" ]; then
    exit 0
fi

if [ "$choice" == "2" ]; then
    echo -n "确定卸载吗? (y/n): "
    read -r confirm < /dev/tty
    if [ "$confirm" == "y" ]; then
        cd "${INSTALL_DIR}" && docker compose down || true
        rm -rf "${INSTALL_DIR}"
        echo -e "${GREEN}[成功]${PLAIN} 已卸载"
    fi
    exit 0
fi

# 3. 安装 Docker
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${BLUE}[信息]${PLAIN} 正在安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker && systemctl start docker
fi

if ! docker compose version >/dev/null 2>&1; then
    echo -e "${BLUE}[信息]${PLAIN} 正在安装 Docker Compose 插件..."
    apt-get update && apt-get install -y docker-compose-plugin || yum install -y docker-compose-plugin
fi

# 4. 创建配置
echo -e "${BLUE}[信息]${PLAIN} 正在准备配置文件..."
mkdir -p "${INSTALL_DIR}/data"
cat > "${INSTALL_DIR}/docker-compose.yml" <<EOF
services:
  x-fusion-panel:
    image: ${IMAGE_NAME}
    container_name: x-fusion-panel
    restart: always
    ports:
      - "0.0.0.0:8081:8080"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
      - XUI_USERNAME=admin
      - XUI_PASSWORD=admin

  subconverter:
    image: ghcr.io/metacubex/subconverter:latest
    container_name: subconverter
    restart: always
    ports:
      - "127.0.0.1:25500:25500"
EOF

# 5. 启动
echo -e "${BLUE}[信息]${PLAIN} 正在拉取镜像并启动..."
cd "${INSTALL_DIR}"
docker compose pull
docker compose up -d

# 6. 完成
IP=$(curl -s --max-time 5 https://api64.ipify.org || curl -s --max-time 5 ifconfig.me || echo "你的VPS_IP")
echo -e "-----------------------------------------"
echo -e "${GREEN}[成功] X-Fusion Panel 已启动！${PLAIN}"
echo -e "访问地址: ${BLUE}http://${IP}:8081${PLAIN}"
echo -e "默认账号: ${YELLOW}admin${PLAIN}"
echo -e "默认密码: ${YELLOW}admin${PLAIN}"
echo -e "-----------------------------------------"
