#!/bin/bash

# ==============================================================================
# X-Fusion Panel Pro 一键管理脚本 (100% 源码本地构建模式)
# ==============================================================================

# --- 全局变量 ---
PROJECT_NAME="x-fusion-panel-pro"
INSTALL_DIR="/root/${PROJECT_NAME}"
# 指向你的 Pro 版仓库 raw 地址
REPO_URL="https://raw.githubusercontent.com/SIJULY/x-fusion-panel-pro/main"

# Caddy 配置标记
CADDY_MARK_START="# X-Fusion Panel Config Start"
CADDY_MARK_END="# X-Fusion Panel Config End"

# 颜色定义
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
PLAIN="\033[0m"

# --- 辅助函数 ---
print_info() { echo -e "${BLUE}[信息]${PLAIN} $1"; }
print_success() { echo -e "${GREEN}[成功]${PLAIN} $1"; }
print_warning() { echo -e "${YELLOW}[警告]${PLAIN} $1"; }
print_error() { echo -e "${RED}[错误]${PLAIN} $1"; exit 1; }

check_root() {
    [ "$(id -u)" -ne 0 ] && print_error "必须以 root 运行"
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

# --- 核心功能：下载源码 ---
download_source_code() {
    print_info "正在从仓库拉取源码文件..."
    
    mkdir -p ${INSTALL_DIR}/app
    mkdir -p ${INSTALL_DIR}/data
    
    # 下载构建所需的核心文件
    curl -sS -H 'Cache-Control: no-cache' -o ${INSTALL_DIR}/Dockerfile ${REPO_URL}/Dockerfile
    # 注意：如果你的 requirements 在 app 目录下，请确认路径
    curl -sS -H 'Cache-Control: no-cache' -o ${INSTALL_DIR}/app/requirements.txt ${REPO_URL}/app/requirements.txt
    curl -sS -H 'Cache-Control: no-cache' -o ${INSTALL_DIR}/app/main.py ${REPO_URL}/app/main.py
    
    # 简单校验
    if [ ! -f "${INSTALL_DIR}/Dockerfile" ]; then
        print_error "下载失败！请检查网络或仓库地址: ${REPO_URL}"
    fi
    print_success "源码下载完成！"
}

init_directories() {
    mkdir -p ${INSTALL_DIR}/data
    cd ${INSTALL_DIR}
    [ ! -f "Caddyfile" ] && touch Caddyfile
}

generate_compose() {
    local BIND_IP=$1
    local PORT=$2
    local USER=$3
    local PASS=$4
    local SECRET=$5
    local ENABLE_CADDY=$6

    cat > ${INSTALL_DIR}/docker-compose.yml << EOF
services:
  x-fusion-panel:
    # 核心：直接使用本地目录进行构建
    build: .
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
    # 使用官方支持 ARM 的镜像
    image: tindy2013/subconverter:latest
    container_name: subconverter
    restart: always
    expose:
      - "25500"
    environment:
      - TZ=Asia/Shanghai
EOF

    if [ "$ENABLE_CADDY" == "true" ]; then
        cat >> ${INSTALL_DIR}/docker-compose.yml << EOF

  caddy:
    image: caddy:latest
    container_name: caddy
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./caddy_data:/data
    depends_on:
      - x-fusion-panel
EOF
    fi
}

configure_caddy() {
    local DOMAIN=$1
    local DOCKER_CADDY_FILE="${INSTALL_DIR}/Caddyfile"
    sed -i "/${CADDY_MARK_START}/,/${CADDY_MARK_END}/d" "$DOCKER_CADDY_FILE"
    
    cat >> "$DOCKER_CADDY_FILE" << EOF
${CADDY_MARK_START}
${DOMAIN} {
    encode gzip
    handle_path /convert* {
        rewrite * /sub
        reverse_proxy subconverter:25500 
    }
    handle {
        reverse_proxy x-fusion-panel:8080
    }
}
${CADDY_MARK_END}
EOF
}

install_panel() {
    check_docker
    download_source_code
    init_directories

    # 配置账号
    local def_user="admin"
    local def_pass="admin"
    local def_key=$(cat /proc/sys/kernel/random/uuid | tr -d '-')

    echo "------------------------------------------------"
    read -p "设置账号 [${def_user}]: " admin_user
    admin_user=${admin_user:-$def_user}
    read -p "设置密码 [${def_pass}]: " admin_pass
    admin_pass=${admin_pass:-$def_pass}
    read -p "设置密钥 (回车随机): " input_key
    secret_key=${input_key:-$def_key}
    echo "------------------------------------------------"

    # 配置网络
    echo "选择访问方式："
    echo "  1) IP + 端口"
    echo "  2) 域名访问 (Caddy 自动 HTTPS)"
    read -p "选项 [1]: " net_choice
    net_choice=${net_choice:-1}

    if [ "$net_choice" == "1" ]; then
        read -p "开放端口 [8081]: " port
        port=${port:-8081}
        generate_compose "0.0.0.0" "$port" "$admin_user" "$admin_pass" "$secret_key" "false"
    else
        read -p "输入域名: " domain
        [ -z "$domain" ] && print_error "域名不能为空"
        configure_caddy "$domain"
        generate_compose "127.0.0.1" "8081" "$admin_user" "$admin_pass" "$secret_key" "true"
    fi

    print_info "正在本地构建镜像并启动服务..."
    cd ${INSTALL_DIR}
    docker compose up -d --build

    IP=$(curl -s ifconfig.me)
    [ "$net_choice" == "1" ] && URL="http://${IP}:${port}" || URL="https://${domain}"
    print_success "安装成功！访问地址: ${URL}"
}

uninstall_panel() {
    read -p "确定卸载吗？(y/n): " confirm
    if [ "$confirm" == "y" ]; then
        if [ -d "${INSTALL_DIR}" ]; then
            cd ${INSTALL_DIR} && docker compose down
            rm -rf ${INSTALL_DIR}
        fi
        print_success "卸载完成。"
    fi
}

# --- 主入口 ---
check_root
clear
echo -e "${GREEN}=========================================${PLAIN}"
echo -e "${GREEN}    X-Fusion Panel Pro 管理脚本          ${PLAIN}"
echo -e "${GREEN}=========================================${PLAIN}"
echo "1. 安装/重装面板"
echo "2. 卸载面板"
echo "0. 退出"
read -p "选项: " choice

case $choice in
    1) install_panel ;;
    2) uninstall_panel ;;
    0) exit 0 ;;
    *) print_error "无效选项" ;;
esac
