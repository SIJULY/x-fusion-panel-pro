# X-Fusion Panel

X-Fusion Panel 是一个基于 Python 的面板项目，当前仓库已适配为“完整仓库源码 + 本地 Docker 构建”的发布方式，适合本地开发、Docker 部署以及通过 `install.sh` 在 VPS 上安装。

## 项目简介

本项目当前以完整源码仓库方式发布，应用主入口位于 `app/main.py`，Python 依赖以 `app/requirements.txt` 为准。




## 环境要求

- Python 3.11+
- Docker
- Docker Compose Plugin
- Git（使用 `install.sh` 时需要）

## 本地运行方式

可使用一条命令完成本地环境初始化并启动：

```bash
python3 -m venv .venv && source .venv/bin/activate && pip install -r app/requirements.txt && python app/main.py
```

## Docker / docker-compose 运行方式

### Docker

在项目根目录可使用一条命令完成构建并启动：

```bash
bash <(curl -Ls https://raw.githubusercontent.com/SIJULY/x-fusion-panel-pro/main/install.sh)
```

### Docker Compose

如果项目根目录已有 `docker-compose.yml`，可直接一条命令启动：

```bash
docker compose up -d --build
```

## install.sh 使用方式

适用于 VPS 一键安装 / 更新，可直接远程一条命令执行：

```bash
bash <(curl -Ls https://raw.githubusercontent.com/SIJULY/x-fusion-panel-pro/main/install.sh)
```

如需先下载后再手动执行，也可使用：

```bash
wget -O install.sh https://raw.githubusercontent.com/SIJULY/x-fusion-panel-pro/main/install.sh && chmod +x install.sh && sudo ./install.sh
```

脚本会拉取完整仓库源码，并通过本地 `Dockerfile` 构建运行。

## 默认登录说明

安装脚本默认登录信息：

- 用户名：`admin`
- 密码：`admin`

首次安装后建议立即修改默认账号信息。

## data 目录说明

`data/` 用于存放运行时数据，例如：

- `servers.json`
- `subscriptions.json`
- `admin_config.json`

该目录属于本地运行数据目录，部署时应保留，提交到公开仓库时应避免提交真实运行内容。

## 安全提示

- 不要提交真实生产密码、密钥、令牌、域名配置。
- 不要把真实运行期 `data/` 内容直接提交到 GitHub。
- 如需展示配置文件内容，请使用示例值或脱敏内容。
- 示例文档中的默认账号仅用于初始化演示，不建议在生产环境长期保留。

## 说明

当前 README 仅保留发布适配所需的最小必要说明，后续如需补充功能介绍、截图或进阶部署文档，可再单独扩展。

