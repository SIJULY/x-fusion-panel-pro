#!/bin/bash

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
echo -e "${BLUE}    X-Fusion Panel 最终修复版 (ARM兼容)  ${PLAIN}"
echo -e "${BLUE}=========================================${PLAIN}"

if [[ $EUID -ne 0 ]]; then
    echo -e "${RED}[错误]${PLAIN} 请用 root 用户运行"
    exit 1
fi

echo -e "${YELLOW}请选择操作:${PLAIN}"
echo "1) 安装/更新"
echo "2) 卸载"
echo "0) 退出"
printf "选择 [1]: "
read -r choice < /dev/tty
choice=${choice:-1}

if [ "$choice" == "0" ]; then exit 0; fi

if [ "$choice" == "2" ]; then
    cd "${INSTALL_DIR}" && docker compose down || true
    rm -rf "${INSTALL_DIR}"
    echo -e "${GREEN}[成功]${PLAIN} 已卸载"
    exit 0
fi

# 检查 Docker
if ! command -v docker >/dev/null 2>&1; then
    echo -e "${BLUE}[信息]${PLAIN} 正在安装 Docker..."
    curl -fsSL https://get.docker.com | bash
    systemctl enable docker && systemctl start docker
fi

if ! docker compose version >/dev/null 2>&1; then
    echo -e "${BLUE}[信息]${PLAIN} 正在安装 Docker Compose..."
    apt-get update && apt-get install -y docker-compose-plugin || yum install -y docker-compose-plugin
fi

# 准备配置
echo -e "${BLUE}[信息]${PLAIN} 正在准备配置文件 (已自动适配 ARM)..."
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
    # 替换为支持 ARM64 的镜像
    image: asdlokj123/subconverter:latest
    container_name: subconverter
    restart: always
    ports:
      - "127.0.0.1:25500:25500"
EOF

# 启动
echo -e "${BLUE}[信息]${PLAIN} 正在拉取镜像并启动..."
cd "${INSTALL_DIR}"
docker compose pull
docker compose up -d

# 检查服务状态
if [ "$(docker ps -q -f name=subconverter)" ]; then
    STATUS="${GREEN}运行中${PLAIN}"
else
    STATUS="${RED}启动失败 (请检查架构兼容性)${PLAIN}"
fi

IP=$(curl -s --max-time 5 https://api64.ipify.org || curl -s --max-time 5 ifconfig.me || echo "你的VPS_IP")
echo -e "-----------------------------------------"
echo -e "${GREEN}[成功] X-Fusion Panel 安装逻辑执行完毕！${PLAIN}"
echo -e "访问地址: ${BLUE}http://${IP}:8081${PLAIN}"
echo -e "后端服务: ${STATUS}"
echo -e "默认账号: ${YELLOW}admin${PLAIN}"
echo -e "默认密码: ${YELLOW}admin${PLAIN}"
echo -e "-----------------------------------------"
