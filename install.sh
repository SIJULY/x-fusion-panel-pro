#!/bin/bash

# ==============================================================================
# X-Fusion Panel Pro 终极修复版 (完全沿用成功老版的逻辑)
# ==============================================================================

# --- 全局变量 ---
PROJECT_NAME="x-fusion-panel-pro"
INSTALL_DIR="/root/${PROJECT_NAME}"
# 指向 Pro 版仓库
REPO_URL="https://raw.githubusercontent.com/SIJULY/x-fusion-panel-pro/main"

# 颜色定义
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
PLAIN="\033[0m"

print_info() { echo -e "${BLUE}[信息]${PLAIN} $1"; }
print_success() { echo -e "${GREEN}[成功]${PLAIN} $1"; }
print_error() { echo -e "${RED}[错误]${PLAIN} $1"; exit 1; }

check_root() {
    [ "$(id -u)" -ne 0 ] && print_error "必须以 root 用户运行。"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_info "正在安装 Docker..."
        curl -fsSL https://get.docker.com | bash
        systemctl enable docker && systemctl start docker
    fi
    if ! docker compose version &> /dev/null; then
        print_info "正在安装 Docker Compose..."
        apt-get update && apt-get install -y docker-compose-plugin
    fi
}

# 📥 [核心] 仿照成功老版：下载源码到本地
download_source_code() {
    print_info "正在同步 Pro 版源码..."
    mkdir -p ${INSTALL_DIR}/app
    mkdir -p ${INSTALL_DIR}/data
    
    # 逐个拉取核心文件，确保本地构建有素材
    curl -sS -H 'Cache-Control: no-cache' -o ${INSTALL_DIR}/Dockerfile ${REPO_URL}/Dockerfile
    curl -sS -H 'Cache-Control: no-cache' -o ${INSTALL_DIR}/requirements.txt ${REPO_URL}/requirements.txt
    curl -sS -H 'Cache-Control: no-cache' -o ${INSTALL_DIR}/app/main.py ${REPO_URL}/app/main.py
    
    # 如果 Pro 版有其他依赖文件夹，这里可以继续添加
}

generate_compose() {
    local BIND_IP=$1
    local PORT=$2
    local USER=$3
    local PASS=$4
    local SECRET=$5

    cat > ${INSTALL_DIR}/docker-compose.yml << EOF
services:
  x-fusion-panel:
    # 🛠️ 关键：强制本地构建 (Build)，不拉取 Docker Hub 镜像
    build: .
    image: x-fusion-panel-pro:local
    container_name: x-fusion-panel
    restart: always
    ports:
      - "${BIND_IP}:${PORT}:8080"
    volumes:
      - ./data:/app/data
      - ./:/app
    environment:
      - TZ=Asia/Shanghai
      - XUI_USERNAME=${USER}
      - XUI_PASSWORD=${PASS}
      - XUI_SECRET_KEY=${SECRET}

  subconverter:
    # 🚀 使用老版脚本中成功的镜像 (支持 ARM)
    image: tindy2013/subconverter:latest
    container_name: subconverter
    restart: always
    ports:
      - "127.0.0.1:25500:25500"
    environment:
      - TZ=Asia/Shanghai
EOF
}

install_panel() {
    check_root
    check_docker
    download_source_code
    
    # 默认账号配置
    read -p "设置账号 [admin]: " admin_user
    admin_user=${admin_user:-admin}
    read -p "设置密码 [admin]: " admin_pass
    admin_pass=${admin_pass:-admin}
    secret_key=$(cat /proc/sys/kernel/random/uuid | tr -d '-')

    read -p "开放端口 [8081]: " port
    port=${port:-8081}

    generate_compose "0.0.0.0" "$port" "$admin_user" "$admin_pass" "$secret_key"

    print_info "正在启动容器 (执行本地 Build)..."
    cd ${INSTALL_DIR}
    # 使用 --build 强制重新编译，确保 ARM 兼容
    docker compose up -d --build

    local ip_addr=$(curl -s ifconfig.me)
    print_success "Pro 版安装成功！http://${ip_addr}:${port}"
}

# --- 主入口 ---
clear
echo "========================================="
echo "    X-Fusion Panel Pro 一键管理脚本      "
echo "========================================="
echo "  1. 安装 Pro 版"
echo "  2. 卸载"
echo "  0. 退出"
read -p "选择: " choice

case $choice in
    1) install_panel ;;
    2) 
        cd ${INSTALL_DIR} && docker compose down || true
        rm -rf ${INSTALL_DIR}
        print_success "已卸载"
        ;;
    0) exit 0 ;;
esac
