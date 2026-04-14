import asyncio
import json

from nicegui import run, ui

from app.core.logging import logger
from app.core.state import ADMIN_CONFIG, NODES_DATA, PROBE_DATA_CACHE
from app.services.cloudflare import CloudflareHandler
from app.services.manager_factory import get_manager
from app.services.ssh import _ssh_exec_wrapper, get_ssh_client_sync
from app.services.xui_fetch import fetch_inbounds_safe
from app.storage.repositories import save_nodes_cache, save_servers
from app.ui.common.notifications import safe_copy_to_clipboard, safe_notify
from app.ui.dialogs.inbound_dialog import delete_inbound_with_confirm, open_inbound_dialog
from app.utils.encoding import generate_detail_config, generate_node_link
from app.utils.formatters import format_bytes
from app.ui.dialogs import server_dialog as _server_dialog


REFRESH_CURRENT_NODES = lambda: None


async def render_single_server_view(server_conf, force_refresh=False):
    global REFRESH_CURRENT_NODES

    SINGLE_COLS_NO_PING = _server_dialog.SINGLE_COLS_NO_PING
    XHTTP_UNINSTALL_SCRIPT = _server_dialog.XHTTP_UNINSTALL_SCRIPT
    _sync_resolve_ip = _server_dialog._sync_resolve_ip

    from app.ui.pages.content_router import content_container, refresh_content

    if content_container:
        content_container.clear()
        content_container.classes(remove='overflow-y-auto block justify-start', add='h-full flex-1 min-h-0 overflow-hidden flex flex-col p-4')

    with content_container:
        with ui.element('div').classes('w-full max-w-[1440px] mx-auto h-full flex-1 min-h-[calc(100vh-130px)] flex flex-col gap-0 flex-nowrap'):
            has_manager_access = (server_conf.get('url') and server_conf.get('user') and server_conf.get('pass')) or (server_conf.get('probe_installed') and server_conf.get('ssh_host'))
            mgr = None
            if has_manager_access:
                try:
                    mgr = get_manager(server_conf)
                except:
                    pass

            def to_float(value, default=0.0):
                try:
                    return float(value)
                except:
                    return default

            def clamp_percent(value):
                return max(0.0, min(100.0, to_float(value, 0.0)))

            def fmt_gb(value):
                if value in [None, '', '--']:
                    return '--'
                return f"{to_float(value):.2f} GB"

            def render_metric_row(label, value, sub_text='', value_color='text-slate-100'):
                with ui.row().classes('w-full items-center justify-between gap-4 px-4 py-3 rounded-xl bg-slate-800/55 border border-slate-700/80 shadow-sm transition-all hover:bg-slate-800/80 flex-nowrap'):
                    with ui.column().classes('gap-1 min-w-0 flex-1 justify-center'):
                        ui.label(label).classes('text-[11px] font-black uppercase tracking-[0.18em] text-slate-500 leading-none')
                        if sub_text:
                            ui.label(sub_text).classes('text-[10px] text-slate-400 break-all leading-tight mt-0.5')
                    ui.label(str(value)).classes(f'text-sm font-black text-right shrink-0 {value_color}')

            def render_section_header(title, icon, accent_class, desc='', right_renderer=None):
                with ui.row().classes('w-full items-center justify-between px-4 py-3 rounded-xl border border-slate-700 bg-slate-800/80 shadow-sm min-h-[64px]'):
                    with ui.row().classes('items-center gap-3'):
                        with ui.element('div').classes(f'w-10 h-10 rounded-xl flex items-center justify-center bg-slate-900 border border-slate-700 {accent_class}'):
                            ui.icon(icon).classes('text-xl')
                        with ui.column().classes('gap-0 justify-center'):
                            ui.label(title).classes('text-base font-black text-slate-100 tracking-wide')
                            if desc:
                                ui.label(desc).classes('text-[11px] text-slate-400')
                    if right_renderer:
                        right_renderer()

            def get_os_visual(os_name):
                name = str(os_name or '').lower()
                if 'ubuntu' in name:
                    return 'https://upload.wikimedia.org/wikipedia/commons/a/ab/Logo-ubuntu_cof-orange-hex.svg', 'Ubuntu'
                if 'debian' in name:
                    return 'https://upload.wikimedia.org/wikipedia/commons/6/66/Openlogo-debianV2.svg', 'Debian'
                if 'centos' in name:
                    return 'https://upload.wikimedia.org/wikipedia/commons/9/9e/CentOS_Icon.svg', 'CentOS'
                if 'red hat' in name:
                    return 'https://upload.wikimedia.org/wikipedia/commons/d/d8/Red_Hat_logo.svg', 'RedHat'
                if 'rocky' in name:
                    return 'https://upload.wikimedia.org/wikipedia/commons/1/11/Rocky_Linux_logo.svg', 'RockyLinux'
                if 'alma' in name:
                    return 'https://upload.wikimedia.org/wikipedia/commons/0/07/AlmaLinux_logo.svg', 'AlmaLinux'
                if 'alpine' in name:
                    return 'https://upload.wikimedia.org/wikipedia/commons/1/18/Alpine_Linux_logo.svg', 'Alpine'
                if 'arch' in name:
                    return 'https://upload.wikimedia.org/wikipedia/commons/a/a5/Archlinux-icon-crystal-64.svg', 'ArchLinux'

                return 'https://upload.wikimedia.org/wikipedia/commons/3/35/Tux.svg', 'Linux'

            def format_arch_text(arch_value):
                value = str(arch_value or '--').strip().lower()
                if value in ['x86_64', 'amd64']:
                    return 'AMD64 / x86_64'
                if value in ['aarch64', 'arm64']:
                    return 'ARM64 / AArch64'
                if value.startswith('arm'):
                    return 'ARM'
                if value in ['', '--']:
                    return '--'
                return str(arch_value)

            ssh_fallback_data = {}

            def _fetch_runtime_via_ssh():
                if not server_conf.get('ssh_host'):
                    return None
                client, msg = get_ssh_client_sync(server_conf)
                if not client:
                    return None
                try:
                    # 核心改动：用 SQLite 的表结构（基因）来绝对识别 3x-ui
                    remote_script = r'''python3 - <<'PY'
import json, os, platform, multiprocessing
info = {}
try:
    pretty = '--'
    if os.path.exists('/etc/os-release'):
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('PRETTY_NAME='):
                    pretty = line.split('=', 1)[1].strip().strip('"')
                    break

    uptime_text = '--'
    try:
        with open('/proc/uptime') as f:
            u = float(f.read().split()[0])
        d = int(u // 86400); h = int((u % 86400) // 3600); m = int((u % 3600) // 60)
        uptime_text = f'{d}天 {h}时 {m}分'
    except:
        pass
        
    xui_path = None
    is_3x_ui = False
    
    import sqlite3
    for p in ['/etc/x-ui/x-ui.db', '/usr/local/x-ui/bin/x-ui.db', '/usr/local/x-ui/x-ui.db']:
        if os.path.exists(p):
            try:
                conn = sqlite3.connect(p)
                res = conn.execute("SELECT value FROM settings WHERE key='webBasePath'").fetchone()
                if res and res[0]: xui_path = res[0].strip('/')
                
                # 终极黑科技：查找 3x-ui 独有的 client_traffics 表或 subURI 字段
                res_3x = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='client_traffics'").fetchone()
                res_sub = conn.execute("SELECT value FROM settings WHERE key='subURI'").fetchone()
                if res_3x or res_sub:
                    is_3x_ui = True
                    
                conn.close()
                if xui_path is not None: break
            except: pass

    info = {
        'os': pretty,
        'arch': platform.machine(),
        'cpu_cores': multiprocessing.cpu_count(),
        'uptime': uptime_text,
        'xui_path': xui_path,
        'is_3x_ui': is_3x_ui
    }
except Exception as e:
    info = {'error': str(e)}
print(json.dumps(info, ensure_ascii=False))
PY'''
                    stdin, stdout, stderr = client.exec_command(remote_script, timeout=15)
                    raw = stdout.read().decode('utf-8', errors='ignore').strip()
                    if raw:
                        parsed = json.loads(raw.splitlines()[-1])
                        if isinstance(parsed, dict) and not parsed.get('error'):
                            return parsed
                except Exception as e:
                    logger.warning(f'初始获取静态信息失败: {e}')
                finally:
                    try:
                        client.close()
                    except:
                        pass
                return None

            async def run_ssh_fallback():
                remote_data = await run.io_bound(_fetch_runtime_via_ssh)
                if isinstance(remote_data, dict):
                    ssh_fallback_data.update(remote_data)
                    
                    need_save = False
                    if 'is_3x_ui' in remote_data and server_conf.get('is_3x_ui') != remote_data['is_3x_ui']:
                        server_conf['is_3x_ui'] = remote_data['is_3x_ui']
                        need_save = True
                    
                    if 'xui_path' in remote_data:
                        detected_prefix = f"/{remote_data['xui_path']}" if remote_data['xui_path'] else ""
                        if server_conf.get('prefix') != detected_prefix:
                            server_conf['prefix'] = detected_prefix
                            need_save = True
                            logger.info(f"[AutoDetect] Server path automatically self-healed to: '{detected_prefix}'")
                            
                    if need_save:
                        asyncio.create_task(save_servers())
                        if has_manager_access:
                            asyncio.create_task(reload_and_refresh_ui())

            ui.timer(0.1, run_ssh_fallback, once=True)

            def get_cached_snapshot():
                import time as _time
                probe_cache = PROBE_DATA_CACHE.get(server_conf['url'], {}) or {}
                static = probe_cache.get('static', {}) or {}

                now_ts = _time.time()
                is_stale = bool(probe_cache and (now_ts - probe_cache.get('last_updated', 0) > 20))

                mem_total = to_float(probe_cache.get('mem_total', 0.0))
                mem_usage_pct = clamp_percent(probe_cache.get('mem_usage', 0.0))
                mem_used = round(mem_total * mem_usage_pct / 100.0, 2)
                swap_total = to_float(probe_cache.get('swap_total', 0.0))
                swap_free = to_float(probe_cache.get('swap_free', 0.0))

                disk_total = to_float(probe_cache.get('disk_total', 0.0))
                disk_usage_pct = clamp_percent(probe_cache.get('disk_usage', 0.0))
                disk_used = round(disk_total * disk_usage_pct / 100.0, 2)

                cpu_usage_pct = 0.0 if is_stale else clamp_percent(probe_cache.get('cpu_usage', 0.0))
                cpu_cores = probe_cache.get('cpu_cores') or static.get('cpu_cores') or ssh_fallback_data.get('cpu_cores') or 0

                uptime_val = probe_cache.get('uptime') or ssh_fallback_data.get('uptime') or '--'
                if is_stale:
                    uptime_val = '⚠️ 机器已离线'

                return {
                    'os': static.get('os') or ssh_fallback_data.get('os') or '--',
                    'arch': static.get('arch') or ssh_fallback_data.get('arch') or '--',
                    'uptime': uptime_val,
                    'cpu_cores': cpu_cores,
                    'cpu_usage_pct': cpu_usage_pct,
                    'mem_total_gb': mem_total,
                    'mem_free_gb': max(mem_total - mem_used, 0.0) if mem_total else 0.0,
                    'mem_used_gb': mem_used,
                    'mem_cache_gb': to_float(probe_cache.get('mem_cache_gb', 0.0)),
                    'mem_usage_pct': 0.0 if is_stale else mem_usage_pct,
                    'swap_total_gb': swap_total,
                    'swap_free_gb': swap_free,
                    'swap_used_gb': max(swap_total - swap_free, 0.0),
                    'swap_usage_pct': 0.0 if is_stale else clamp_percent((max(swap_total - swap_free, 0.0) / swap_total * 100.0) if swap_total else 0.0),
                    'disk_device': probe_cache.get('disk_device') or '/',
                    'disk_total_gb': disk_total,
                    'disk_free_gb': max(disk_total - disk_used, 0.0) if disk_total else 0.0,
                    'disk_used_gb': disk_used,
                    'disk_usage_pct': disk_usage_pct,
                    'has_probe': bool(probe_cache)
                }

            server_dialog_key = server_conf.get('url') or server_conf.get('ssh_host') or str(id(server_conf))

            def open_ssh_page():
                if not server_conf.get('ssh_host'):
                    safe_notify('当前服务器未配置 SSH 主机，无法打开终端', 'warning')
                    return
                try: client = ui.context.client
                except: client = None
                asyncio.create_task(refresh_content('SSH_SINGLE', server_conf, manual_client=client))

            @ui.refreshable
            async def render_node_list():
                xui_nodes = await fetch_inbounds_safe(server_conf, force_refresh=False)
                if xui_nodes is None: xui_nodes = []
                custom_nodes = server_conf.get('custom_nodes', [])
                all_nodes = xui_nodes + custom_nodes

                if not all_nodes:
                    with ui.column().classes('w-full py-12 items-center justify-center opacity-50'):
                        msg = '暂无节点 (可直接新建)' if has_manager_access else '暂无数据'
                        ui.icon('inbox', size='4rem').classes('text-slate-600 mb-2')
                        ui.label(msg).classes('text-slate-500 text-sm')
                else:
                    for n in all_nodes:
                        is_custom = n.get('_is_custom', False)
                        is_ssh_mode = (not is_custom) and (server_conf.get('probe_installed') and server_conf.get('ssh_host'))
                        row_3d_cls = 'grid w-full gap-4 py-3 px-2 mb-2 items-center group bg-[#1e293b] rounded-xl border border-slate-700 border-b-[3px] shadow-sm transition-all duration-150 ease-out hover:shadow-md hover:border-blue-500 hover:bg-[#252f45] active:border-b active:translate-y-[2px] active:shadow-none cursor-default'
                        with ui.element('div').classes(row_3d_cls).style(SINGLE_COLS_NO_PING):
                            ui.label(n.get('remark', '未命名')).classes('font-bold truncate w-full text-left pl-2 text-slate-300 text-sm group-hover:text-white')
                            if is_custom:
                                ui.label('独立').classes('text-[10px] bg-purple-900/50 text-purple-300 font-bold px-2 py-0.5 rounded-full w-fit mx-auto border border-purple-700')
                            elif is_ssh_mode:
                                ui.label('Root').classes('text-[10px] bg-teal-900/50 text-teal-300 font-bold px-2 py-0.5 rounded-full w-fit mx-auto border border-teal-700')
                            else:
                                ui.label('API').classes('text-[10px] bg-slate-700 text-slate-300 font-bold px-2 py-0.5 rounded-full w-fit mx-auto border border-slate-600')
                            traffic = format_bytes(n.get('up', 0) + n.get('down', 0)) if not is_custom else '--'
                            ui.label(traffic).classes('text-xs text-slate-400 w-full text-center font-mono font-bold')
                            proto = str(n.get('protocol', 'unk')).upper()
                            ui.label(proto).classes('text-[11px] font-extrabold w-full text-center text-slate-500 tracking-wide')
                            ui.label(str(n.get('port', 0))).classes('text-blue-400 font-mono w-full text-center font-bold text-xs')
                            is_enable = n.get('enable', True)
                            with ui.row().classes('w-full justify-center items-center gap-1'):
                                color = 'green' if is_enable else 'red'
                                text = '启用' if is_enable else '停止'
                                ui.element('div').classes(f'w-2 h-2 rounded-full bg-{color}-500 shadow-[0_0_5px_rgba(0,0,0,0.5)]')
                                ui.label(text).classes(f'text-[10px] font-bold text-{color}-400')
                            with ui.row().classes('gap-2 justify-center w-full no-wrap opacity-60 group-hover:opacity-100 transition'):
                                btn_props = 'flat dense size=sm round'
                                raw_link = n.get('_raw_link', '') or generate_node_link(n, server_conf['url'])
                                if raw_link:
                                    ui.button(icon='link', on_click=lambda u=raw_link: safe_copy_to_clipboard(u)).props(btn_props).tooltip('复制原始链接').classes('text-slate-400 hover:bg-slate-600 hover:text-cyan-400')

                                async def copy_detail_action(node_item=n):
                                    host = server_conf.get('url', '').replace('http://', '').replace('https://', '').split(':')[0]
                                    text = generate_detail_config(node_item, host)
                                    if text and not str(text).startswith('//'):
                                        await safe_copy_to_clipboard(text)
                                    else:
                                        ui.notify(text or '该协议不支持生成明文配置', type='warning')

                                ui.button(icon='description', on_click=copy_detail_action).props(btn_props).tooltip('复制明文配置').classes('text-slate-400 hover:bg-slate-600 hover:text-orange-400')

                                if is_custom:
                                    ui.button(icon='edit', on_click=lambda node=n: open_edit_custom_node(node)).props(btn_props).classes('text-blue-400 hover:bg-slate-600')
                                    ui.button(icon='delete', on_click=lambda node=n: uninstall_and_delete(node)).props(btn_props).classes('text-red-400 hover:bg-slate-600')
                                elif has_manager_access:
                                    async def on_edit_success():
                                        ui.notify('修改成功')
                                        await reload_and_refresh_ui()
                                        
                                    # 核心改动：保证 lambda 调用时，获取的是 server_conf 里最新的 'is_3x_ui' 状态，而不是闭包写死的旧值
                                    ui.button(icon='edit', on_click=lambda i=n: open_inbound_dialog(mgr, i, on_edit_success, is_3x_ui=server_conf.get('is_3x_ui', False))).props(btn_props).classes('text-blue-400 hover:bg-slate-600')
                                    
                                    async def on_del_success():
                                        ui.notify('删除成功')
                                        await reload_and_refresh_ui()
                                    ui.button(icon='delete', on_click=lambda i=n: delete_inbound_with_confirm(mgr, i['id'], i.get('remark', ''), on_del_success)).props(btn_props).classes('text-red-400 hover:bg-slate-600')
                                else:
                                    ui.icon('lock', size='xs').classes('text-slate-600').tooltip('无权限')

            async def reload_and_refresh_ui():
                if mgr and hasattr(mgr, '_exec_remote_script'):
                    try:
                        new_inbounds = await run.io_bound(lambda: asyncio.run(mgr.get_inbounds())) if not asyncio.iscoroutinefunction(mgr.get_inbounds) else await mgr.get_inbounds()
                        if new_inbounds is not None:
                            NODES_DATA[server_conf['url']] = new_inbounds
                            server_conf['_status'] = 'online'
                            await save_nodes_cache()
                    except: pass
                else:
                    try: await fetch_inbounds_safe(server_conf, force_refresh=True)
                    except: pass
                render_node_list.refresh()

            REFRESH_CURRENT_NODES = reload_and_refresh_ui
            _server_dialog.REFRESH_CURRENT_NODES = reload_and_refresh_ui

            def open_edit_custom_node(node_data):
                with ui.dialog() as d, ui.card().classes('w-96 p-4'):
                    ui.label('编辑节点备注').classes('text-lg font-bold mb-4')
                    name_input = ui.input('节点名称', value=node_data.get('remark', '')).classes('w-full')
                    async def save():
                        node_data['remark'] = name_input.value.strip()
                        await save_servers()
                        safe_notify('修改已保存', 'positive')
                        d.close()
                        render_node_list.refresh()
                    with ui.row().classes('w-full justify-end mt-4'):
                        ui.button('取消', on_click=d.close).props('flat')
                        ui.button('保存', on_click=save).classes('bg-blue-600 text-white')
                d.open()

            async def uninstall_and_delete(node_data):
                with ui.dialog() as d, ui.card().classes('w-96 p-6'):
                    with ui.row().classes('items-center gap-2 text-red-600 mb-2'):
                        ui.icon('delete_forever', size='md')
                        ui.label('卸载并清理环境').classes('font-bold text-lg')
                    async def start_uninstall():
                        d.close()
                        notification = ui.notification(message='正在执行卸载与清理...', timeout=0, spinner=True)
                        success, output = await run.io_bound(lambda: _ssh_exec_wrapper(server_conf, XHTTP_UNINSTALL_SCRIPT))
                        notification.dismiss()
                        if success: safe_notify('✅ 服务已卸载，进程已清理', 'positive')
                        if 'custom_nodes' in server_conf and node_data in server_conf['custom_nodes']:
                            server_conf['custom_nodes'].remove(node_data)
                            await save_servers()
                        await reload_and_refresh_ui()
                    with ui.row().classes('w-full justify-end mt-6 gap-2'):
                        ui.button('取消', on_click=d.close).props('flat color=grey')
                        ui.button('确认执行', color='red', on_click=start_uninstall).props('unelevated')
                d.open()

            btn_3d_base = 'text-xs font-bold text-white rounded-lg px-4 py-2 border-b-4 active:border-b-0 active:translate-y-[4px] transition-all duration-150 shadow-sm'
            btn_blue = f'bg-blue-600 border-blue-800 hover:bg-blue-500 {btn_3d_base}'
            btn_green = f'bg-green-600 border-green-800 hover:bg-green-500 {btn_3d_base}'

            with ui.row().classes('w-full justify-between items-center bg-[#1e293b] p-4 rounded-xl border border-slate-700 border-b-[4px] border-b-slate-800 shadow-sm flex-shrink-0'):
                with ui.row().classes('items-center gap-4'):
                    sys_icon = 'computer' if 'Oracle' in server_conf.get('name', '') else 'dns'
                    with ui.element('div').classes('p-3 bg-[#0f172a] rounded-lg border border-slate-600 shadow-inner'):
                        ui.icon(sys_icon, size='md').classes('text-blue-400')
                    with ui.column().classes('gap-1'):
                        with ui.row().classes('items-center gap-3 no-wrap'):
                            ui.label(server_conf.get('name', '未命名服务器')).classes('text-xl font-black text-slate-200 leading-tight tracking-tight')
                        with ui.row().classes('items-center gap-2 flex-wrap'):
                            raw_host = server_conf.get('ssh_host') or server_conf.get('url', '').replace('http://', '').replace('https://', '').split(':')[0]
                            ui.label(raw_host).classes('text-xs font-mono font-bold text-slate-400 bg-[#0f172a] px-2 py-0.5 rounded border border-slate-700')
                            @ui.refreshable
                            def live_status_badge():
                                import time as _time
                                is_online = False
                                now_ts = _time.time()
                                probe_cache = PROBE_DATA_CACHE.get(server_conf['url'])
                                if probe_cache and (now_ts - probe_cache.get('last_updated', 0) < 20): is_online = True
                                elif server_conf.get('_status') == 'online': is_online = True
                                ui.badge('Online' if is_online else 'Offline', color='green' if is_online else 'grey').props('rounded outline size=xs')
                            live_status_badge()
                            ui.timer(3.0, live_status_badge.refresh)
                with ui.row().classes('items-center justify-end'):
                    if server_conf.get('ssh_host'):
                        ui.button('进入 SSH 终端', icon='terminal', on_click=open_ssh_page).props('flat round size=sm color=green').classes('bg-[#0f172a] border border-slate-700 shadow-md px-4 py-2 font-bold')

            ui.element('div').classes('h-4 flex-shrink-0')

            vps_container = ui.element('div').classes('w-full flex-shrink-0 p-0 gap-0 rounded-xl border border-slate-700 border-b-[4px] border-b-slate-800 shadow-lg overflow-hidden bg-slate-900 flex flex-col')
            with vps_container:
                with ui.row().classes('w-full items-center justify-between px-4 py-3 border-b border-slate-700 bg-[#0f172a]'):
                    with ui.row().classes('items-center gap-2'):
                        ui.icon('monitor_heart').classes('text-cyan-400')
                        ui.label('VPS 运行信息').classes('text-sm font-black text-slate-300 uppercase tracking-wide')
                    @ui.refreshable
                    def render_sync_status():
                        import time as _time
                        probe_cache = PROBE_DATA_CACHE.get(server_conf['url'])
                        if probe_cache and (_time.time() - probe_cache.get('last_updated', 0)) <= 20:
                            ui.label('🟢 探针实时同步中').classes('text-xs text-emerald-400 font-bold tracking-wide')
                        else:
                            ui.label('🔴 探针已断联 (离线)').classes('text-xs text-red-500 font-bold tracking-wide')
                    render_sync_status()

                with ui.column().classes('w-full gap-4 p-4 bg-[#111827]'):
                    with ui.grid().classes('w-full grid-cols-1 lg:grid-cols-2 gap-4 items-stretch'):
                        with ui.card().classes('w-full h-full bg-[#0f172a] border border-slate-700 rounded-2xl shadow-md p-4 gap-4'):
                            snap = get_cached_snapshot()
                            os_logo_url, _ = get_os_visual(snap['os'])
                            render_section_header('系统信息', 'developer_board', 'text-blue-400', '操作系统 / 架构 / 在线时间', right_renderer=lambda: ui.label(f"{snap['cpu_cores']} C").classes('text-xs font-bold text-blue-400 bg-blue-400/10 px-2 py-1 rounded-md'))
                            with ui.row().classes('w-full items-center justify-center gap-3 py-3 px-4 rounded-xl bg-slate-800/40 border border-slate-700 shadow-sm'):
                                ui.element('img').props(f'src="{os_logo_url}"').classes('w-6 h-6 object-contain shrink-0')
                                ui.label(snap['os']).classes('text-sm font-black text-slate-50 truncate')
                            @ui.refreshable
                            def render_sys_dyn():
                                snap = get_cached_snapshot()
                                with ui.row().classes('w-full items-center justify-between gap-4 px-4 py-3 rounded-xl bg-slate-800/55 border border-slate-700/80 shadow-sm'):
                                    ui.label('CPU 使用率').classes('text-[11px] font-black uppercase tracking-[0.18em] text-slate-500 leading-none shrink-0')
                                    pct = snap.get('cpu_usage_pct', 0.0)
                                    bar_color = 'bg-emerald-500/80' if pct < 60 else ('bg-amber-500/80' if pct < 85 else 'bg-red-500/80')
                                    with ui.element('div').classes('w-1/2 max-w-[150px] ml-auto bg-slate-900 rounded-md h-[18px] relative overflow-hidden border border-slate-700/50'):
                                        ui.element('div').classes(f'h-full {bar_color} transition-all duration-500').style(f'width: {pct}%')
                                        ui.label(f'{pct:.1f}%').classes('absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white')
                                render_metric_row('处理器架构', format_arch_text(snap['arch']), value_color='text-cyan-400')
                                render_metric_row('在线运行时间', snap['uptime'], value_color='text-emerald-400')
                            render_sys_dyn()
                        
                        with ui.card().classes('w-full h-full bg-[#0f172a] border border-slate-700 rounded-2xl shadow-md p-4 gap-4'):
                            @ui.refreshable
                            def render_mem_card():
                                snap = get_cached_snapshot()
                                render_section_header('内存信息', 'memory', 'text-green-400', '系统内存 / 缓存 / SWAP 使用情况', right_renderer=lambda: ui.label(f"{fmt_gb(snap['mem_total_gb'])}").classes('text-xs font-bold text-emerald-400 bg-emerald-400/10 px-2 py-1 rounded-md'))
                                with ui.column().classes('w-full flex-1 gap-3 justify-center mt-1'):
                                    with ui.row().classes('w-full items-center justify-between gap-4 px-4 py-3 rounded-xl bg-slate-800/55 border border-slate-700/80 shadow-sm'):
                                        ui.label('真实使用内存').classes('text-[11px] font-black uppercase tracking-[0.18em] text-slate-500 leading-none shrink-0')
                                        pct, val = snap['mem_usage_pct'], fmt_gb(snap['mem_used_gb'])
                                        bar_color = 'bg-amber-500/80' if pct > 80 else 'bg-blue-500/80'
                                        with ui.element('div').classes('w-1/2 max-w-[150px] ml-auto bg-slate-900 rounded-md h-[18px] relative overflow-hidden border border-slate-700/50'):
                                            ui.element('div').classes(f'h-full {bar_color} transition-all duration-500').style(f'width: {pct}%')
                                            ui.label(f'{val} ({pct:.0f}%)').classes('absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white')
                                    render_metric_row('系统缓存', fmt_gb(snap['mem_cache_gb']), value_color='text-teal-400')
                                    render_metric_row('SWAP 虚拟内存', f"{fmt_gb(snap['swap_used_gb'])} / {fmt_gb(snap['swap_total_gb'])}", f"使用率 {snap['swap_usage_pct']:.0f}%", value_color='text-purple-400')
                            render_mem_card()
                
                def safe_refresh():
                    try:
                        if not vps_container.is_deleted:
                            render_sync_status.refresh()
                            render_sys_dyn.refresh()
                            render_mem_card.refresh()
                    except: pass
                ui.timer(2.0, safe_refresh)

            ui.element('div').classes('h-6 flex-shrink-0')

            with ui.element('div').classes('w-full flex-1 min-h-[300px] flex flex-col p-0 rounded-xl border border-slate-700 border-b-[4px] border-b-slate-800 shadow-sm overflow-hidden bg-[#1e293b]'):
                with ui.row().classes('w-full items-center justify-between p-3 bg-[#0f172a] border-b border-slate-700 gap-3 flex-wrap flex-shrink-0'):
                    with ui.row().classes('items-center gap-2'):
                        ui.label('节点列表').classes('text-sm font-black text-slate-400 uppercase tracking-wide ml-1')
                        if server_conf.get('probe_installed') and server_conf.get('ssh_host'):
                            ui.badge('Root 模式', color='teal').props('outline rounded size=xs')
                    with ui.row().classes('items-center gap-2 flex-wrap justify-end'):
                        from app.services.deployment import open_deploy_hysteria_dialog, open_deploy_snell_dialog, open_deploy_xhttp_dialog
                        ui.button('一键部署 XHTTP', icon='rocket_launch', on_click=lambda: open_deploy_xhttp_dialog(server_conf, reload_and_refresh_ui)).props('unelevated').classes(btn_blue)
                        ui.button('一键部署 Hy2', icon='bolt', on_click=lambda: open_deploy_hysteria_dialog(server_conf, reload_and_refresh_ui)).props('unelevated').classes(btn_blue)
                        ui.button('一键部署 Snell', icon='security', on_click=lambda: open_deploy_snell_dialog(server_conf, reload_and_refresh_ui)).props('unelevated').classes(btn_blue)
                        
                        if has_manager_access:
                            async def on_add_success():
                                ui.notify('添加节点成功')
                                await reload_and_refresh_ui()
                            
                            # 核心改动：保证 lambda 调用时获取最新的 'is_3x_ui' 状态
                            ui.button('新建 XUI 节点', icon='add', on_click=lambda: open_inbound_dialog(mgr, None, on_add_success, is_3x_ui=server_conf.get('is_3x_ui', False))).props('unelevated').classes(btn_green)
                        else:
                            ui.button('探针只读', icon='visibility', on_click=None).props('unelevated disabled').classes('bg-slate-700 text-slate-400 rounded-lg px-4 py-2 border-b-4 border-slate-800 text-xs font-bold opacity-70')

                with ui.element('div').classes('grid w-full gap-4 font-bold text-slate-500 border-b border-slate-700 pb-2 pt-2 px-2 text-xs uppercase tracking-wider bg-[#1e293b] flex-shrink-0').style(SINGLE_COLS_NO_PING):
                    ui.label('节点名称').classes('text-left pl-2')
                    for h in ['类型', '流量', '协议', '端口', '状态', '操作']: ui.label(h).classes('text-center')

                with ui.element('div').classes('w-full relative flex-1 min-h-0'):
                    with ui.element('div').classes('absolute inset-0 bg-[#0f172a]'):
                        with ui.scroll_area().classes('w-full h-full p-1'):
                            await render_node_list()

            if has_manager_access and not NODES_DATA.get(server_conf['url']):
                ui.timer(0.2, lambda: asyncio.create_task(reload_and_refresh_ui()), once=True)

__all__ = ['render_single_server_view']
