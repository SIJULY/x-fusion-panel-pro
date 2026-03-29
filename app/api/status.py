from fastapi import Request
from nicegui import app, ui

from app.core.state import ADMIN_CONFIG, CURRENT_PROBE_TAB, PROBE_DATA_CACHE, SERVERS_CACHE
from app.ui.components.status_cards import render_status_card
from app.utils.geo import detect_country_group
from app.utils.network import get_real_ip_display


def is_mobile_device(request: Request) -> bool:
    """通过 User-Agent 判断是否为移动设备"""
    user_agent = request.headers.get('user-agent', '').lower()
    mobile_keywords = ['iphone', 'android', 'ipad', 'mobile', 'miui', 'huawei', 'honor']
    return any(k in user_agent for k in mobile_keywords)


async def status_page_router(request: Request):
    """
    路由分发器：
    1. 检测设备类型
    2. 手机端调用 render_mobile_status_page()
    3. 电脑端调用 render_desktop_status_page()
    """
    if is_mobile_device(request):
        await render_mobile_status_page()
    else:
        await render_desktop_status_page()


def register_status_page():
    ui.page('/status')(status_page_router)


async def render_desktop_status_page():
    ui.add_head_html('''
        <link href="https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&family=Noto+Color+Emoji&display=swap" rel="stylesheet">
        <style>
            body {
                background: #0b1121;
                color: #e2e8f0;
                font-family: 'Noto Sans SC', 'Noto Color Emoji', sans-serif;
            }
        </style>
    ''')

    total = len(SERVERS_CACHE)
    online = 0
    probe_online = 0
    region_set = set()

    for s in SERVERS_CACHE:
        url = s.get('url', '')
        probe = PROBE_DATA_CACHE.get(url, {})
        is_online = bool(
            probe and (
                probe.get('status') == 'online'
                or probe.get('cpu_usage') is not None
                or probe.get('last_updated')
            )
        ) or s.get('_status') == 'online'
        if is_online:
            online += 1
        if probe.get('status') == 'online':
            probe_online += 1
        try:
            region_set.add(detect_country_group(s.get('name', ''), s))
        except:
            pass

    with ui.column().classes('w-full min-h-screen bg-[#0b1121] text-slate-100 p-6 gap-6'):
        with ui.row().classes('w-full items-center justify-between'):
            with ui.column().classes('gap-1'):
                ui.label('X-Fusion Status').classes('text-3xl font-black text-white')
                ui.label('公开监控墙 / Public Status').classes('text-sm text-slate-400')
            ui.button('后台管理', icon='login', on_click=lambda: ui.navigate.to('/login')).props('outline color=blue')

        with ui.row().classes('w-full gap-4 flex-wrap'):
            render_status_card('总服务器', str(total), 'All Servers', 'text-blue-500', 'dns')
            render_status_card('当前在线', str(online), 'Online Now', 'text-green-500', 'bolt')
            render_status_card('探针在线', str(probe_online), 'Probe Active', 'text-purple-500', 'memory')
            render_status_card('分布区域', str(len([r for r in region_set if r])), 'Regions', 'text-orange-500', 'public')

        groups = ['ALL'] + ADMIN_CONFIG.get('probe_custom_groups', [])
        current_group = CURRENT_PROBE_TAB if CURRENT_PROBE_TAB in groups else 'ALL'

        with ui.row().classes('w-full gap-2 flex-wrap'):
            for group in groups:
                label = '全部' if group == 'ALL' else group
                color = 'blue' if group == current_group else 'grey'
                ui.button(label, on_click=lambda _, g=group: ui.navigate.to(f'/status?group={g}')).props(f'outline color={color}')

        with ui.column().classes('w-full gap-4'):
            filtered = [s for s in SERVERS_CACHE if current_group == 'ALL' or current_group in s.get('tags', [])]
            filtered.sort(key=lambda x: x.get('name', ''))

            if not filtered:
                with ui.card().classes('w-full p-10 bg-[#1e293b] border border-slate-700 items-center'):
                    ui.icon('inbox', size='3rem').classes('text-slate-600')
                    ui.label('暂无服务器').classes('text-slate-400')

            for s in filtered:
                url = s.get('url', '')
                probe = PROBE_DATA_CACHE.get(url, {})
                static = probe.get('static', {}) if isinstance(probe, dict) else {}
                is_online = bool(
                    probe and (
                        probe.get('status') == 'online'
                        or probe.get('cpu_usage') is not None
                        or probe.get('last_updated')
                    )
                ) or s.get('_status') == 'online'
                status_text = 'ONLINE' if is_online else 'OFFLINE'
                status_cls = 'text-green-400' if is_online else 'text-red-400'
                host_text = s.get('ssh_host') or get_real_ip_display(url)
                os_text = static.get('os', 'Linux')
                uptime = probe.get('uptime', '--') if isinstance(probe, dict) else '--'
                cpu = probe.get('cpu_usage', '--') if isinstance(probe, dict) else '--'
                mem = probe.get('mem_usage', '--') if isinstance(probe, dict) else '--'
                disk = probe.get('disk_usage', '--') if isinstance(probe, dict) else '--'

                with ui.card().classes('w-full p-5 bg-[#1e293b] border border-slate-700 rounded-xl shadow-sm gap-3'):
                    with ui.row().classes('w-full items-center justify-between'):
                        with ui.row().classes('items-center gap-3 flex-nowrap'):
                            ui.label(s.get('name', '未命名服务器')).classes('text-lg font-bold text-slate-100')
                            ui.label(status_text).classes(f'text-xs font-black {status_cls}')
                        ui.label(host_text).classes('text-xs font-mono text-slate-400')

                    with ui.row().classes('w-full gap-6 flex-wrap text-sm'):
                        ui.label(f'系统: {os_text}').classes('text-slate-300')
                        ui.label(f'在线时长: {uptime}').classes('text-slate-400')
                        ui.label(f'区域: {detect_country_group(s.get("name", ""), s)}').classes('text-slate-400')

                    with ui.row().classes('w-full gap-3 flex-wrap'):
                        render_status_card('CPU', f'{cpu}%', None, 'text-blue-500', 'developer_board')
                        render_status_card('内存', f'{mem}%', None, 'text-green-500', 'memory')
                        render_status_card('硬盘', f'{disk}%', None, 'text-purple-500', 'storage')


async def render_mobile_status_page():
    ui.add_head_html('''
        <style>
            body { background: #0d0d0d; color: #fff; }
        </style>
    ''')

    groups = ['ALL'] + ADMIN_CONFIG.get('probe_custom_groups', [])
    current_group = CURRENT_PROBE_TAB if CURRENT_PROBE_TAB in groups else 'ALL'
    filtered = [s for s in SERVERS_CACHE if current_group == 'ALL' or current_group in s.get('tags', [])]
    filtered.sort(key=lambda x: (0 if x.get('_status') == 'online' else 1, x.get('name', '')))

    with ui.column().classes('w-full min-h-screen bg-[#0d0d0d] text-white gap-0'):
        with ui.column().classes('w-full sticky top-0 z-10 bg-[#1a1a1a] border-b border-[#333] p-4 gap-2'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('X-Fusion Status').classes('text-lg font-black text-blue-400')
                ui.button(icon='login', on_click=lambda: ui.navigate.to('/login')).props('flat dense color=grey-5')
            online_count = len([s for s in SERVERS_CACHE if s.get('_status') == 'online'])
            ui.label(f'🟢 {online_count} ONLINE / {len(SERVERS_CACHE)} TOTAL').classes('text-[10px] font-bold text-gray-500 tracking-widest')
            with ui.row().classes('w-full gap-2 overflow-auto no-wrap'):
                for group in groups:
                    label = '全部' if group == 'ALL' else group
                    color = 'blue' if group == current_group else 'grey'
                    ui.button(label, on_click=lambda _, g=group: ui.navigate.to(f'/status?group={g}')).props(f'outline dense color={color}')

        with ui.column().classes('w-full p-3 gap-3'):
            if not filtered:
                ui.label('暂无服务器').classes('text-center text-gray-500 mt-10')

            for s in filtered:
                url = s.get('url', '')
                status = PROBE_DATA_CACHE.get(url, {})
                is_online = status.get('status') == 'online' or s.get('_status') == 'online'
                cpu = status.get('cpu_usage', 0)
                mem = status.get('mem_usage', 0)
                uptime = status.get('uptime', '--')
                load_1 = status.get('load_1', '0.0')
                host_text = s.get('ssh_host') or get_real_ip_display(url)

                with ui.card().classes('w-full bg-[#1a1a1a] border border-[#333] rounded-2xl p-4 gap-3'):
                    with ui.row().classes('items-center justify-between w-full'):
                        ui.label(s.get('name', '未命名服务器')).classes('text-base font-bold truncate')
                        ui.label('ACTIVE' if is_online else 'DOWN').classes(f'text-[10px] font-black {"text-green-500" if is_online else "text-red-400"}')

                    ui.label(host_text).classes('text-[11px] font-mono text-gray-500')

                    with ui.grid().classes('w-full grid-cols-2 gap-3'):
                        with ui.column().classes('bg-[#242424] rounded-xl p-3 gap-1'):
                            ui.label('CPU').classes('text-[11px] text-gray-500 font-bold')
                            ui.label(f'{cpu}%').classes('text-lg font-black font-mono')
                        with ui.column().classes('bg-[#242424] rounded-xl p-3 gap-1'):
                            ui.label('RAM').classes('text-[11px] text-gray-500 font-bold')
                            ui.label(f'{mem}%').classes('text-lg font-black font-mono')

                    with ui.row().classes('w-full justify-between pt-2 border-t border-[#333]'):
                        ui.label(f'在线时长：{uptime}').classes('text-[10px] font-bold text-green-500 font-mono')
                        ui.label(f'⚡ {load_1}').classes('text-[10px] text-gray-400 font-bold')
