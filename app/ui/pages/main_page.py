import asyncio
import uuid

from fastapi import Request
from fastapi.responses import RedirectResponse
from nicegui import app, run, ui

from app.core.config import AUTO_REGISTER_SECRET
from app.core.logging import logger
from app.core.state import ADMIN_CONFIG, SERVERS_CACHE
from app.storage.repositories import save_admin_config
from app.ui.common.notifications import safe_copy_to_clipboard
from app.ui.components.sidebar import render_sidebar_content
from app.ui.pages.login_page import check_auth
from app.utils.geo import fetch_geo_from_ip
from app.utils.network import get_dynamic_origin


def main_page(request: Request):
    dark = ui.dark_mode()
    dark.enable()

    ui.colors(
        primary='#6366f1',
        secondary='#475569',
        accent='#8b5cf6',
        dark='#0f172a',
        positive='#10b981',
        negative='#ef4444',
        info='#3b82f6',
        warning='#f59e0b',
    )

    ui.add_head_html('''
        <link rel="stylesheet" href="/static/xterm.css" />
        <script src="/static/xterm.js"></script>
        <script src="/static/xterm-addon-fit.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js"></script>
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&family=Noto+Color+Emoji&display=swap" rel="stylesheet">
        <style>
            @font-face {
                font-family: 'Twemoji Country Flags';
                src: url('https://cdn.jsdelivr.net/npm/country-flag-emoji-polyfill@0.1/dist/TwemojiCountryFlags.woff2') format('woff2');
                unicode-range: U+1F1E6-1F1FF, U+1F3F4, U+E0062-E007F;
            }
            body {
                background-color: #0f172a !important;
                color: #e2e8f0 !important;
                font-family: 'Twemoji Country Flags', 'Noto Sans SC', "Roboto", "Helvetica", "Arial", sans-serif, "Noto Color Emoji";
            }
            .nicegui-connection-lost { display: none !important; }
            ::-webkit-scrollbar { width: 6px; height: 6px; }
            ::-webkit-scrollbar-track { background: #0f172a; }
            ::-webkit-scrollbar-thumb { background: #334155; border-radius: 3px; }
            ::-webkit-scrollbar-thumb:hover { background: #475569; }
            .q-card { background-color: #1e293b !important; border: 1px solid #334155 !important; }
            .q-drawer { background-color: #1e293b !important; }
        </style>
    ''')

    if not check_auth(request):
        return RedirectResponse('/login')

    try:
        current_ip = request.headers.get('X-Forwarded-For', request.client.host).split(',')[0].strip()
        current_device_id = request.cookies.get('fp_device_id', 'Unknown')
    except:
        current_ip = 'Unknown'
        current_device_id = 'Unknown'

    last_ip = app.storage.user.get('last_known_ip', '')
    last_device_id = app.storage.user.get('device_id', '')
    login_region = app.storage.user.get('login_region', '未知区域')

    async def reset_global_session(dialog_ref=None):
        new_ver = str(uuid.uuid4())[:8]
        ADMIN_CONFIG['session_version'] = new_ver
        await save_admin_config()
        if dialog_ref:
            dialog_ref.close()
        ui.notify('🔒 安全密钥已重置，正在强制所有设备下线...', type='warning', close_button=False)
        await asyncio.sleep(1.5)
        app.storage.user.clear()
        ui.navigate.to('/login')

    def trigger_geo_alert(new_ip, old_ip, old_loc, new_loc):
        app.storage.user['last_known_ip'] = new_ip
        with ui.dialog() as d, ui.card().classes('w-[450px] p-5 border-t-4 border-red-500 shadow-2xl bg-[#1e293b]'):
            with ui.row().classes('items-center gap-2 text-red-500 mb-2'):
                ui.icon('gpp_bad', size='md')
                ui.label('⚠️ 安全拦截：异地/异常设备登录').classes('font-bold text-lg')
            ui.label('系统检测到您的会话出现了异常跳变，可能存在 Cookie 劫持风险：').classes('text-sm text-slate-300')

            with ui.grid().classes('grid-cols-1 gap-2 my-4 bg-red-900/30 p-3 rounded border border-red-500/50'):
                ui.label(f'🔒 原始登录地: {old_ip} ({old_loc})').classes('text-xs font-mono font-bold text-slate-400')
                ui.label(f'🚨 当前请求源: {new_ip} ({new_loc})').classes('text-xs font-mono font-bold text-red-400')

            ui.label('如果您正在使用代理节点访问面板，请忽略；如果不是您本人的操作，请立即强制下线所有设备！').classes('text-xs text-red-300 font-bold')

            with ui.row().classes('w-full justify-end gap-3 mt-4'):
                ui.button('是本人操作 (忽略)', on_click=d.close).props('outline color=grey')
                ui.button('冻结并强制下线', color='red', icon='block', on_click=lambda: reset_global_session(d)).props('unelevated')
        d.open()

    async def run_security_check():
        if last_ip and last_ip != current_ip:
            if last_device_id and last_device_id == current_device_id:
                current_geo = await run.io_bound(fetch_geo_from_ip, current_ip)
                current_region = f"{current_geo[2]}-{current_geo[3]}" if current_geo else '未知区域'
                if current_region == login_region or '未知' in current_region:
                    app.storage.user['last_known_ip'] = current_ip
                else:
                    trigger_geo_alert(current_ip, last_ip, login_region, current_region)
            else:
                trigger_geo_alert(current_ip, last_ip, '旧设备', '未知新设备')

    ui.timer(0.5, run_security_check, once=True)

    with ui.left_drawer(value=True, fixed=True).classes('bg-[#1e293b] border-r border-slate-700').props('width=360 bordered') as drawer:
        render_sidebar_content()

    with ui.header().classes('bg-[#0f172a] text-white h-14 border-b border-slate-800 shadow-md'):
        with ui.row().classes('w-full items-center justify-between'):
            with ui.row().classes('items-center gap-2'):
                ui.button(icon='menu', on_click=lambda: drawer.toggle()).props('flat round dense color=white')
                ui.label('X-Fusion Panel').classes('text-lg font-bold ml-2 tracking-wide text-blue-400')

            with ui.row().classes('items-center gap-3 mr-2'):
                with ui.button(icon='gpp_bad', color='red', on_click=lambda: reset_global_session(None)).props('flat dense round size=sm').tooltip('安全重置'):
                    ui.badge('Reset', color='orange').props('floating rounded')

                with ui.button(icon='vpn_key', on_click=lambda: safe_copy_to_clipboard(AUTO_REGISTER_SECRET)).props('flat dense round size=sm color=grey-5').tooltip('复制通讯密钥'):
                    ui.badge('Key', color='red').props('floating rounded')

                ui.button(icon='logout', on_click=lambda: (app.storage.user.clear(), ui.navigate.to('/login'))).props('flat round dense color=grey-5').tooltip('退出登录')

    from app.ui.pages import content_router

    content_router.content_container = ui.column().classes('w-full h-full pl-4 pr-4 pt-4 overflow-y-auto bg-[#0f172a]')
    logger.info(f"[MainPage] content_container assigned | id={id(content_router.content_container)}")

    async def auto_init_system_settings():
        try:
            real_origin = get_dynamic_origin()
            if 'YOUR-DOMAIN' in real_origin:
                real_origin = await ui.run_javascript('return window.location.origin', timeout=3.0)

            if not real_origin:
                return

            stored_url = ADMIN_CONFIG.get('manager_base_url', '')
            need_save = False

            if 'session_version' not in ADMIN_CONFIG:
                ADMIN_CONFIG['session_version'] = 'init_v1'
                need_save = True

            if not stored_url or 'sijuly.nyc.mn' in stored_url or '127.0.0.1' in stored_url:
                ADMIN_CONFIG['manager_base_url'] = real_origin
                need_save = True

            if not ADMIN_CONFIG.get('probe_enabled'):
                ADMIN_CONFIG['probe_enabled'] = True
                need_save = True

            if need_save:
                await save_admin_config()
        except:
            pass

    ui.timer(1.0, auto_init_system_settings, once=True)

    async def restore_last_view():
        from app.ui.components.dashboard import load_dashboard_stats
        from app.ui.pages.content_router import refresh_content
        from app.ui.pages.probe_page import render_probe_page
        from app.ui.pages.subs_page import load_subs_view

        logger.info(f"[MainPage] restore_last_view start | stored_scope={app.storage.user.get('last_view_scope', 'DASHBOARD')} stored_data={app.storage.user.get('last_view_data', None)} content_container_id={id(content_router.content_container) if content_router.content_container else None}")

        last_scope = app.storage.user.get('last_view_scope', 'DASHBOARD')
        last_data_id = app.storage.user.get('last_view_data', None)
        target_data = last_data_id
        if last_scope in ['SINGLE', 'SSH_SINGLE'] and last_data_id:
            target_data = next((s for s in SERVERS_CACHE if s['url'] == last_data_id), None)
            if not target_data:
                last_scope = 'DASHBOARD'

        if last_scope == 'DASHBOARD':
            logger.info("[MainPage] restore_last_view branch=DASHBOARD")
            await load_dashboard_stats()
        elif last_scope == 'PROBE':
            logger.info("[MainPage] restore_last_view branch=PROBE")
            await render_probe_page()
        elif last_scope == 'SUBS':
            logger.info("[MainPage] restore_last_view branch=SUBS")
            await load_subs_view()
        else:
            logger.info(f"[MainPage] restore_last_view branch={last_scope} target_data={target_data}")
            await refresh_content(last_scope, target_data)
        logger.info(f'♻️ 自动恢复视图: {last_scope}')

    ui.timer(0.1, lambda: asyncio.create_task(restore_last_view()), once=True)
    logger.info('✅ UI 已就绪')
