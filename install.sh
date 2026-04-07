#!/bin/bash

# ==============================================================================
# X-Fusion Panel Pro 最终适配版 (全仓库同步模式)
# ==============================================================================

PROJECT_NAME="x-fusion-panel-pro"
INSTALL_DIR="/root/${PROJECT_NAME}"
GIT_REPO_URL="https://github.com/SIJULY/x-fusion-panel-pro.git"

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
        print_info "正在安装 Docker..."
        curl -fsSL https://get.docker.com | bash
        systemctl enable docker && systemctl start docker
    fi
    if ! docker compose version &> /dev/null; then
        print_info "正在安装 Docker Compose..."
        apt-get update && apt-get install -y docker-compose-plugin
    fi
}

# --- 📥 改用 git clone 确保目录结构完整 ---
sync_source_code() {
    if ! command -v git &> /dev/null; then
        print_info "安装 Git..."
        apt-get update && apt-get install -y git
    fi
    
    print_info "正在同步完整仓库源码..."
    if [ -d "${INSTALL_DIR}/.git" ]; then
        cd "${INSTALL_DIR}" && git reset --hard HEAD && git pull
    else
        rm -rf "${INSTALL_DIR}"
        git clone "${GIT_REPO_URL}" "${INSTALL_DIR}"
    fi
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
    build: 
      context: .
      dockerfile: Dockerfile
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
    sync_source_code
    
    read -p "设置账号 [admin]: " admin_user
    admin_user=${admin_user:-admin}
    read -p "设置密码 [admin]: " admin_pass
    admin_pass=${admin_pass:-admin}
    secret_key=$(cat /proc/sys/kernel/random/uuid | tr -d '-')
    read -p "访问端口 [8081]: " port
    port=${port:-8081}

    generate_compose "0.0.0.0" "$port" "$admin_user" "$admin_pass" "$secret_key"

    print_info "开始本地镜像构建 (请稍后)..."
    cd ${INSTALL_DIR}
    docker compose up -d --build

    local ip_addr=$(curl -s ifconfig.me)
    print_success "安装完成！访问地址: http://${ip_addr}:${port}"
}

# --- 主界面 ---
clear
echo "========================================="
echo "    X-Fusion Panel Pro 一键管理脚本      "
echo "========================================="
echo "  1. 安装/更新 Pro 版"
echo "  2. 卸载面板"
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
