from nicegui import ui

from app.core.state import DNS_CACHE, DNS_WAITING_LABELS
from app.ui.common.notifications import safe_copy_to_clipboard
from app.utils.encoding import generate_detail_config, generate_node_link
from app.utils.formatters import format_bytes
from app.utils.geo import detect_country_group
from app.utils.network import get_real_ip_display


def bind_ip_label(url, label):
    """
    ✨ 新增辅助函数：将 UI Label 绑定到 DNS 监听列表
    用法：在创建 ui.label 后调用 bind_ip_label(url, label)
    """
    try:
        host = url.split('://')[-1].split(':')[0]
        import re
        if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", host):
            return
        if host in DNS_CACHE:
            return

        if host not in DNS_WAITING_LABELS:
            DNS_WAITING_LABELS[host] = []
        DNS_WAITING_LABELS[host].append(label)
    except:
        pass


def show_custom_node_info(node):
    with ui.dialog() as d, ui.card().classes('w-full max-w-sm'):
        ui.label(node.get('remark', '节点详情')).classes('text-lg font-bold mb-2')

        link = node.get('_raw_link') or node.get('link') or "无法获取链接"

        with ui.row().classes('w-full bg-gray-100 p-3 rounded break-all font-mono text-xs mb-4'):
            ui.label(link)

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('复制', icon='content_copy', on_click=lambda: [safe_copy_to_clipboard(link), d.close()])
            ui.button('关闭', on_click=d.close).props('flat')
    d.open()


def draw_row(srv, node, css_style, use_special_mode, is_first=True):
    card_cls = 'grid w-full gap-4 py-3 px-4 items-center group relative bg-[#1e293b] rounded-xl border border-slate-700 border-b-[3px] shadow-sm transition-all duration-150 ease-out hover:shadow-md hover:border-blue-500 hover:bg-[#252f45] hover:-translate-y-[1px] mb-2'

    with ui.element('div').classes(card_cls).style(css_style):
        srv_name = srv.get('name', '未命名')
        if not is_first:
            ui.label(srv_name).classes('text-xs text-slate-700 truncate w-full text-left pl-2 font-mono')
        else:
            ui.label(srv_name).classes('text-xs text-slate-400 font-bold truncate w-full text-left pl-2 font-mono group-hover:text-white')

        if not node:
            is_probe = srv.get('probe_installed', False)
            msg = '同步中...' if not is_probe else '无节点配置'
            ui.label(msg).classes('font-bold truncate text-slate-600 text-xs italic')
            ui.label('--').classes('text-center text-slate-700')
            ui.label('--').classes('text-center text-slate-700')
            ui.label('UNK').classes('text-center text-slate-700 font-bold text-[10px]')
            ui.label('--').classes('text-center text-slate-700')
            if not use_special_mode:
                ui.element('div')
            with ui.row().classes('gap-1 justify-center w-full no-wrap'):
                ui.button(icon='settings', on_click=lambda _, s=srv: __import__('asyncio').create_task(_refresh_single_server(s))).props('flat dense size=sm round color=grey')
            return

        remark = node.get('ps') or node.get('remark') or '未命名节点'
        ui.label(remark).classes('font-bold truncate w-full text-left pl-2 text-slate-300 text-sm group-hover:text-blue-300')

        if use_special_mode:
            with ui.row().classes('w-full justify-center items-center gap-1.5 no-wrap'):
                is_online = srv.get('_status') == 'online'
                color = 'text-green-500' if is_online else 'text-red-500'
                if not srv.get('probe_installed') and not node.get('_is_custom'):
                    color = 'text-orange-400'
                ui.icon('bolt').classes(f'{color} text-sm')
                display_ip = get_real_ip_display(srv['url'])
                ip_lbl = ui.label(display_ip).classes('text-[10px] font-mono text-slate-400 font-bold bg-[#0f172a] px-1.5 py-0.5 rounded select-all border border-slate-700')
                bind_ip_label(srv['url'], ip_lbl)
        else:
            group_display = srv.get('group', '默认分组')
            if group_display in ['默认分组', '自动注册', '未分组', '自动导入']:
                try:
                    detected = detect_country_group(srv.get('name', ''), None)
                    if detected:
                        group_display = detected
                except:
                    pass
            ui.label(group_display).classes('text-xs font-bold text-slate-400 w-full text-center truncate bg-[#0f172a] px-2 py-0.5 rounded-full border border-slate-700')

        if node.get('_is_custom'):
            ui.label('-').classes('text-xs text-slate-600 w-full text-center font-mono')
        else:
            traffic = sum([node.get('up', 0), node.get('down', 0)])
            ui.label(format_bytes(traffic)).classes('text-xs text-blue-400 w-full text-center font-mono font-bold')

        proto = str(node.get('protocol', 'unk')).upper()
        if 'HYSTERIA' in proto:
            proto = 'HY2'
        if 'SHADOWSOCKS' in proto:
            proto = 'SS'
        proto_color = 'text-slate-500'
        if 'HY2' in proto:
            proto_color = 'text-purple-400'
        elif 'VLESS' in proto:
            proto_color = 'text-blue-400'
        elif 'VMESS' in proto:
            proto_color = 'text-green-400'
        elif 'TROJAN' in proto:
            proto_color = 'text-orange-400'
        ui.label(proto).classes(f'text-[11px] font-extrabold w-full text-center {proto_color} tracking-wide')

        port_val = str(node.get('port', 0))
        ui.label(port_val).classes('text-slate-400 font-mono w-full text-center font-bold text-xs')

        if not use_special_mode:
            with ui.element('div').classes('flex justify-center w-full'):
                is_enable = node.get('enable', True)
                dot_cls = "bg-green-500 shadow-[0_0_6px_rgba(34,197,94,0.6)]" if is_enable else "bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.6)]"
                ui.element('div').classes(f'w-2 h-2 rounded-full {dot_cls}')

        with ui.row().classes('gap-1 justify-center w-full no-wrap'):
            async def copy_link(n=node, s=srv):
                link = n.get('_raw_link') or n.get('link')
                if not link:
                    link = generate_node_link(n, s['url'])
                await safe_copy_to_clipboard(link)

            ui.button(icon='content_copy', on_click=copy_link).props('flat dense size=sm round').tooltip('复制链接').classes('text-slate-500 hover:text-blue-400 hover:bg-slate-700')

            async def copy_detail():
                host = srv['url'].split('://')[-1].split(':')[0]
                text = generate_detail_config(node, host)
                if text:
                    await safe_copy_to_clipboard(text)
                else:
                    ui.notify('不支持生成配置', type='warning')

            ui.button(icon='description', on_click=copy_detail).props('flat dense size=sm round').tooltip('复制明文配置').classes('text-slate-500 hover:text-orange-400 hover:bg-slate-700')
            ui.button(icon='settings', on_click=lambda _, s=srv: __import__('asyncio').create_task(_refresh_single_server(s))).props('flat dense size=sm round').tooltip('管理服务器').classes('text-slate-500 hover:text-white hover:bg-slate-700')


async def _refresh_single_server(server):
    from app.ui.pages.content_router import refresh_content

    await refresh_content('SINGLE', server)
