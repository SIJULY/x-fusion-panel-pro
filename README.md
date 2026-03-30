# X-Fusion Panel

X-Fusion Panel 是一个基于 Python 的面板项目，当前仓库已适配为“完整仓库源码 + 本地 Docker 构建”的发布方式，适合本地开发、Docker 部署以及通过 `install.sh` 在 VPS 上安装。

## 项目简介

本项目当前以完整源码仓库方式发布，应用主入口位于 `app/main.py`，Python 依赖以 `app/requirements.txt` 为准。

当前拆分后的项目结构如下：

```text README.md
project/
├─ app/                                  # 当前拆分后的主应用目录
│  ├─ __init__.py
│  ├─ main.py                            # 当前运行入口（拆分后入口）
│  ├─ requirements.txt                   # app 运行依赖
│  │
│  ├─ api/                               # 路由/接口桥接层
│  │  ├─ __init__.py
│  │  ├─ auth.py                         # 登录页、主页路由注册
│  │  ├─ probe.py                        # probe 相关接口桥接
│  │  ├─ status.py                       # /status 页面路由注册
│  │  ├─ subscriptions.py                # 订阅接口桥接
│  │  └─ notifications.py                # Telegram 通知发送
│  │
│  ├─ core/                              # 全局配置 / 状态 / 日志等核心层
│  │  ├─ __init__.py
│  │  ├─ config.py                       # 配置常量、路径、脚本模板
│  │  ├─ state.py                        # 全局缓存与 UI 状态容器
│  │  ├─ logging.py                      # logger / 线程池 / scheduler
│  │  └─ security.py                     # 安全模块预留位（当前较轻）
│  │
│  ├─ services/                          # 业务服务层
│  │  ├─ __init__.py
│  │  ├─ ssh.py                          # Paramiko SSH / WebSSH / 远程执行
│  │  ├─ probe.py                        # probe/agent 安装、推送、注册、状态
│  │  ├─ xui_api.py                      # X-UI HTTP API 管理器
│  │  ├─ xui_ssh.py                      # X-UI SSH/SQLite 管理器
│  │  ├─ manager_factory.py              # 选择 API 管理器或 SSH 管理器
│  │  ├─ xui_fetch.py                    # 节点/入站安全拉取
│  │  ├─ dashboard.py                    # 仪表盘统计与地图数据
│  │  ├─ server_ops.py                   # 服务器配置保存、命名、刷新等
│  │  ├─ subscriptions.py                # 订阅内容生成/转换
│  │  ├─ deployment.py                   # XHTTP/Hysteria/Snell 远程部署
│  │  └─ cloudflare.py                   # Cloudflare 自动解析/配置
│  │
│  ├─ jobs/                              # 启动任务 / 定时任务
│  │  ├─ __init__.py
│  │  ├─ startup.py                      # 启动时初始化后台任务
│  │  ├─ monitor.py                      # 服务器在线状态监控
│  │  ├─ traffic.py                      # 流量/节点周期同步
│  │  └─ geoip.py                        # GeoIP 命名修正任务
│  │
│  ├─ storage/                           # 数据文件读写层
│  │  ├─ __init__.py
│  │  ├─ files.py                        # 底层安全写文件
│  │  ├─ repositories.py                 # 保存/读取仓储封装
│  │  └─ bootstrap.py                    # 启动时加载 data/*
│  │
│  ├─ utils/                             # 工具层
│  │  ├─ __init__.py
│  │  ├─ geo.py                          # IP 地理位置 / 国旗 / 区域识别
│  │  ├─ network.py                      # ping / DNS / origin / 网络辅助
│  │  ├─ encoding.py                     # base64 / 节点链接生成与解析
│  │  ├─ formatters.py                   # 格式化/排序工具
│  │  └─ async_tools.py                  # 后台执行器包装
│  │
│  └─ ui/                                # UI 层
│     ├─ __init__.py
│     ├─ common/                         # UI 公共能力
│     │  ├─ __init__.py
│     │  ├─ notifications.py             # 通知、复制等 UI 公共反馈
│     │  ├─ dialogs_data.py              # 数据/全局设置弹窗
│     │  └─ dialogs_settings.py          # Cloudflare/设置类弹窗
│     │
│     ├─ components/                     # 页面组件
│     │  ├─ __init__.py
│     │  ├─ sidebar.py                   # 左侧导航/分组/服务器树
│     │  ├─ dashboard.py                 # 仪表盘 UI 组件
│     │  ├─ server_rows.py               # 服务器行渲染
│     │  └─ status_cards.py              # 状态卡片渲染
│     │
│     ├─ dialogs/                        # 各类对话框/操作弹窗
│     │  ├─ __init__.py
│     │  ├─ server_dialog.py             # 服务器新增/编辑主弹窗
│     │  ├─ inbound_dialog.py            # 节点(inbound)编辑弹窗
│     │  ├─ sub_dialogs.py               # 订阅编辑弹窗
│     │  ├─ group_dialogs.py             # 分组管理/排序/批量管理弹窗
│     │  ├─ bulk_edit.py                 # 批量编辑
│     │  ├─ batch_ssh.py                 # 批量 SSH 执行
│     │  ├─ ssh_console.py               # WebSSH 控制台
│     │  ├─ deploy_xhttp.py              # XHTTP 部署弹窗（拆分保留）
│     │  ├─ deploy_hysteria.py           # Hysteria 部署弹窗（拆分保留）
│     │  └─ deploy_snell.py              # Snell 部署弹窗（拆分保留）
│     │
│     └─ pages/                          # 页面级逻辑
│        ├─ __init__.py
│        ├─ login_page.py                # 登录页 + MFA + 会话校验
│        ├─ main_page.py                 # 主页面壳子
│        ├─ content_router.py            # 主内容区路由/切换
│        ├─ probe_page.py                # probe 设置页
│        ├─ subs_page.py                 # 订阅管理页
│        ├─ single_server.py             # 单服务器详情页
│        ├─ aggregated_view.py           # 聚合列表页
│        └─ public_status.py             # 公开监控墙/状态页
│
├─ static/                               # 前端静态资源
│  ├─ xterm.js                           # WebSSH 终端库
│  ├─ xterm.css
│  ├─ xterm-addon-fit.js
│  ├─ echarts-gl.min.js                  # 图表/地球视图相关
│  └─ world.json                         # 世界地图数据
│
├─ data/                                 # 运行时数据目录
│  ├─ .gitkeep
│  ├─ servers.json                       # 服务器配置
│  ├─ subscriptions.json                 # 订阅配置
│  ├─ admin_config.json                  # 管理配置
│  ├─ nodes_cache.json                   # 节点缓存
│  ├─ servers.json.bak                   # 服务器备份
│  └─ servers.json                       # 实际运行中主配置文件
│
├─ .github/
│  └─ workflows/
│     └─ docker-image.yml                # GitHub Actions 自动构建镜像
│
├─ Dockerfile                            # 镜像构建定义
├─ docker-compose.yml                    # 本地/源码模式 compose 启动
├─ install.sh                            # VPS 一键安装/更新/卸载脚本
├─ README.md                             # 项目说明文档
├─ requirements.txt                      # 根目录依赖文件
├─ main.py                               # 原始单文件版本（最高依据）
├─ main_index.json                       # 原始 main.py 索引
├─ main_slices/                          # 原始 main.py 切片辅助目录
├─ migration_manifest.md                 # 拆分职责清单
├─ migration_state.md                    # 迁移状态记录
├─ slice_main.py                         # main.py 切片辅助脚本
└─ build_index.py                        # main 索引构建脚本
```

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

