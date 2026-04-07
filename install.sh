#!/bin/bash

# ==============================================================================
# X-Fusion Panel Pro 一键管理脚本 (ARM 适配 + Caddy 反代)
# ==============================================================================

PROJECT_NAME="x-fusion-panel-pro"
INSTALL_DIR="/root/${PROJECT_NAME}"
GIT_REPO_URL="https://github.com/SIJULY/x-fusion-panel-pro.git"

# 颜色定义
RED="\033[31m"
GREEN="\033[32m"
YELLOW="\033[33m"
BLUE="\033[34m"
PLAIN="\033[0m"

print_info() { echo -e "${BLUE}[信息]${PLAIN} $1"; }
print_success() { echo -e "${GREEN}[成功]${PLAIN} $1"; }
print_warning() { echo -e "${YELLOW}[警告]${PLAIN} $1"; }
print_error() { echo -e "${RED}[错误]${PLAIN} $1"; exit 1; }

check_root() {
    [ "$(id -u)" -ne 0 ] && print_error "必须以 root 运行"
}

check_docker() {
    if ! command -v docker &> /dev/null; then
        print_info "安装 Docker..."
        curl -fsSL https://get.docker.com | bash
        systemctl enable docker && systemctl start docker
    fi
    if ! docker compose version &> /dev/null; then
        print_info "安装 Docker Compose..."
        apt-get update && apt-get install -y docker-compose-plugin || yum install -y docker-compose-plugin
    fi
}

init_directories() {
    mkdir -p ${INSTALL_DIR}/data
}

download_source() {
    print_info "同步源码..."
    if [ -d "${INSTALL_DIR}/.git" ]; then
        cd "${INSTALL_DIR}" && git pull
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
    local ENABLE_CADDY=$6
    local MODE=$7

    cat > ${INSTALL_DIR}/docker-compose.yml << EOF
version: '3.8'
services:
  x-fusion-panel:
EOF

    if [ "$MODE" == "dev" ]; then
        # 开发者模式：挂载本地目录
        cat >> ${INSTALL_DIR}/docker-compose.yml << EOF
    build: .
    image: x-fusion-panel-pro:dev
    volumes:
      - ./data:/app/data
      - ./:/app
EOF
    else
        # 标准模式：本地构建但不挂载源码
        cat >> ${INSTALL_DIR}/docker-compose.yml << EOF
    build: .
    image: x-fusion-panel-pro:latest
    volumes:
      - ./data:/app/data
EOF
    fi

    cat >> ${INSTALL_DIR}/docker-compose.yml << EOF
    container_name: x-fusion-panel
    restart: always
    ports:
      - "${BIND_IP}:${PORT}:8080"
    environment:
      - TZ=Asia/Shanghai
      - XUI_USERNAME=${USER}
      - XUI_PASSWORD=${PASS}
      - XUI_SECRET_KEY=${SECRET}

  subconverter:
    # 使用支持 ARM64 的镜像
    image: asdlokj123/subconverter:latest
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
    cat > ${INSTALL_DIR}/Caddyfile << EOF
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
EOF
}

install_panel() {
    check_docker
    download_source
    init_directories

    echo -e "${YELLOW}--- 安装配置 ---${PLAIN}"
    read -p "设置账号 [admin]: " admin_user
    admin_user=${admin_user:-admin}
    read -p "设置密码 [admin]: " admin_pass
    admin_pass=${admin_pass:-admin}
    secret_key=$(cat /proc/sys/kernel/random/uuid | tr -d '-')

    echo -e "\n${YELLOW}--- 访问方式 ---${PLAIN}"
    echo "1) IP + 端口"
    echo "2) 域名 + 自动 HTTPS (Caddy)"
    read -p "请选择 [1]: " net_choice
    net_choice=${net_choice:-1}

    if [ "$net_choice" == "2" ]; then
        read -p "请输入解析到此服务器的域名: " domain
        [ -z "$domain" ] && print_error "域名不能为空"
        configure_caddy "$domain"
        generate_compose "127.0.0.1" "8081" "$admin_user" "$admin_pass" "$secret_key" "true" "standard"
    else
        read -p "访问端口 [8081]: " port
        port=${port:-8081}
        generate_compose "0.0.0.0" "$port" "$admin_user" "$admin_pass" "$secret_key" "false" "standard"
    fi

    print_info "开始构建镜像并启动服务 (ARM 适配中)..."
    cd ${INSTALL_DIR}
    docker compose up -d --build

    IP=$(curl -s ifconfig.me)
    URL=$([ "$net_choice" == "2" ] && echo "https://${domain}" || echo "http://${IP}:${port}")
    
    print_success "安装成功！"
    echo -e "管理地址: ${GREEN}${URL}${PLAIN}"
    echo -e "账号密码: ${admin_user} / ${admin_pass}"
}

update_panel() {
    [ ! -d "${INSTALL_DIR}" ] && print_error "未安装"
    cd ${INSTALL_DIR}
    print_info "正在获取源码更新..."
    git pull
    docker compose up -d --build
    print_success "更新完成"
}

uninstall_panel() {
    read -p "确认卸载? (y/n): " c
    if [ "$c" == "y" ]; then
        cd ${INSTALL_DIR} && docker compose down
        rm -rf ${INSTALL_DIR}
        print_success "已卸载"
    fi
}

# --- 主入口 ---
check_root
clear
echo -e "${BLUE}=========================================${PLAIN}"
echo -e "${BLUE}    X-Fusion Panel Pro 管理脚本          ${PLAIN}"
echo -e "${BLUE}=========================================${PLAIN}"
echo "1. 安装面板"
echo "2. 更新面板"
echo "3. 卸载面板"
echo "0. 退出"
read -p "请选择: " choice

case $choice in
    1) install_panel ;;
    2) update_panel ;;
    3) uninstall_panel ;;
    0) exit 0 ;;
    *) print_error "选项无效" ;;
esac
