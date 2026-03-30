#!/bin/bash

# ==============================================================================
# X-Fusion Panel 一键安装/管理脚本
# 双模式：
# 1) 标准模式：镜像安装（推荐）
# 2) 开发者模式：拉取完整仓库源码并本地构建
# ==============================================================================

set -e

# --- 全局变量 ---
PROJECT_NAME="x-fusion-panel"
INSTALL_DIR="/root/${PROJECT_NAME}"

# 最新仓库地址
GIT_REPO_URL="https://github.com/SIJULY/x-fusion-panel-pro.git"
RAW_BASE_URL="https://raw.githubusercontent.com/SIJULY/x-fusion-panel-pro/main"

# 镜像地址：请按你的实际镜像仓库名调整
IMAGE_NAME="sijuly0713/x-fusion-panel-pro:latest"

# 分支
GIT_BRANCH="main"

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
    if [ "$(id -u)" -ne 0 ]; then
        print_error "此脚本必须以 root 用户身份运行。"
    fi
}

wait_for_apt_lock() {
    local wait_time=0
    local timeout=60
    while fuser /var/lib/dpkg/lock >/dev/null 2>&1 || \
          fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 || \
          fuser /var/lib/apt/lists/lock >/dev/null 2>&1 ; do
        echo -e "${YELLOW}[系统] 等待系统更新锁释放 (${wait_time}s)...${PLAIN}"
        sleep 10
        ((wait_time+=10))
        if [ "$wait_time" -ge "$timeout" ]; then
            killall apt apt-get dpkg 2>/dev/null || true
            rm -f /var/lib/apt/lists/lock /var/cache/apt/archives/lock /var/lib/dpkg/lock* || true
            dpkg --configure -a || true
            break
        fi
    done
}

check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        print_info "正在安装 Docker..."
        wait_for_apt_lock
        curl -fsSL https://get.docker.com | bash
        systemctl enable docker
        systemctl start docker
    fi

    if ! docker compose version >/dev/null 2>&1; then
        print_info "正在安装 Docker Compose..."
        wait_for_apt_lock
        apt-get update
        apt-get install -y docker-compose-plugin
    fi
}

check_git() {
    if ! command -v git >/dev/null 2>&1; then
        print_info "正在安装 Git..."
        wait_for_apt_lock
        apt-get update
        apt-get install -y git
    fi
}

init_directories() {
    mkdir -p "${INSTALL_DIR}/data"
    cd "${INSTALL_DIR}"

    # 初始化空数据文件，防止 Docker 自动创建目录
    [ -f "data/servers.json" ] || echo "[]" > data/servers.json
    [ -f "data/subscriptions.json" ] || echo "[]" > data/subscriptions.json
    [ -f "data/admin_config.json" ] || echo "{}" > data/admin_config.json
    [ -f "Caddyfile" ] || touch Caddyfile
}

# 开发者模式：拉完整仓库源码
download_source_code() {
    print_info "正在拉取完整仓库源码（开发者模式）..."

    check_git

    if [ -d "${INSTALL_DIR}/.git" ]; then
        print_info "检测到已有仓库，正在更新到最新 ${GIT_BRANCH}..."
        git -C "${INSTALL_DIR}" fetch origin
        git -C "${INSTALL_DIR}" reset --hard "origin/${GIT_BRANCH}"
    else
        rm -rf "${INSTALL_DIR}"
        git clone -b "${GIT_BRANCH}" "${GIT_REPO_URL}" "${INSTALL_DIR}"
    fi

    mkdir -p "${INSTALL_DIR}/data"
    [ -f "${INSTALL_DIR}/Caddyfile" ] || touch "${INSTALL_DIR}/Caddyfile"

    if [ ! -f "${INSTALL_DIR}/Dockerfile" ] || [ ! -f "${INSTALL_DIR}/app/main.py" ]; then
        print_error "完整仓库源码拉取失败！请检查仓库地址或网络。"
    fi

    print_success "源码拉取完成！"
}

generate_compose() {
    local BIND_IP=$1
    local PORT=$2
    local USER=$3
    local PASS=$4
    local SECRET=$5
    local ENABLE_CADDY=$6
    local MODE=$7

    cat > "${INSTALL_DIR}/docker-compose.yml" << EOF
services:
  x-fusion-panel:
EOF

    if [ "$MODE" = "dev" ]; then
        cat >> "${INSTALL_DIR}/docker-compose.yml" << EOF
    build: .
    image: x-fusion-panel:dev
    volumes:
      - ./data:/app/data
      - ./:/app
EOF
    else
        cat >> "${INSTALL_DIR}/docker-compose.yml" << EOF
    image: ${IMAGE_NAME}
    volumes:
      - ./data:/app/data
EOF
    fi

    cat >> "${INSTALL_DIR}/docker-compose.yml" << EOF
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
    image: tindy2013/subconverter:latest
    container_name: subconverter
    restart: always
    ports:
      - "127.0.0.1:25500:25500"
    environment:
      - TZ=Asia/Shanghai
EOF

    if [ "$ENABLE_CADDY" = "true" ]; then
        cat >> "${INSTALL_DIR}/docker-compose.yml" << EOF

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
      - subconverter
EOF
    fi
}

configure_caddy_docker() {
    local DOMAIN=$1
    local DOCKER_CADDY_FILE="${INSTALL_DIR}/Caddyfile"

    sed -i "/${CADDY_MARK_START}/,/${CADDY_MARK_END}/d" "$DOCKER_CADDY_FILE" 2>/dev/null || true

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

start_panel() {
    local MODE=$1

    print_info "正在启动容器..."
    cd "${INSTALL_DIR}"

    if [ "$MODE" = "dev" ]; then
        docker compose up -d --build
    else
        docker compose pull
        docker compose up -d
    fi
}

install_panel() {
    check_docker
    init_directories

    echo "------------------------------------------------"
    echo "请选择安装模式："
    echo -e "  1) ${GREEN}标准模式 (Image)${PLAIN} - 推荐，直接拉取预构建镜像安装"
    echo -e "  2) ${YELLOW}开发者模式 (Source)${PLAIN} - 拉取完整仓库源码并本地构建"
    echo "------------------------------------------------"
    read -p "选择模式 [1]: " mode_choice
    mode_choice=${mode_choice:-1}

    local MODE_TAG="standard"
    if [ "$mode_choice" = "2" ]; then
        MODE_TAG="dev"
        download_source_code
    fi

    local def_user="admin"
    local def_pass="admin"
    local def_key
    def_key=$(cat /proc/sys/kernel/random/uuid | tr -d '-')

    echo "------------------------------------------------"
    read -p "设置账号 [${def_user}]: " admin_user
    admin_user=${admin_user:-$def_user}
    read -p "设置密码 [${def_pass}]: " admin_pass
    admin_pass=${admin_pass:-$def_pass}
    read -p "设置密钥 (回车跳过): " input_key
    secret_key=${input_key:-$def_key}
    echo "------------------------------------------------"

    echo "请选择访问方式："
    echo "  1) IP + 端口 (无 HTTPS)"
    echo "  2) 域名访问 (自动 HTTPS)"
    echo "  3) 域名访问 (共存模式)"
    read -p "选项 [2]: " net_choice
    net_choice=${net_choice:-2}

    if [ "$net_choice" = "1" ]; then
        read -p "开放端口 [8081]: " port
        port=${port:-8081}

        generate_compose "0.0.0.0" "$port" "$admin_user" "$admin_pass" "$secret_key" "false" "$MODE_TAG"
        start_panel "$MODE_TAG"

        local ip_addr
        ip_addr=$(curl -s ifconfig.me || true)
        print_success "安装成功！http://${ip_addr}:${port}"

    elif [ "$net_choice" = "3" ]; then
        read -p "内部端口 [8081]: " port
        port=${port:-8081}

        generate_compose "127.0.0.1" "$port" "$admin_user" "$admin_pass" "$secret_key" "false" "$MODE_TAG"
        start_panel "$MODE_TAG"

        print_success "安装成功（共存模式）。请手动反代 127.0.0.1:${port}"

    else
        read -p "输入域名: " domain
        [ -n "$domain" ] || print_error "域名不能为空"

        configure_caddy_docker "$domain"
        generate_compose "127.0.0.1" "8081" "$admin_user" "$admin_pass" "$secret_key" "true" "$MODE_TAG"
        start_panel "$MODE_TAG"

        print_success "安装成功！https://${domain}"
    fi

    if [ "$MODE_TAG" = "dev" ]; then
        echo -e "${YELLOW}提示：代码位于 ${INSTALL_DIR}，修改后执行 docker compose restart 即可生效。${PLAIN}"
    fi
}

update_panel() {
    [ -d "${INSTALL_DIR}" ] || print_error "未检测到安装目录。"

    cd "${INSTALL_DIR}"

    [ -f "docker-compose.yml" ] || print_error "未检测到 docker-compose.yml。"
    cp docker-compose.yml docker-compose.yml.bak

    print_info "正在提取旧配置..."
    CONFIG_FILE="docker-compose.yml.bak"

    OLD_USER=$(grep "XUI_USERNAME=" "$CONFIG_FILE" | cut -d= -f2)
    OLD_PASS=$(grep "XUI_PASSWORD=" "$CONFIG_FILE" | cut -d= -f2)
    OLD_KEY=$(grep "XUI_SECRET_KEY=" "$CONFIG_FILE" | cut -d= -f2)
    PORT_LINE=$(grep ":8080" "$CONFIG_FILE" | head -n 1)

    IS_DEV="false"
    if grep -q "build: ." "$CONFIG_FILE"; then
        IS_DEV="true"
        print_warning "检测到当前为【开发者模式】"
    else
        print_info "检测到当前为【标准模式】"
    fi

    if [[ $PORT_LINE == *"127.0.0.1"* ]]; then
        BIND_IP="127.0.0.1"
        OLD_PORT=$(echo "$PORT_LINE" | sed -E 's/.*127.0.0.1:([0-9]+):8080.*/\1/' | tr -d ' "-')
        ENABLE_CADDY=$(grep -q "container_name: caddy" "$CONFIG_FILE" && echo "true" || echo "false")
    else
        BIND_IP="0.0.0.0"
        OLD_PORT=$(echo "$PORT_LINE" | sed -E 's/.*:([0-9]+):8080.*/\1/' | tr -d ' "-')
        ENABLE_CADDY="false"
    fi

    print_info "停止旧容器..."
    docker compose down

    if [ "$IS_DEV" = "true" ]; then
        echo -e "${YELLOW}您处于开发者模式。${PLAIN}"
        read -p "是否强制从 GitHub 拉取最新代码覆盖本地修改？(y/n) [n]: " pull_code
        if [ "$pull_code" = "y" ]; then
            download_source_code
            print_success "代码已更新（本地修改已覆盖）。"
        else
            print_info "跳过代码更新，保留本地文件。"
        fi

        generate_compose "$BIND_IP" "$OLD_PORT" "$OLD_USER" "$OLD_PASS" "$OLD_KEY" "$ENABLE_CADDY" "dev"
        print_info "正在重新构建..."
        docker compose up -d --build
    else
        generate_compose "$BIND_IP" "$OLD_PORT" "$OLD_USER" "$OLD_PASS" "$OLD_KEY" "$ENABLE_CADDY" "standard"
        print_info "正在拉取最新镜像..."
        docker compose pull
        docker compose up -d
        docker image prune -f
    fi

    if [ "$ENABLE_CADDY" = "true" ] && [ -f "Caddyfile" ]; then
        EXISTING_DOMAIN=$(grep " {" Caddyfile | head -n 1 | awk '{print $1}')
        if [ -n "$EXISTING_DOMAIN" ]; then
            configure_caddy_docker "${EXISTING_DOMAIN}"
        fi
    fi

    print_success "更新完成！"
}

uninstall_panel() {
    read -p "确定卸载并删除所有数据吗？(y/n): " confirm
    if [ "$confirm" = "y" ]; then
        if [ -d "${INSTALL_DIR}" ]; then
            cd "${INSTALL_DIR}" && docker compose down || true
            cd /root
            rm -rf "${INSTALL_DIR}"
        fi
        print_success "卸载完成。"
    fi
}

# --- 主入口 ---
check_root
clear

echo -e "${GREEN}=========================================${PLAIN}"
echo -e "${GREEN}    X-Fusion Panel 一键管理脚本         ${PLAIN}"
echo -e "${GREEN}=========================================${PLAIN}"
echo -e "  1. 安装面板（镜像模式 / 开发者模式）"
echo -e "  2. 更新面板"
echo -e "  3. 卸载面板"
echo -e "  0. 退出"
echo

read -p "请输入选项: " choice

case $choice in
    1) install_panel ;;
    2) update_panel ;;
    3) uninstall_panel ;;
    0) exit 0 ;;
    *) print_error "无效选项" ;;
esac
