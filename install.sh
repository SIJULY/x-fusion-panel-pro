#!/bin/bash

# 开启错误检查，但增加容错
set -e

PROJECT_NAME="x-fusion-panel"
INSTALL_DIR="/root/${PROJECT_NAME}"
GIT_REPO_URL="https://github.com/SIJULY/x-fusion-panel-pro.git"
IMAGE_NAME="sijuly0713/x-fusion-panel-pro:latest"
GIT_BRANCH="main"

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

# 检查 Root
check_root() {
    if [[ $EUID -ne 0 ]]; then
        print_error "请用 root 用户运行此脚本"
    fi
}

# 检查 Docker
check_docker() {
    if ! command -v docker >/dev/null 2>&1; then
        print_info "正在安装 Docker..."
        curl -fsSL https://get.docker.com | bash
        systemctl enable docker && systemctl start docker
    fi

    if ! docker compose version >/dev/null 2>&1; then
        print_info "正在安装 Docker Compose 插件..."
        apt-get update && apt-get install -y docker-compose-plugin || yum install -y docker-compose-plugin
    fi
}

# 检查并配置 Buildx
check_buildx() {
    if ! docker buildx version >/dev/null 2>&1; then
        print_warning "buildx 未安装或版本过低"
    fi

    if ! docker buildx inspect x-builder >/dev/null 2>&1; then
        print_info "初始化 buildx 实例..."
        docker buildx create --name x-builder --use
    else
        docker buildx use x-builder
    fi
    docker buildx inspect --bootstrap >/dev/null 2>&1
}

download_source() {
    if ! command -v git >/dev/null 2>&1; then
        print_info "安装 Git..."
        apt-get update && apt-get install -y git || yum install -y git
    fi
    
    print_info "拉取源码至 ${INSTALL_DIR}..."
    rm -rf "${INSTALL_DIR}"
    git clone -b "${GIT_BRANCH}" "${GIT_REPO_URL}" "${INSTALL_DIR}"
}

generate_compose() {
    print_info "生成 docker-compose.yml..."
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
}

build_image() {
    cd "${INSTALL_DIR}"
    print_info "开始本地构建镜像..."
    # 修正：本地加载不支持多平台同时构建，这里自动识别本机架构
    docker build -t ${IMAGE_NAME} .
    print_success "本地镜像构建完成"
}

start_panel() {
    cd "${INSTALL_DIR}"
    print_info "启动容器中..."
    docker compose up -d
}

install_panel() {
    check_docker
    
    echo -e "${YELLOW}请选择安装模式:${PLAIN}"
    echo "1) 镜像模式（推荐，直接拉取现成镜像）"
    echo "2) 开发者模式（从源码本地构建）"
    read -p "选择 [1-2]: " mode < /dev/tty
    mode=${mode:-1}

    if [ "$mode" = "2" ]; then
        check_buildx
        download_source
        build_image
    else
        mkdir -p "${INSTALL_DIR}"
    fi

    generate_compose
    start_panel

    IP=$(curl -s https://api64.ipify.org || curl -s ifconfig.me || echo "VPS_IP")
    print_success "X-Fusion Panel 安装完成！"
    print_info "管理地址：http://${IP}:8081"
    print_info "默认账号：admin"
    print_info "默认密码：admin"
}

update_panel() {
    if [ ! -d "${INSTALL_DIR}" ]; then print_error "未检测到安装目录，请先执行安装"; fi
    cd "${INSTALL_DIR}"
    print_info "正在更新镜像并重启..."
    docker compose pull
    docker compose up -d
    print_success "更新完成"
}

uninstall_panel() {
    read -p "确定要卸载并删除所有数据吗? (y/n): " confirm < /dev/tty
    if [[ "$confirm" == "y" || "$confirm" == "Y" ]]; then
        cd "${INSTALL_DIR}" && docker compose down || true
        rm -rf "${INSTALL_DIR}"
        print_success "卸载完成"
    else
        print_info "已取消卸载"
    fi
}

# --- 脚本主逻辑 ---
check_root

# 移除可能导致崩溃的 clear
echo "-----------------------------------------"
echo -e "${BLUE}    X-Fusion Panel 一键脚本 (修复版) ${PLAIN}"
echo "-----------------------------------------"
echo "1. 安装/重装"
echo "2. 仅更新"
echo "3. 彻底卸载"
echo "0. 退出"
echo "-----------------------------------------"

# 修复在管道执行时的输入读取
if [ -t 0 ]; then
    read -p "请输入选项: " choice
else
    read -p "请输入选项: " choice < /dev/tty
fi

case $choice in
    1) install_panel ;;
    2) update_panel ;;
    3) uninstall_panel ;;
    0) exit 0 ;;
    *) print_error "无效选项" ;;
esac
