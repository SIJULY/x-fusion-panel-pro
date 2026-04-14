# X-Fusion Panel

X-Fusion Panel 是一个基于 **NiceGUI + FastAPI + Paramiko** 的服务器与节点管理面板，围绕以下场景构建：

- 管理 X-UI / 节点面板
- 通过 SSH 托管服务器
- 安装与接收探针数据
- 聚合查看服务器、节点、流量与状态
- 生成订阅并对接 subconverter
- 通过 WebSSH / SFTP 直接管理远程文件

当前仓库已经完成模块化拆分，项目可正常运行，页面职责也已经重新整理完成。

---

## 1. 当前项目状态

当前代码库已经不再是单纯的“大一统 `main.py`”形式，而是：

- **运行入口**：`app/main.py`
- **核心业务代码**：集中在 `app/`
- **根目录 `main.py`**：保留为历史单文件版本参考
- **`main_slices/`、`main_index.json`**：历史切片/索引辅助产物，用于迁移与比对，不参与当前正式运行链路

也就是说：

> **现在真正运行的是 `app/` 下的模块化版本。**

---

## 2. 技术栈

- Python 3.11
- NiceGUI
- FastAPI
- Paramiko
- APScheduler
- Requests / urllib3
- PyOTP / QRCode / Pillow
- Docker / Docker Compose

---

## 3. 运行入口与启动流程

### 正式入口

项目当前正式入口：

```python app/main.py
python app/main.py
```

`app/main.py` 负责：

- 注册静态资源 `/static`
- 注册登录页 `/login` 与主页面 `/`
- 注册公开状态页 `/status`
- 注册探针接口：
  - `POST /api/probe/push`
  - `POST /api/probe/register`
  - `POST /api/auto_register_node`
- 注册订阅接口：
  - `GET /sub/{token}`
  - `GET /sub/group/{group_b64}`
  - `GET /get/sub/{target}/{token}`
  - `GET /get/group/{target}/{group_b64}`
- 注册仪表盘实时数据接口：
  - `GET /api/dashboard/live_data`
- 启动数据加载与后台任务
- 最终调用 `ui.run(...)` 监听 `0.0.0.0:8080`

### 启动初始化流程

启动时主要执行：

1. `init_data()`：加载 `data/` 中的配置与缓存
2. `register_auth_pages()`：注册登录页与主页
3. `register_status_page()`：注册状态墙页面
4. `startup_sequence()`：启动后台任务与进程池

---

## 4. 当前模块职责说明

下面先给出你想要的这种**树状图结构总览**，再在后面分模块说明职责。

### 4.1 当前项目树状结构

```text README.md
project/
├─ app/                                  # 当前正式运行的主应用目录
│  ├─ __init__.py
│  ├─ main.py                            # 当前运行入口（正式入口）
│  ├─ requirements.txt                   # app 运行依赖
│  │
│  ├─ api/                               # 路由/接口桥接层
│  │  ├─ __init__.py
│  │  ├─ auth.py                         # 登录页、主页路由注册
│  │  ├─ probe.py                        # probe 相关接口桥接
│  │  ├─ status.py                       # /status 页面路由注册
│  │  ├─ subscriptions.py                # 订阅接口与转换接口
│  │  └─ notifications.py                # Telegram 通知发送
│  │
│  ├─ core/                              # 全局配置 / 状态 / 日志等核心层
│  │  ├─ __init__.py
│  │  ├─ config.py                       # 配置常量、路径、脚本模板
│  │  ├─ state.py                        # 全局缓存与 UI 状态容器
│  │  ├─ logging.py                      # logger / 线程池 / scheduler
│  │  └─ security.py                     # 安全相关预留模块
│  │
│  ├─ services/                          # 业务服务层
│  │  ├─ __init__.py
│  │  ├─ ssh.py                          # Paramiko SSH / WebSSH / 远程执行
│  │  ├─ sftp.py                         # 远程文件管理 / 上传下载 / 权限处理
│  │  ├─ probe.py                        # probe/agent 安装、推送、注册、状态
│  │  ├─ xui_api.py                      # X-UI HTTP API 管理器
│  │  ├─ xui_ssh.py                      # X-UI SSH/SQLite 管理器
│  │  ├─ manager_factory.py              # 选择 API 管理器或 SSH 管理器
│  │  ├─ xui_fetch.py                    # 节点/入站安全拉取
│  │  ├─ dashboard.py                    # 仪表盘统计与实时数据
│  │  ├─ server_ops.py                   # 服务器命名、刷新、分组、保存等
│  │  ├─ subscriptions.py                # 订阅相关服务逻辑
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
│     │  ├─ server_dialog.py             # 服务器新增/编辑主弹窗（兼容入口保留）
│     │  ├─ inbound_dialog.py            # 节点(inbound)编辑弹窗
│     │  ├─ sub_dialogs.py               # 订阅编辑弹窗
│     │  ├─ group_dialogs.py             # 分组管理/排序/批量管理弹窗
│     │  ├─ bulk_edit.py                 # 批量编辑
│     │  ├─ batch_ssh.py                 # 批量 SSH 执行
│     │  ├─ ssh_console.py               # WebSSH 控制台弹窗
│     │  ├─ deploy_xhttp.py              # XHTTP 部署弹窗
│     │  ├─ deploy_hysteria.py           # Hysteria 部署弹窗
│     │  └─ deploy_snell.py              # Snell 部署弹窗
│     │
│     └─ pages/                          # 页面级逻辑
│        ├─ __init__.py
│        ├─ login_page.py                # 登录页 + MFA + 会话校验
│        ├─ main_page.py                 # 主页面壳子
│        ├─ content_router.py            # 主内容区路由/切换
│        ├─ probe_page.py                # probe 设置页
│        ├─ subs_page.py                 # 订阅管理页
│        ├─ aggregated_view.py           # 聚合列表页
│        ├─ single_server.py             # 单服务器详情页
│        ├─ single_ssh.py                # 单服务器 SSH / 文件管理页
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
│  └─ .gitkeep                           # 默认占位，实际运行时会生成 JSON/密钥文件
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
├─ main.py                               # 原始单文件版本（历史参考）
├─ main_index.json                       # 原始 main.py 索引
├─ main_slices/                          # 原始 main.py 切片辅助目录
├─ migration_manifest.md                 # 拆分职责清单
├─ migration_state.md                    # 迁移状态记录
├─ slice_main.py                         # main.py 切片辅助脚本
└─ build_index.py                        # main 索引构建脚本
```

---

### 4.2 `app/api/`：接口桥接与页面注册

#### `app/api/auth.py`
负责注册：
- `/login`
- `/`

对应页面分别来自：
- `app/ui/pages/login_page.py`
- `app/ui/pages/main_page.py`

#### `app/api/status.py`
负责注册：
- `/status`

对应页面来自：
- `app/ui/pages/public_status.py`

#### `app/api/subscriptions.py`
负责订阅相关接口逻辑：
- 原始订阅生成
- 分组订阅生成
- 短链/转换订阅
- subconverter 参数组装与转发

#### `app/api/notifications.py`
负责 Telegram 消息发送。

#### `app/api/probe.py`
当前是一个**薄桥接文件**，把探针相关接口实现从 `app.services.probe` 暴露出来，本身不承载主要逻辑。

---

### 4.3 `app/core/`：核心基础层

#### `app/core/config.py`
定义：
- 数据目录与文件路径
- 环境变量读取
- 默认账号密码
- 自动注册密钥
- 各种脚本模板（探针安装、XHTTP、Hysteria、Snell）
- 国家/区域映射表与坐标数据

#### `app/core/state.py`
维护运行期全局状态，例如：
- `SERVERS_CACHE`
- `SUBS_CACHE`
- `NODES_DATA`
- `ADMIN_CONFIG`
- `PROBE_DATA_CACHE`
- `PING_TREND_CACHE`
- `CURRENT_VIEW_STATE`
- 各类 UI 引用缓存

#### `app/core/logging.py`
负责：
- 全局日志输出
- `ThreadPoolExecutor`
- `AsyncIOScheduler`

#### `app/core/security.py`
当前存在，但职责较轻，更多属于预留核心模块。

---

### 4.4 `app/jobs/`：后台任务

#### `app/jobs/startup.py`
启动时：
- 创建 `ProcessPoolExecutor`
- 启动 APScheduler
- 注册周期任务
- 启动初始化同步任务

#### `app/jobs/traffic.py`
负责周期流量/节点同步。

#### `app/jobs/monitor.py`
负责服务器状态监控与告警逻辑。

#### `app/jobs/geoip.py`
负责 GeoIP 命名修正相关任务。

---

### 4.5 `app/storage/`：数据持久化

#### `app/storage/bootstrap.py`
启动时从 `data/` 加载：
- `servers.json`
- `subscriptions.json`
- `nodes_cache.json`
- `admin_config.json`

#### `app/storage/repositories.py`
负责保存：
- 服务器配置
- 管理配置
- 订阅配置
- 节点缓存
- 全局 SSH 私钥

#### `app/storage/files.py`
提供底层安全写文件能力。

---

### 4.6 `app/services/`：业务服务层

这是项目最核心的业务区。

#### 服务器/面板相关
- `server_ops.py`：命名、刷新、分组、保存等服务器操作
- `manager_factory.py`：根据配置选择 API 管理器或 SSH 管理器
- `xui_api.py`：X-UI HTTP API 方式管理
- `xui_ssh.py`：SSH/SQLite 方式管理 X-UI
- `xui_fetch.py`：安全拉取入站/节点数据

#### SSH / 文件 / 远程操作
- `ssh.py`：SSH 客户端、WebSSH、远程执行
- `sftp.py`：远程目录、文件上传下载、读写、重命名、权限修改

#### 探针相关
- `probe.py`：探针安装、注册、推送、自动注册节点、状态处理

#### 订阅/转换相关
- `subscriptions.py`：订阅链接复制、构造、转换辅助

#### 部署相关
- `deployment.py`：一键部署 XHTTP / Hysteria / Snell

#### 其他服务
- `dashboard.py`：仪表盘实时统计数据
- `cloudflare.py`：Cloudflare DNS 自动处理

---

### 4.7 `app/utils/`：工具层

- `geo.py`：地理位置与国家识别
- `network.py`：网络探测、DNS、origin 等辅助
- `encoding.py`：节点链接生成、明文配置生成、base64 处理
- `formatters.py`：格式化与排序工具
- `async_tools.py`：异步辅助封装

---

### 4.8 `app/ui/`：界面层

UI 现在已经重新按职责拆开。

#### `app/ui/pages/`：页面级逻辑

这是本次拆分后最重要的整理结果。

- `login_page.py`：登录页、MFA、会话校验
- `main_page.py`：主框架页，包含 Header / Drawer / 内容容器初始化
- `content_router.py`：主内容区路由分发与刷新中心
- `aggregated_view.py`：服务器聚合列表页
- `single_server.py`：单服务器详情页
- `single_ssh.py`：单服务器 SSH / WebSSH / 文件管理页
- `probe_page.py`：探针管理页
- `subs_page.py`：订阅管理页
- `public_status.py`：公开状态墙 / 公共状态页

#### `app/ui/components/`：可复用组件

- `sidebar.py`：左侧服务器树与分组导航
- `dashboard.py`：仪表盘 UI 组件与刷新逻辑
- `server_rows.py`：聚合列表中的服务器行渲染
- `status_cards.py`：状态卡片渲染

#### `app/ui/dialogs/`：操作弹窗

- `server_dialog.py`：新增/编辑服务器弹窗，且保留页面函数的兼容转发入口
- `inbound_dialog.py`：节点编辑弹窗
- `sub_dialogs.py`：订阅编辑弹窗
- `group_dialogs.py`：分组管理弹窗
- `bulk_edit.py`：批量编辑
- `batch_ssh.py`：批量 SSH 执行
- `ssh_console.py`：SSH 控制台弹窗
- `deploy_xhttp.py` / `deploy_hysteria.py` / `deploy_snell.py`：部署类弹窗

#### `app/ui/common/`：UI 公共能力

- `notifications.py`：通知、复制等统一反馈
- `dialogs_data.py`：数据类弹窗
- `dialogs_settings.py`：设置类弹窗

---

## 5. 当前页面路由与内容分发关系

### 公开与登录层
- `/login` → `login_page.py`
- `/` → `main_page.py`
- `/status` → `public_status.py`

### 主内容区动态路由
登录后进入主页，真正的内容区由 `app/ui/pages/content_router.py` 负责分发。

它会根据 scope 渲染：

- `DASHBOARD`
- `PROBE`
- `SUBS`
- `ALL`
- `TAG`
- `COUNTRY`
- `SINGLE`
- `SSH_SINGLE`

其中：
- 聚合列表页 → `aggregated_view.py`
- 单机详情页 → `single_server.py`
- SSH 页面 → `single_ssh.py`

这部分已经从原来的 `server_dialog.py` 中真正拆出。

---

## 6. 目录结构总览

目录结构已经在上面的树状图中完整列出。这里补一句最重要的结论：

- **正式运行代码在 `app/`**
- **运行数据在 `data/`**
- **前端静态资源在 `static/`**
- **根目录 `main.py`、`main_slices/`、`main_index.json` 属于历史迁移参考产物**

---

## 7. `data/` 目录说明

项目运行时数据默认保存在：

- 本地开发：项目根目录下的 `data/`
- Docker 运行：`/app/data`

主要文件：

- `servers.json`：服务器配置
- `subscriptions.json`：订阅配置
- `admin_config.json`：管理员配置
- `nodes_cache.json`：节点缓存
- `global_ssh_key`：全局 SSH 私钥文件（如果已设置）

> `data/` 是运行期真实数据目录，部署时必须保留，公开仓库中不要提交真实生产数据。

---

## 8. `static/` 目录说明

当前静态资源包括：

- `xterm.js`
- `xterm.css`
- `xterm-addon-fit.js`
- `echarts-gl.min.js`
- `world.json`

主要用于：
- WebSSH 终端
- 仪表盘图表
- 地图/地球展示

---

## 9. 本地运行

### 环境要求

- Python 3.11+
- 建议使用虚拟环境

### 安装依赖

```bash README.md
python3 -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
```

### 启动项目

```bash README.md
python app/main.py
```

默认监听：
- `0.0.0.0:8080`

默认登录环境变量：
- `XUI_USERNAME=admin`
- `XUI_PASSWORD=admin`
- `XUI_SECRET_KEY=sijuly_secret_key_default`

如果未显式设置，代码会使用默认值。

---

## 10. Docker 运行

### 使用 Docker Compose

```bash README.md
docker compose up -d --build
```

当前默认映射：
- 面板：`8081 -> 8080`
- 数据卷：`./data:/app/data`

同时会启动：
- `x-fusion-panel`
- `subconverter`

---

## 11. VPS 安装脚本

`install.sh` 提供安装/更新/卸载流程，主要能力：

- 自动安装 Docker / Docker Compose / Git
- 克隆或更新仓库源码
- 生成 `docker-compose.yml`
- 支持：
  - IP + 端口方式访问
  - 域名 + Caddy 自动 HTTPS
- 构建并启动服务

执行方式：

```bash README.md
bash <(curl -Ls https://raw.githubusercontent.com/SIJULY/x-fusion-panel-pro/main/install.sh)
```

或：

```bash README.md
wget -O install.sh https://raw.githubusercontent.com/SIJULY/x-fusion-panel-pro/main/install.sh
chmod +x install.sh
./install.sh
```

> 注意：脚本中的仓库地址、镜像名、端口策略以脚本内容为准，部署前建议自行复核一遍。

---

## 12. 默认登录说明

默认账号密码来自环境变量，未设置时默认：

- 用户名：`admin`
- 密码：`admin`

首次部署后建议立即修改相关配置，并妥善保存：

- 面板管理员账号密码
- `XUI_SECRET_KEY`
- `data/` 下的实际配置数据

---

## 13. 安全建议

### 必做
- 不要把真实 `data/` 目录内容提交到 Git 仓库
- 不要把真实服务器密码、SSH 私钥、TG Token、Cloudflare Token 提交到公开仓库
- 首次部署后立即修改默认管理员账号密码
- 修改自动注册密钥 `XUI_SECRET_KEY`

### 推荐
- 生产环境使用反代或 HTTPS
- 定期备份 `data/`
- 对可公网访问的接口增加访问控制
- 谨慎暴露 `/status` 与订阅接口给外部环境

---

## 14. 历史迁移文件说明

以下文件/目录主要是为了历史迁移、切片分析、结构比对而保留：

- `main.py`
- `main_index.json`
- `main_slices/`
- `slice_main.py`
- `build_index.py`
- `migration_manifest.md`
- `migration_state.md`

它们的作用更偏向：
- 历史版本参考
- 拆分过程记录
- 函数切片与索引辅助

**当前正式运行不依赖这些文件。**

---

## 15. 当前推荐的阅读顺序

如果你要继续维护这个项目，建议按下面顺序读代码：

1. `app/main.py`
2. `app/ui/pages/main_page.py`
3. `app/ui/pages/content_router.py`
4. `app/ui/pages/aggregated_view.py`
5. `app/ui/pages/single_server.py`
6. `app/ui/pages/single_ssh.py`
7. `app/services/probe.py`
8. `app/services/server_ops.py`
9. `app/services/xui_fetch.py`
10. `app/storage/bootstrap.py` / `app/storage/repositories.py`

这样最容易理解整条运行链。

---

## 16. 一句话总结

> 当前仓库已经完成从单文件形态向模块化结构的迁移，`app/` 是正式运行代码区；页面渲染、路由分发、SSH 管理、探针、订阅、部署、数据持久化都已具备明确职责边界。

