#!/bin/bash

set -e

PROJECT_NAME="x-fusion-panel"
INSTALL_DIR="/root/${PROJECT_NAME}"

GIT_REPO_URL="https://github.com/SIJULY/x-fusion-panel-pro.git"
IMAGE_NAME="sijuly0713/x-fusion-panel-pro:latest"
GIT_BRANCH="main"

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
    [ "$(id -u)" -ne 0 ] && print_error "请用 root 运行"
}

# ✅ Docker + Compose
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        print_info "安装 Docker..."
        curl -fsSL https://get.docker.com | bash
        systemctl enable docker && systemctl start docker
    fi

    if ! docker compose version >/dev/null 2>&1; then
        print_info "安装 docker compose..."
        apt-get update && apt-get install -y docker-compose-plugin
    fi
}

# ✅ buildx（关键）
check_buildx() {
    if ! docker buildx version >/dev/null 2>&1; then
        print_warning "buildx 未安装，初始化中..."
    fi

    if ! docker buildx inspect multiarch >/dev/null 2>&1; then
        docker buildx create --name multiarch --use
    else
        docker buildx use multiarch
    fi

    docker buildx inspect --bootstrap >/dev/null 2>&1
}

check_git() {
    if ! command -v git >/dev/null 2>&1; then
        apt-get update && apt-get install -y git
    fi
}

init_dir() {
    mkdir -p "${INSTALL_DIR}/data"
    cd "${INSTALL_DIR}"
}

# ✅ 拉源码（修复路径问题）
download_source() {
    print_info "拉取源码..."

    check_git
    cd /root

    rm -rf "${INSTALL_DIR}"
    git clone -b "${GIT_BRANCH}" "${GIT_REPO_URL}" "${INSTALL_DIR}"

    mkdir -p "${INSTALL_DIR}/data"

    print_success "源码拉取完成"
}

# ✅ docker-compose（已改 ARM）
generate_compose() {
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
}

# ✅ 多架构构建
build_multi_arch() {
    print_info "构建多架构镜像..."

    docker buildx build \
      --platform linux/amd64,linux/arm64 \
      -t ${IMAGE_NAME} \
      --load .
}

start_panel() {
    cd "${INSTALL_DIR}"
    docker compose up -d
}

install_panel() {
    check_docker
    check_buildx

    echo "1) 镜像模式（推荐）"
    echo "2) 开发者模式（本地构建 ARM/x86）"
    read -p "选择 [1]: " mode
    mode=${mode:-1}

    if [ "$mode" = "2" ]; then
        download_source
        build_multi_arch
    else
        mkdir -p "${INSTALL_DIR}"
        cd "${INSTALL_DIR}"
    fi

    generate_compose
    start_panel

    IP=$(curl -s ifconfig.me || echo "你的IP")
    print_success "访问：http://${IP}:8081"
}

update_panel() {
    cd "${INSTALL_DIR}" || print_error "未安装"

    print_info "更新中..."
    docker compose pull || true
    docker compose up -d

    print_success "更新完成"
}

uninstall_panel() {
    read -p "确认卸载? (y/n): " c
    [ "$c" != "y" ] && exit 0

    cd "${INSTALL_DIR}" && docker compose down || true
    rm -rf "${INSTALL_DIR}"

    print_success "已卸载"
}

# 主入口
check_root
clear

echo "========================================="
echo "    X-Fusion Panel 一键脚本（增强版）"
echo "========================================="
echo "1. 安装"
echo "2. 更新"
echo "3. 卸载"
echo "0. 退出"

read -p "选择: " c

case $c in
1) install_panel ;;
2) update_panel ;;
3) uninstall_panel ;;
0) exit ;;
*) print_error "无效选项" ;;
esac
