#!/bin/bash

# ==============================================================================
# X-Fusion Panel Pro 修复版 (严格对齐仓库目录结构)
# ==============================================================================

PROJECT_NAME="x-fusion-panel-pro"
INSTALL_DIR="/root/${PROJECT_NAME}"
REPO_URL="https://raw.githubusercontent.com/SIJULY/x-fusion-panel-pro/main"

RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
PLAIN="\033[0m"

print_info() { echo -e "${BLUE}[信息]${PLAIN} $1"; }
print_success() { echo -e "${GREEN}[成功]${PLAIN} $1"; }
print_error() { echo -e "${RED}[错误]${PLAIN} $1"; exit 1; }

check_docker() {
    if ! command -v docker &> /dev/null; then
        curl -fsSL https://get.docker.com | bash
        systemctl enable docker && systemctl start docker
    fi
    if ! docker compose version &> /dev/null; then
        apt-get update && apt-get install -y docker-compose-plugin
    fi
}

# --- 📥 修复重点：严格按照仓库结构下载文件 ---
download_source_code() {
    print_info "正在同步源码文件..."
    
    # 1. 先彻底清理旧目录，防止干扰
    rm -rf ${INSTALL_DIR}
    mkdir -p ${INSTALL_DIR}/app
    mkdir -p ${INSTALL_DIR}/data
    
    # 2. 下载根目录文件
    curl -sS -H 'Cache-Control: no-cache' -o ${INSTALL_DIR}/Dockerfile ${REPO_URL}/Dockerfile
    
    # 3. 下载 app 目录下的核心文件 (必须放在 app/ 文件夹内)
    # 因为 Dockerfile 里写的是 COPY app/requirements.txt
    curl -sS -H 'Cache-Control: no-cache' -o ${INSTALL_DIR}/app/requirements.txt ${REPO_URL}/app/requirements.txt
    curl -sS -H 'Cache-Control: no-cache' -o ${INSTALL_DIR}/app/main.py ${REPO_URL}/app/main.py
    
    if [ ! -f "${INSTALL_DIR}/app/requirements.txt" ]; then
        print_error "文件下载失败，请检查网络或仓库路径！"
    fi
    print_success "文件同步完成。"
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
    build: .
    image: x-fusion-panel-pro:local
    container_name: x-fusion-panel
    restart: always
    ports:
      - "${BIND_IP}:${PORT}:8080"
    volumes:
      - ./data:/app/data
    environment:
      - TZ=Asia/Shanghai
      - XUI_USERNAME=${USER}
      - XUI_PASSWORD=${PASS}
      - XUI_SECRET_KEY=${SECRET}

  subconverter:
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
    [ "$(id -u)" -ne 0 ] && print_error "请用 root 运行"
    check_docker
    download_source_code
    
    read -p "设置账号 [admin]: " admin_user
    admin_user=${admin_user:-admin}
    read -p "设置密码 [admin]: " admin_pass
    admin_pass=${admin_pass:-admin}
    secret_key=$(cat /proc/sys/kernel/random/uuid | tr -d '-')
    read -p "访问端口 [8081]: " port
    port=${port:-8081}

    generate_compose "0.0.0.0" "$port" "$admin_user" "$admin_pass" "$secret_key"

    print_info "开始本地构建 (ARM 适配)..."
    cd ${INSTALL_DIR}
    docker compose up -d --build

    local ip_addr=$(curl -s ifconfig.me)
    print_success "安装成功！http://${ip_addr}:${port}"
}

# --- 菜单 ---
clear
echo "========================================="
echo "    X-Fusion Panel Pro 一键管理脚本      "
echo "========================================="
echo "  1. 安装/重装 Pro 版"
echo "  2. 卸载"
echo "  0. 退出"
read -p "选择: " choice

case $choice in
    1) install_panel ;;
    2) 
        [ -d "${INSTALL_DIR}" ] && (cd ${INSTALL_DIR} && docker compose down)
        rm -rf ${INSTALL_DIR}
        print_success "已卸载"
        ;;
    0) exit 0 ;;
esac
