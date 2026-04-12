import asyncio
import json
import time
import uuid

from nicegui import run, ui

from app.core.config import AUTO_COUNTRY_MAP
from app.core.logging import logger
from app.core.state import (
    ADMIN_CONFIG,
    CURRENT_VIEW_STATE,
    EXPANDED_GROUPS,
    NODES_DATA,
    PING_TREND_CACHE,
    PROBE_DATA_CACHE,
    REFRESH_CURRENT_NODES,
    SERVERS_CACHE,
    SIDEBAR_UI_REFS,
)
from app.services.cloudflare import CloudflareHandler
from app.services.manager_factory import get_manager
from app.services.probe import install_probe_on_server
from app.services.server_ops import fast_resolve_single_server, generate_smart_name
from app.services.ssh import WebSSH, _ssh_exec_wrapper, get_ssh_client_sync
from app.services.subscriptions import copy_group_link
from app.services.xui_fetch import fetch_inbounds_safe
from app.storage.repositories import save_admin_config, save_nodes_cache, save_servers
from app.ui.common.notifications import safe_copy_to_clipboard, safe_notify
from app.ui.components.dashboard import refresh_dashboard_ui
from app.ui.components.server_rows import draw_row
from app.ui.components.sidebar import render_sidebar_content, render_single_sidebar_row
from app.ui.dialogs.inbound_dialog import delete_inbound_with_confirm, open_inbound_dialog
from app.utils.encoding import generate_detail_config, generate_node_link
from app.utils.formatters import format_bytes, smart_sort_key
from app.utils.geo import detect_country_group


COLS_NO_PING = 'grid-template-columns: 2fr 2fr 1.5fr 1fr 0.8fr 0.8fr 0.5fr 1.5fr; align-items: center;'
COLS_SPECIAL_WITH_PING = 'grid-template-columns: 2fr 2fr 1.5fr 1fr 0.8fr 0.8fr 1.5fr; align-items: center;'
SINGLE_COLS_NO_PING = 'grid-template-columns: 3fr 1fr 1.5fr 1fr 1fr 1fr 1.5fr; align-items: center;'
XHTTP_UNINSTALL_SCRIPT = r"""
#!/bin/bash
systemctl stop xray
systemctl disable xray
rm -f /etc/systemd/system/xray.service
systemctl daemon-reload
rm -rf /usr/local/etc/xray

echo "Xray Service Uninstalled (Binary kept safe)"
"""


SSH_DIALOG_STATES = {}
SSH_PAGE_TERMINALS = {}
SSH_DIALOG_OPEN_COOLDOWN = 1.2


async def save_server_config(server_data, is_add=True, idx=None):
    client = None
    try:
        client = ui.context.client
    except:
        pass

    logger.info(f"[SaveServerDialog] save_server_config called | is_add={is_add} idx={idx} client_present={client is not None} servers_before={len(SERVERS_CACHE)} url={server_data.get('url')} name={server_data.get('name')}")

    if not server_data.get('name') or not server_data.get('url'):
        safe_notify("名称和地址不能为空", "negative")
        return False

    old_group = None
    if not is_add and idx is not None and 0 <= idx < len(SERVERS_CACHE):
        old_group = SERVERS_CACHE[idx].get('group')

    if is_add:
        for s in SERVERS_CACHE:
            if s['url'] == server_data['url']:
                safe_notify("已存在！", "warning")
                return False

        has_flag = False
        for v in AUTO_COUNTRY_MAP.values():
            if v.split(' ')[0] in server_data['name']:
                has_flag = True
                break
        if not has_flag and '🏳️' not in server_data['name']:
            server_data['name'] = f"🏳️ {server_data['name']}"

        SERVERS_CACHE.append(server_data)
        safe_notify(f"已添加: {server_data['name']}", "positive")
    else:
        if idx is not None and 0 <= idx < len(SERVERS_CACHE):
            SERVERS_CACHE[idx].update(server_data)
            safe_notify(f"已更新: {server_data['name']}", "positive")
        else:
            safe_notify("目标不存在", "negative")
            return False

    await save_servers()
    logger.info(f"[SaveServerDialog] save_servers done | servers_after={len(SERVERS_CACHE)} rows_refs={len(SIDEBAR_UI_REFS.get('rows', {}))} group_refs={len(SIDEBAR_UI_REFS.get('groups', {}))}")

    new_group = server_data.get('group', '默认分组')
    if new_group in ['默认分组', '自动注册', '未分组', '自动导入']:
        try:
            new_group = detect_country_group(server_data.get('name', ''), server_data)
        except:
            pass
        if not new_group:
            new_group = '🏳️ 其他地区'

    need_full_refresh = False

    try:
        if is_add:
            if new_group in SIDEBAR_UI_REFS['groups']:
                with SIDEBAR_UI_REFS['groups'][new_group]:
                    render_single_sidebar_row(server_data)
                EXPANDED_GROUPS.add(new_group)
            else:
                need_full_refresh = True
        elif old_group != new_group:
            row_el = SIDEBAR_UI_REFS['rows'].get(server_data['url'])
            target_col = SIDEBAR_UI_REFS['groups'].get(new_group)
            if row_el and target_col:
                row_el.move(target_col)
                EXPANDED_GROUPS.add(new_group)
            else:
                need_full_refresh = True
    except Exception as e:
        logger.error(f"UI Move Error: {e}")
        need_full_refresh = True

    logger.info(f"[SaveServerDialog] sidebar refresh decision | need_full_refresh={need_full_refresh} new_group={new_group} rows_refs={len(SIDEBAR_UI_REFS.get('rows', {}))} group_refs={len(SIDEBAR_UI_REFS.get('groups', {}))}")
    if need_full_refresh:
        try:
            logger.info(f"[SaveServerDialog] calling render_sidebar_content.refresh | client_present={client is not None}")
            if client:
                with client:
                    render_sidebar_content.refresh()
            else:
                render_sidebar_content.refresh()
            logger.info("[SaveServerDialog] render_sidebar_content.refresh returned")
        except Exception as e:
            logger.error(f"[SaveServerDialog] render_sidebar_content.refresh failed: {e}")

    current_scope = CURRENT_VIEW_STATE.get('scope')
    current_data = CURRENT_VIEW_STATE.get('data')

    if current_scope == 'SINGLE' and (current_data == server_data or (is_add and server_data == SERVERS_CACHE[-1])):
        try:
            from app.ui.pages.content_router import refresh_content

            await refresh_content('SINGLE', server_data, force_refresh=True)
        except:
            pass
    elif current_scope in ['ALL', 'TAG', 'COUNTRY']:
        CURRENT_VIEW_STATE['scope'] = None
        try:
            from app.ui.pages.content_router import refresh_content

            await refresh_content(current_scope, current_data, force_refresh=True)
        except:
            pass
    elif current_scope == 'DASHBOARD':
        try:
            logger.info(f"[SaveServerDialog] calling refresh_dashboard_ui | client_present={client is not None} current_scope={current_scope}")
            if client:
                with client:
                    await refresh_dashboard_ui()
            else:
                await refresh_dashboard_ui()
            logger.info("[SaveServerDialog] refresh_dashboard_ui returned")
        except Exception as e:
            logger.error(f"[SaveServerDialog] refresh_dashboard_ui failed: {e}")

    asyncio.create_task(fast_resolve_single_server(server_data))

    if ADMIN_CONFIG.get('probe_enabled', False) and server_data.get('probe_installed', False):
        async def delayed_install():
            await asyncio.sleep(1)
            await install_probe_on_server(server_data)
        asyncio.create_task(delayed_install())

    return True


async def open_server_dialog(idx=None):
    is_edit = idx is not None
    original_data = SERVERS_CACHE[idx] if is_edit else {}
    data = original_data.copy()

    if is_edit:
        has_xui_conf = bool(data.get('url') and data.get('user') and data.get('pass'))
        raw_ssh_host = data.get('ssh_host')
        if not raw_ssh_host and not has_xui_conf:
            raw_ssh_host = data.get('url', '').replace('http://', '').replace('https://', '').split(':')[0]

        has_ssh_conf = bool(raw_ssh_host or data.get('ssh_user') or data.get('ssh_key') or data.get('ssh_password') or data.get('probe_installed'))
        if not has_ssh_conf and not has_xui_conf:
            has_ssh_conf = True
    else:
        has_xui_conf = True
        has_ssh_conf = True

    state = {'ssh_active': has_ssh_conf, 'xui_active': has_xui_conf}

    with ui.dialog() as d, ui.card().classes('w-full max-w-sm p-5 flex flex-col gap-4'):
        with ui.row().classes('w-full justify-between items-center'):
            ui.label('编辑服务器' if is_edit else '添加服务器').classes('text-lg font-bold')
            tabs = ui.tabs().classes('text-blue-600')
            with tabs:
                t_ssh = ui.tab('SSH / 探针', icon='terminal')
                t_xui = ui.tab('X-UI面板', icon='settings')

        async def save_basic_info_only():
            if not is_edit:
                safe_notify("新增服务器请使用下方的保存按钮", "warning")
                return

            new_name = name_input.value.strip()
            new_group = group_input.value

            if not new_name:
                new_name = await generate_smart_name(data)

            SERVERS_CACHE[idx]['name'] = new_name
            SERVERS_CACHE[idx]['group'] = new_group

            await save_servers()
            render_sidebar_content.refresh()

            current_scope = CURRENT_VIEW_STATE.get('scope')
            if current_scope == 'SINGLE' and CURRENT_VIEW_STATE.get('data') == SERVERS_CACHE[idx]:
                try:
                    from app.ui.pages.content_router import refresh_content

                    await refresh_content('SINGLE', SERVERS_CACHE[idx])
                except:
                    pass
            elif current_scope in ['ALL', 'TAG', 'COUNTRY']:
                CURRENT_VIEW_STATE['scope'] = None
                try:
                    from app.ui.pages.content_router import refresh_content

                    await refresh_content(current_scope, CURRENT_VIEW_STATE.get('data'), force_refresh=False)
                except:
                    pass

            safe_notify("✅ 基础信息已更新", "positive")
            d.close()

        with ui.column().classes('w-full gap-2'):
            name_input = ui.input(value=data.get('name', ''), label='备注名称 (留空自动获取)').classes('w-full').props('outlined dense')

            with ui.row().classes('w-full items-center gap-2 no-wrap'):
                from app.services.server_ops import get_all_groups

                group_input = ui.select(options=get_all_groups(), value=data.get('group', '默认分组'), new_value_mode='add-unique', label='分组').classes('flex-grow').props('outlined dense')

                if is_edit:
                    ui.button(icon='save', on_click=save_basic_info_only).props('flat dense round color=primary').tooltip('仅保存名称和分组 (不重新部署)')

        inputs = {}
        btn_keycap_blue = 'bg-white rounded-lg font-bold tracking-wide border-t border-x border-gray-100 border-b-4 border-blue-100 text-blue-600 px-4 py-1 transition-all duration-100 active:border-b-0 active:border-t-4 active:translate-y-1 hover:bg-blue-50'
        btn_keycap_delete = 'bg-white rounded-xl font-bold tracking-wide w-full border-t border-x border-gray-100 border-b-4 border-red-100 text-red-500 transition-all duration-100 active:border-b-0 active:border-t-4 active:translate-y-1 hover:bg-red-50'
        btn_keycap_red_confirm = 'rounded-lg font-bold tracking-wide text-white border-b-4 border-red-900 transition-all duration-100 active:border-b-0 active:border-t-4 active:translate-y-1'

        async def save_panel_data(panel_type):
            final_name = name_input.value.strip()
            final_group = group_input.value
            new_server_data = data.copy()
            new_server_data['group'] = final_group

            if panel_type == 'ssh':
                if not inputs.get('ssh_host'):
                    return
                s_host = inputs['ssh_host'].value.strip()
                if not s_host:
                    safe_notify("SSH 主机 IP 不能为空", "negative")
                    return

                new_server_data.update({
                    'ssh_host': s_host,
                    'ssh_port': str(inputs['ssh_port'].value).strip(),
                    'ssh_user': inputs['ssh_user'].value.strip(),
                    'ssh_auth_type': inputs['auth_type'].value,
                    'ssh_password': inputs['ssh_pwd'].value if inputs['ssh_pwd'] else '',
                    'ssh_key': inputs['ssh_key'].value if inputs['ssh_key'] else '',
                    'probe_installed': True,
                })

                if 'probe_chk' in inputs:
                    inputs['probe_chk'].value = True

                if not new_server_data.get('url'):
                    new_server_data['url'] = f"http://{s_host}:22"

            elif panel_type == 'xui':
                if not inputs.get('xui_url'):
                    return
                x_url_raw = inputs['xui_url'].value.strip()
                x_user = inputs['xui_user'].value.strip()
                x_pass = inputs['xui_pass'].value.strip()

                if not (x_url_raw and x_user and x_pass):
                    safe_notify("必填项不能为空", "negative")
                    return

                if '://' not in x_url_raw:
                    x_url_raw = f"http://{x_url_raw}"

                from urllib.parse import urlparse
                try:
                    parsed = urlparse(x_url_raw)
                    netloc = parsed.netloc
                    if ':' not in netloc and ']' not in netloc:
                        netloc = f"{netloc}:54321"
                        safe_notify("已自动添加默认端口: 54321", "positive")

                    final_base_url = f"{parsed.scheme}://{netloc}"
                    path_from_url = parsed.path.strip().strip('/')

                    if path_from_url:
                        final_prefix = f"/{path_from_url}"
                        if 'xui_prefix' in inputs:
                            inputs['xui_prefix'].value = final_prefix
                        safe_notify(f"已自动识别路径: {final_prefix}", "positive")
                    else:
                        final_prefix = inputs['xui_prefix'].value.strip()
                except Exception as e:
                    logger.error(f"URL Parse Error: {e}")
                    final_base_url = x_url_raw
                    final_prefix = inputs['xui_prefix'].value.strip()

                probe_val = inputs['probe_chk'].value
                new_server_data.update({
                    'url': final_base_url,
                    'user': x_user,
                    'pass': x_pass,
                    'prefix': final_prefix,
                    'probe_installed': probe_val,
                })

                if probe_val:
                    if not new_server_data.get('ssh_host'):
                        try:
                            clean_host = urlparse(final_base_url).hostname or final_base_url.split('://')[-1].split(':')[0]
                            new_server_data['ssh_host'] = clean_host
                        except:
                            new_server_data['ssh_host'] = final_base_url.split('://')[-1].split(':')[0]
                    if not new_server_data.get('ssh_port'):
                        new_server_data['ssh_port'] = '22'
                    if not new_server_data.get('ssh_user'):
                        new_server_data['ssh_user'] = 'root'
                    if not new_server_data.get('ssh_auth_type'):
                        new_server_data['ssh_auth_type'] = '全局密钥'

            if not final_name:
                safe_notify("正在生成名称...", "ongoing")
                final_name = await generate_smart_name(new_server_data)
            new_server_data['name'] = final_name

            success = await save_server_config(new_server_data, is_add=not is_edit, idx=idx)

            if success:
                data.update(new_server_data)
                if panel_type == 'ssh':
                    state['ssh_active'] = True
                if panel_type == 'xui':
                    state['xui_active'] = True
                if panel_type == 'xui' and new_server_data.get('probe_installed'):
                    state['ssh_active'] = True

                if new_server_data.get('probe_installed'):
                    safe_notify("🚀 配置已保存，正在自动推送探针...", "ongoing")
                    asyncio.create_task(install_probe_on_server(new_server_data))
                else:
                    safe_notify(f"✅ {panel_type.upper()} 已保存", "positive")

        @ui.refreshable
        def render_ssh_panel():
            if not state['ssh_active']:
                with ui.column().classes('w-full h-48 justify-center items-center bg-gray-50 rounded border border-dashed border-gray-300'):
                    ui.icon('terminal', color='grey').classes('text-4xl mb-2')
                    ui.label('SSH 功能未启用').classes('text-gray-500 font-bold mb-2')
                    ui.button('启用 SSH 配置', icon='add', on_click=lambda: _activate_panel('ssh')).props('flat bg-blue-50 text-blue-600')
            else:
                init_host = data.get('ssh_host')
                if not init_host and is_edit:
                    if '://' in data.get('url', ''):
                        init_host = data.get('url', '').split('://')[-1].split(':')[0]
                    else:
                        init_host = data.get('url', '').split(':')[0]

                inputs['ssh_host'] = ui.input(label='SSH 主机 IP', value=init_host).classes('w-full').props('outlined dense')

                with ui.column().classes('w-full gap-3'):
                    with ui.row().classes('w-full gap-2'):
                        inputs['ssh_user'] = ui.input(value=data.get('ssh_user', 'root'), label='SSH 用户').classes('flex-1').props('outlined dense')
                        inputs['ssh_port'] = ui.input(value=data.get('ssh_port', '22'), label='端口').classes('w-1/3').props('outlined dense')

                    valid_auth_options = ['全局密钥', '独立密码', '独立密钥']
                    current_auth = data.get('ssh_auth_type', '全局密钥')
                    if current_auth not in valid_auth_options:
                        current_auth = '全局密钥'

                    inputs['auth_type'] = ui.select(valid_auth_options, value=current_auth, label='认证方式').classes('w-full').props('outlined dense options-dense')
                    inputs['ssh_pwd'] = ui.input(label='SSH 密码', password=True, value=data.get('ssh_password', '')).classes('w-full').props('outlined dense')
                    inputs['ssh_pwd'].bind_visibility_from(inputs['auth_type'], 'value', value='独立密码')
                    inputs['ssh_key'] = ui.textarea(label='SSH 私钥', value=data.get('ssh_key', '')).classes('w-full').props('outlined dense rows=3 input-class=font-mono text-xs')
                    inputs['ssh_key'].bind_visibility_from(inputs['auth_type'], 'value', value='独立密钥')

                ui.separator().classes('my-1')
                with ui.row().classes('w-full justify-between items-center'):
                    ui.label('✅ 自动使用全局私钥').bind_visibility_from(inputs['auth_type'], 'value', value='全局密钥').classes('text-green-600 text-xs font-bold')
                    ui.element('div').bind_visibility_from(inputs['auth_type'], 'value', value='独立密码')
                    ui.element('div').bind_visibility_from(inputs['auth_type'], 'value', value='独立密钥')
                    ui.button('保存 SSH', icon='save', on_click=lambda: save_panel_data('ssh')).props('flat').classes(btn_keycap_blue)

        @ui.refreshable
        def render_xui_panel():
            if not state['xui_active']:
                with ui.column().classes('w-full h-48 justify-center items-center bg-gray-50 rounded border border-dashed border-gray-300'):
                    ui.icon('settings_applications', color='grey').classes('text-4xl mb-2')
                    ui.label('X-UI 面板未配置').classes('text-gray-500 font-bold mb-2')
                    ui.button('配置 X-UI 信息', icon='add', on_click=lambda: _activate_panel('xui')).props('flat bg-purple-50 text-purple-600')
            else:
                inputs['xui_url'] = ui.input(value=data.get('url', ''), label='面板 URL (http://ip:port)').classes('w-full').props('outlined dense')
                ui.label('默认端口 54321，如不填写将自动补全').classes('text-[10px] text-gray-400 ml-1 -mt-1 mb-1')
                with ui.row().classes('w-full gap-2'):
                    inputs['xui_user'] = ui.input(value=data.get('user', ''), label='账号').classes('flex-1').props('outlined dense')
                    inputs['xui_pass'] = ui.input(value=data.get('pass', ''), label='密码', password=True).classes('flex-1').props('outlined dense')
                inputs['xui_prefix'] = ui.input(value=data.get('prefix', ''), label='面板根路径 (选填)').classes('w-full').props('outlined dense')
                ui.separator().classes('my-1')
                with ui.row().classes('w-full justify-between items-center'):
                    inputs['probe_chk'] = ui.checkbox('启用 Root 探针', value=data.get('probe_installed', False))
                    inputs['probe_chk'].classes('text-sm font-bold text-slate-700')
                    ui.button('保存 X-UI', icon='save', on_click=lambda: save_panel_data('xui')).props('flat').classes(btn_keycap_blue)
                ui.label('提示: 启用探针需先配置 SSH 登录信息').classes('text-[10px] text-red-500 ml-8 -mt-2')

                def auto_fill_ssh():
                    if inputs['probe_chk'].value and state['ssh_active'] and inputs.get('ssh_host') and not inputs['ssh_host'].value:
                        p_url = inputs['xui_url'].value
                        if p_url:
                            clean_ip = p_url.split('://')[-1].split(':')[0]
                            if ':' in clean_ip:
                                clean_ip = clean_ip.split(':')[0]
                            inputs['ssh_host'].set_value(clean_ip)
                inputs['probe_chk'].on_value_change(auto_fill_ssh)

        def _activate_panel(panel_type):
            state[f'{panel_type}_active'] = True
            if panel_type == 'ssh':
                render_ssh_panel.refresh()
            elif panel_type == 'xui':
                render_xui_panel.refresh()

        default_tab = t_ssh
        if is_edit and not state['ssh_active'] and state['xui_active']:
            default_tab = t_xui

        with ui.tab_panels(tabs, value=default_tab).classes('w-full animated fadeIn'):
            with ui.tab_panel(t_ssh).classes('p-0 flex flex-col gap-3'):
                render_ssh_panel()
            with ui.tab_panel(t_xui).classes('p-0 flex flex-col gap-3'):
                render_xui_panel()

        if is_edit:
            with ui.row().classes('w-full justify-start mt-4 pt-2 border-t border-gray-100'):
                async def open_delete_confirm():
                    with ui.dialog() as del_d, ui.card().classes('w-80 p-4'):
                        ui.label('删除确认').classes('text-lg font-bold text-red-600')
                        ui.label('请选择要删除的内容：').classes('text-sm text-gray-600 mb-2')

                        real_ssh_exists = bool(data.get('ssh_host') or data.get('ssh_user'))
                        real_xui_exists = bool(data.get('url') and data.get('user') and data.get('pass'))
                        has_probe = data.get('probe_installed', False)

                        if not real_ssh_exists and not real_xui_exists:
                            real_ssh_exists = True
                            real_xui_exists = True

                        chk_ssh = ui.checkbox('SSH 连接信息', value=real_ssh_exists).classes('text-sm font-bold')
                        chk_xui = ui.checkbox('X-UI 面板信息', value=real_xui_exists).classes('text-sm font-bold')
                        chk_uninstall = ui.checkbox('同时卸载远程探针脚本', value=True).classes('text-sm font-bold text-red-500')
                        chk_uninstall.set_visibility(has_probe)

                        if not real_ssh_exists:
                            chk_ssh.value = False
                            chk_ssh.disable()
                        if not real_xui_exists:
                            chk_xui.value = False
                            chk_xui.disable()
                        if real_ssh_exists and not real_xui_exists:
                            chk_ssh.disable()
                        if real_xui_exists and not real_ssh_exists:
                            chk_xui.disable()

                        async def confirm_execution():
                            if idx >= len(SERVERS_CACHE):
                                return
                            target_srv = SERVERS_CACHE[idx]
                            will_delete_ssh = chk_ssh.value
                            will_delete_xui = chk_xui.value
                            will_uninstall = chk_uninstall.value and chk_uninstall.visible
                            remaining_ssh = real_ssh_exists and not will_delete_ssh
                            remaining_xui = real_xui_exists and not will_delete_xui
                            is_full_delete = False

                            if will_uninstall:
                                loading_notify = ui.notification('正在尝试连接并卸载探针...', timeout=None, spinner=True)
                                try:
                                    uninstall_cmd = "systemctl stop x-fusion-agent && systemctl disable x-fusion-agent && rm -f /etc/systemd/system/x-fusion-agent.service && systemctl daemon-reload && rm -f /root/x_fusion_agent.py"
                                    success, output = await run.io_bound(lambda: _ssh_exec_wrapper(target_srv, uninstall_cmd))
                                    if success:
                                        ui.notify('✅ 远程探针已卸载清理', type='positive')
                                    else:
                                        ui.notify('⚠️ 远程卸载失败 (可能是连接超时)，将仅删除本地记录', type='warning')
                                finally:
                                    loading_notify.dismiss()

                            if not remaining_ssh and not remaining_xui:
                                SERVERS_CACHE.pop(idx)
                                u = target_srv.get('url')
                                p_u = target_srv.get('ssh_host') or u
                                for k in [u, p_u]:
                                    if k in PROBE_DATA_CACHE:
                                        del PROBE_DATA_CACHE[k]
                                    if k in NODES_DATA:
                                        del NODES_DATA[k]
                                    if k in PING_TREND_CACHE:
                                        del PING_TREND_CACHE[k]
                                safe_notify('✅ 服务器已彻底删除', 'positive')
                                is_full_delete = True
                            else:
                                if will_delete_ssh:
                                    for k in ['ssh_host', 'ssh_port', 'ssh_user', 'ssh_password', 'ssh_key', 'ssh_auth_type']:
                                        target_srv[k] = ''
                                    target_srv['probe_installed'] = False
                                    state['ssh_active'] = False
                                    data['ssh_host'] = ''
                                    safe_notify('✅ SSH 信息已清除', 'positive')

                                if will_delete_xui:
                                    for k in ['url', 'user', 'pass', 'prefix']:
                                        target_srv[k] = ''
                                    state['xui_active'] = False
                                    data['url'] = ''
                                    safe_notify('✅ X-UI 信息已清除', 'positive')

                            await save_servers()
                            del_d.close()
                            d.close()
                            render_sidebar_content.refresh()
                            current_scope = CURRENT_VIEW_STATE.get('scope')
                            current_data = CURRENT_VIEW_STATE.get('data')

                            from app.ui.pages.content_router import content_container, refresh_content

                            if is_full_delete:
                                if current_scope == 'SINGLE' and current_data == target_srv:
                                    content_container.clear()
                                    with content_container:
                                        ui.label('该服务器已删除').classes('text-gray-400 text-lg w-full text-center mt-20')
                                elif current_scope in ['ALL', 'TAG', 'COUNTRY']:
                                    CURRENT_VIEW_STATE['scope'] = None
                                    await refresh_content(current_scope, current_data, force_refresh=False)
                            else:
                                if current_scope == 'SINGLE' and current_data == target_srv:
                                    await refresh_content('SINGLE', target_srv)

                        with ui.row().classes('w-full justify-end mt-4 gap-2'):
                            ui.button('取消', on_click=del_d.close).props('flat dense color=grey')
                            ui.button('确认执行', color='red', on_click=confirm_execution).props('unelevated').classes(btn_keycap_red_confirm)
                    del_d.open()

                ui.button('删除 / 卸载配置', icon='delete', on_click=open_delete_confirm).props('flat').classes(btn_keycap_delete)
    d.open()




def cleanup_ssh_route_terminal(server_key=None):
    keys = [server_key] if server_key else list(SSH_PAGE_TERMINALS.keys())
    for key in keys:
        inst = SSH_PAGE_TERMINALS.pop(key, None)
        try:
            if inst:
                inst.close()
        except:
            pass


async def render_single_ssh_view(server_conf):
    from app.ui.pages.content_router import content_container, refresh_content

    server_key = server_conf.get('url') or server_conf.get('ssh_host') or str(id(server_conf))
    cleanup_ssh_route_terminal(server_key)

    current_client = None
    try:
        current_client = ui.context.client
    except:
        pass

    if content_container:
        content_container.clear()
        content_container.classes(remove='overflow-y-auto block', add='h-full overflow-hidden flex flex-col p-4')

    terminal_state = {'instance': None}

    async def _start_terminal(terminal_box):
        await asyncio.sleep(0.15)
        try:
            terminal_box.clear()
        except:
            pass
        ssh = WebSSH(terminal_box, server_conf)
        terminal_state['instance'] = ssh
        SSH_PAGE_TERMINALS[server_key] = ssh
        await ssh.connect()

    async def _back_to_detail():
        cleanup_ssh_route_terminal(server_key)
        await refresh_content('SINGLE', server_conf, manual_client=current_client)

    def exec_quick_cmd(cmd_text):
        if terminal_state['instance'] and terminal_state['instance'].active:
            terminal_state['instance'].channel.send(cmd_text + '\n')
            safe_notify(f'已发送: {cmd_text[:20]}...', 'positive')
        else:
            safe_notify('SSH 正在连接，请稍后重试', 'warning')

    def open_cmd_editor(existing_cmd=None):
        with ui.dialog() as edit_d, ui.card().classes('w-96 p-5 bg-[#1e293b] border border-slate-600 shadow-2xl'):
            with ui.row().classes('w-full justify-between items-center mb-4'):
                ui.label('管理快捷命令').classes('text-lg font-bold text-white')
                ui.button(icon='close', on_click=edit_d.close).props('flat round dense color=grey')
            name_input = ui.input('按钮名称', value=existing_cmd['name'] if existing_cmd else '').classes('w-full mb-3').props('outlined dense dark bg-color="slate-800"')
            cmd_input = ui.textarea('执行命令', value=existing_cmd['cmd'] if existing_cmd else '').classes('w-full mb-4').props('outlined dense dark bg-color="slate-800" rows=4')

            async def save():
                name = name_input.value.strip()
                cmd = cmd_input.value.strip()
                if not name or not cmd:
                    return ui.notify('内容不能为空', type='negative')
                if 'quick_commands' not in ADMIN_CONFIG:
                    ADMIN_CONFIG['quick_commands'] = []
                if existing_cmd:
                    existing_cmd['name'] = name
                    existing_cmd['cmd'] = cmd
                else:
                    ADMIN_CONFIG['quick_commands'].append({'name': name, 'cmd': cmd, 'id': str(uuid.uuid4())[:8]})
                await save_admin_config()
                render_quick_commands.refresh()
                edit_d.close()

            async def delete_current():
                if existing_cmd and 'quick_commands' in ADMIN_CONFIG:
                    ADMIN_CONFIG['quick_commands'].remove(existing_cmd)
                    await save_admin_config()
                    render_quick_commands.refresh()
                    edit_d.close()

            with ui.row().classes('w-full justify-between items-center mt-2'):
                if existing_cmd:
                    ui.button('删除', icon='delete', on_click=delete_current).classes('bg-red-600 text-white font-bold rounded-lg border-b-4 border-red-800 active:border-b-0 active:translate-y-[2px]')
                else:
                    ui.element('div')
                ui.button('保存', icon='save', on_click=save).classes('bg-blue-600 text-white font-bold rounded-lg border-b-4 border-blue-800 active:border-b-0 active:translate-y-[2px]')
        edit_d.open()

    @ui.refreshable
    def render_quick_commands():
        commands = ADMIN_CONFIG.get('quick_commands', [])
        with ui.row().classes('w-full gap-2 items-center flex-wrap'):
            ui.label('快捷命令').classes('text-xs font-bold text-slate-500 mr-2')
            for cmd_obj in commands:
                cmd_name = cmd_obj.get('name', '未命名')
                cmd_text = cmd_obj.get('cmd', '')
                with ui.element('div').classes('flex items-center bg-slate-700 rounded overflow-hidden border-b-2 border-slate-900 transition-all active:border-b-0 active:translate-y-[2px] hover:bg-slate-600'):
                    ui.button(cmd_name, on_click=lambda c=cmd_text: exec_quick_cmd(c)).props('unelevated').classes('bg-transparent text-[11px] font-bold text-slate-300 px-3 py-1.5 hover:text-white rounded-none')
                    ui.element('div').classes('w-[1px] h-4 bg-slate-500 opacity-50')
                    ui.button(icon='settings', on_click=lambda c=cmd_obj: open_cmd_editor(c)).props('flat dense size=xs').classes('text-slate-400 hover:text-white px-1 py-1.5 rounded-none')
            ui.button(icon='add', on_click=lambda: open_cmd_editor(None)).props('flat dense round size=sm color=green').tooltip('添加常用命令')

    with content_container:
        with ui.card().classes('w-full h-full p-0 rounded-xl border border-slate-700 border-b-[4px] border-b-slate-800 shadow-lg overflow-hidden bg-slate-900 flex flex-col'):
            with ui.row().classes('w-full items-center justify-between px-4 py-3 border-b border-slate-700 bg-[#111827]'):
                with ui.row().classes('items-center gap-3'):
                    ui.icon('terminal').classes('text-green-400')
                    with ui.column().classes('gap-0'):
                        ui.label(f"SSH Console · {server_conf.get('ssh_user', 'root')}@{server_conf.get('ssh_host') or 'IP'}").classes('text-slate-100 font-bold')
                        ui.label(server_conf.get('name', '未命名服务器')).classes('text-xs text-slate-500')
                with ui.row().classes('items-center gap-2'):
                    ui.button('返回详情', icon='arrow_back', on_click=lambda: asyncio.create_task(_back_to_detail())).props('outline color=grey').classes('text-slate-200')

            with ui.row().classes('w-full items-center justify-between gap-3 px-4 py-2 bg-slate-800 border-b border-slate-700'):
                with ui.row().classes('items-center gap-2'):
                    ui.badge('独立路由终端', color='green').props('outline rounded')
                    ui.badge('交互模式', color='blue').props('outline rounded')
                ui.label('右侧详情区已切换为 SSH 页面').classes('text-xs text-slate-400')

            terminal_box = ui.element('div').classes('w-full min-h-0 flex-grow bg-black overflow-hidden flex items-center justify-center')
            with terminal_box:
                ui.label('正在初始化 SSH 终端...').classes('text-slate-500 text-sm')

            with ui.column().classes('w-full px-4 py-3 bg-slate-800 border-t border-slate-700 gap-2'):
                render_quick_commands()

    logger.info(f"[SingleSSHRoute] page opened | key={server_key}")
    asyncio.create_task(_start_terminal(terminal_box))


async def render_single_server_view(server_conf, force_refresh=False):
    global REFRESH_CURRENT_NODES

    from app.ui.pages.content_router import content_container, refresh_content

    if content_container:
        content_container.clear()
        content_container.classes(remove='overflow-y-auto block', add='h-full overflow-hidden flex flex-col p-4')

    with content_container:
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

        def render_metric_row(label, value, sub_text=''):
            with ui.row().classes('w-full items-center justify-between gap-4 px-4 py-3 rounded-xl bg-slate-800/55 border border-slate-700/80 shadow-sm'):
                with ui.column().classes('gap-0 min-w-0 flex-1'):
                    ui.label(label).classes('text-[11px] font-black uppercase tracking-[0.18em] text-slate-500')
                    if sub_text:
                        ui.label(sub_text).classes('text-[10px] text-slate-400 mt-1 break-all')
                ui.label(str(value)).classes('text-sm font-black text-slate-100 text-right shrink-0')

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
                return 'https://cdn.simpleicons.org/ubuntu/E95420', 'Ubuntu'
            if 'debian' in name:
                return 'https://cdn.simpleicons.org/debian/A81D33', 'Debian'
            if 'centos' in name:
                return 'https://cdn.simpleicons.org/centos/8A2BE2', 'CentOS'
            if 'red hat' in name:
                return 'https://cdn.simpleicons.org/redhat/EE0000', 'RedHat'
            if 'rocky' in name:
                return 'https://cdn.simpleicons.org/rockylinux/10B981', 'RockyLinux'
            if 'alma' in name:
                return 'https://cdn.simpleicons.org/almalinux/2563EB', 'AlmaLinux'
            if 'alpine' in name:
                return 'https://cdn.simpleicons.org/alpinelinux/0EA5E9', 'Alpine'
            if 'arch' in name:
                return 'https://cdn.simpleicons.org/archlinux/1793D1', 'ArchLinux'
            return 'https://cdn.simpleicons.org/linux/FCC624', 'Linux'

        def render_percent_chip(percent):
            pct = clamp_percent(percent)
            ui.label(f'{pct:.0f}%').classes('text-base font-black text-slate-100 leading-none')

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

        async def load_runtime_snapshot():
            probe_cache = PROBE_DATA_CACHE.get(server_conf['url'], {}) or {}
            static = probe_cache.get('static', {}) or {}
            mem_total = to_float(probe_cache.get('mem_total', 0.0))
            mem_used = round(mem_total * clamp_percent(probe_cache.get('mem_usage', 0.0)) / 100.0, 2)
            swap_total = to_float(probe_cache.get('swap_total', 0.0))
            swap_free = to_float(probe_cache.get('swap_free', 0.0))
            disk_total = to_float(probe_cache.get('disk_total', 0.0))
            disk_used = round(disk_total * clamp_percent(probe_cache.get('disk_usage', 0.0)) / 100.0, 2)
            snapshot = {
                'os': static.get('os') or '--',
                'kernel': static.get('kernel') or probe_cache.get('kernel') or '--',
                'arch': static.get('arch') or '--',
                'virt': static.get('virt') or '--',
                'uptime': probe_cache.get('uptime') or '--',
                'mem_total_gb': mem_total,
                'mem_free_gb': max(mem_total - mem_used, 0.0) if mem_total else 0.0,
                'mem_used_gb': mem_used,
                'mem_cache_gb': to_float(probe_cache.get('mem_cache_gb', 0.0)),
                'mem_usage_pct': clamp_percent(probe_cache.get('mem_usage', 0.0)),
                'swap_total_gb': swap_total,
                'swap_free_gb': swap_free,
                'swap_used_gb': max(swap_total - swap_free, 0.0),
                'swap_usage_pct': clamp_percent((max(swap_total - swap_free, 0.0) / swap_total * 100.0) if swap_total else 0.0),
                'disk_device': probe_cache.get('disk_device') or '/',
                'disk_total_gb': disk_total,
                'disk_free_gb': max(disk_total - disk_used, 0.0) if disk_total else 0.0,
                'disk_used_gb': disk_used,
                'disk_usage_pct': clamp_percent(probe_cache.get('disk_usage', 0.0)),
                'last_updated': probe_cache.get('last_updated', 0),
                'source': 'probe' if probe_cache else 'fallback',
            }

            if server_conf.get('probe_installed') and server_conf.get('ssh_host'):
                remote_script = r'''python3 - <<'PY'
import json, os, platform

def read_meminfo():
    data = {}
    try:
        with open('/proc/meminfo') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2:
                    data[parts[0].rstrip(':')] = int(parts[1])
    except:
        pass
    return data

info = {}
try:
    pretty = '--'
    if os.path.exists('/etc/os-release'):
        with open('/etc/os-release') as f:
            for line in f:
                if line.startswith('PRETTY_NAME='):
                    pretty = line.split('=', 1)[1].strip().strip('"')
                    break
    mem = read_meminfo()
    total = mem.get('MemTotal', 0) / 1024 / 1024
    free = mem.get('MemFree', 0) / 1024 / 1024
    available = mem.get('MemAvailable', 0) / 1024 / 1024
    buffers = mem.get('Buffers', 0) / 1024 / 1024
    cached = mem.get('Cached', 0) / 1024 / 1024
    real_used = max(total - available, 0)
    swap_total = mem.get('SwapTotal', 0) / 1024 / 1024
    swap_free = mem.get('SwapFree', 0) / 1024 / 1024

    st = os.statvfs('/')
    disk_total = st.f_blocks * st.f_frsize / 1024 / 1024 / 1024
    disk_free = st.f_bavail * st.f_frsize / 1024 / 1024 / 1024
    disk_used = max(disk_total - disk_free, 0)
    disk_device = '/'
    try:
        with open('/proc/mounts') as f:
            for line in f:
                parts = line.split()
                if len(parts) >= 2 and parts[1] == '/':
                    disk_device = parts[0]
                    break
    except:
        pass

    uptime_text = '--'
    try:
        with open('/proc/uptime') as f:
            u = float(f.read().split()[0])
        d = int(u // 86400); h = int((u % 86400) // 3600); m = int((u % 3600) // 60)
        uptime_text = f'{d}天 {h}时 {m}分'
    except:
        pass

    info = {
        'os': pretty,
        'kernel': platform.release(),
        'arch': platform.machine(),
        'virt': 'Unknown',
        'uptime': uptime_text,
        'mem_total_gb': round(total, 2),
        'mem_free_gb': round(free, 2),
        'mem_used_gb': round(real_used, 2),
        'mem_cache_gb': round(buffers + cached, 2),
        'mem_usage_pct': round((real_used / total * 100.0), 1) if total else 0.0,
        'swap_total_gb': round(swap_total, 2),
        'swap_free_gb': round(swap_free, 2),
        'swap_used_gb': round(max(swap_total - swap_free, 0), 2),
        'swap_usage_pct': round((max(swap_total - swap_free, 0) / swap_total * 100.0), 1) if swap_total else 0.0,
        'disk_device': disk_device,
        'disk_total_gb': round(disk_total, 2),
        'disk_free_gb': round(disk_free, 2),
        'disk_used_gb': round(disk_used, 2),
        'disk_usage_pct': round((disk_used / disk_total * 100.0), 1) if disk_total else 0.0,
        'source': 'ssh',
    }
except Exception as e:
    info = {'error': str(e)}
print(json.dumps(info, ensure_ascii=False))
PY'''

                def _fetch_runtime_via_ssh():
                    client, msg = get_ssh_client_sync(server_conf)
                    if not client:
                        return None
                    try:
                        stdin, stdout, stderr = client.exec_command(remote_script, timeout=20)
                        raw = stdout.read().decode('utf-8', errors='ignore').strip()
                        if raw:
                            parsed = json.loads(raw.splitlines()[-1])
                            if isinstance(parsed, dict) and not parsed.get('error'):
                                return parsed
                    except Exception as e:
                        logger.warning(f'获取运行信息失败: {e}')
                    finally:
                        try:
                            client.close()
                        except:
                            pass
                    return None

                remote_data = await run.io_bound(_fetch_runtime_via_ssh)
                if isinstance(remote_data, dict):
                    snapshot.update(remote_data)

            return snapshot

        runtime_snapshot = await load_runtime_snapshot()
        server_dialog_key = server_conf.get('url') or server_conf.get('ssh_host') or str(id(server_conf))
        ssh_dialog_state = SSH_DIALOG_STATES.setdefault(server_dialog_key, {'opening': False, 'dialog': None, 'last_open_at': 0.0})

        def open_ssh_page():
            if not server_conf.get('ssh_host'):
                safe_notify('当前服务器未配置 SSH 主机，无法打开终端', 'warning')
                return
            try:
                client = ui.context.client
            except:
                client = None
            logger.info(f"[SingleSSHRoute] navigate requested | key={server_dialog_key} client_present={client is not None}")
            asyncio.create_task(refresh_content('SSH_SINGLE', server_conf, manual_client=client))

        def open_ssh_dialog():
            if not server_conf.get('ssh_host'):
                safe_notify('当前服务器未配置 SSH 主机，无法打开终端', 'warning')
                return

            now_ts = time.monotonic()
            last_open_at = ssh_dialog_state.get('last_open_at', 0.0)
            if now_ts - last_open_at < SSH_DIALOG_OPEN_COOLDOWN:
                logger.info(f"[SingleSSH] ignore duplicate open within cooldown | key={server_dialog_key} delta={now_ts - last_open_at:.3f}")
                return

            try:
                if ssh_dialog_state.get('dialog') and ssh_dialog_state['dialog'].visible:
                    logger.info(f"[SingleSSH] ignore open because dialog already visible | key={server_dialog_key}")
                    return
            except:
                ssh_dialog_state['dialog'] = None

            if ssh_dialog_state.get('opening'):
                logger.info(f"[SingleSSH] ignore open because dialog is opening | key={server_dialog_key}")
                return

            ssh_dialog_state['last_open_at'] = now_ts
            ssh_dialog_state['opening'] = True
            logger.info(f"[SingleSSH] open_ssh_dialog accepted | key={server_dialog_key}")

            terminal_state = {'instance': None}


            @ui.refreshable
            def render_quick_commands():
                commands = ADMIN_CONFIG.get('quick_commands', [])
                with ui.row().classes('w-full gap-2 items-center flex-wrap'):
                    ui.label('快捷命令').classes('text-xs font-bold text-slate-500 mr-2')
                    for cmd_obj in commands:
                        cmd_name = cmd_obj.get('name', '未命名')
                        cmd_text = cmd_obj.get('cmd', '')
                        with ui.element('div').classes('flex items-center bg-slate-700 rounded overflow-hidden border-b-2 border-slate-900 transition-all active:border-b-0 active:translate-y-[2px] hover:bg-slate-600'):
                            ui.button(cmd_name, on_click=lambda c=cmd_text: exec_quick_cmd(c)).props('unelevated').classes('bg-transparent text-[11px] font-bold text-slate-300 px-3 py-1.5 hover:text-white rounded-none')
                            ui.element('div').classes('w-[1px] h-4 bg-slate-500 opacity-50')
                            ui.button(icon='settings', on_click=lambda c=cmd_obj: open_cmd_editor(c)).props('flat dense size=xs').classes('text-slate-400 hover:text-white px-1 py-1.5 rounded-none')
                    ui.button(icon='add', on_click=lambda: open_cmd_editor(None)).props('flat dense round size=sm color=green').tooltip('添加常用命令')

            def exec_quick_cmd(cmd_text):
                if terminal_state['instance'] and terminal_state['instance'].active:
                    terminal_state['instance'].channel.send(cmd_text + '\n')
                    safe_notify(f'已发送: {cmd_text[:20]}...', 'positive')
                else:
                    safe_notify('SSH 正在连接，请稍后重试', 'warning')

            def open_cmd_editor(existing_cmd=None):
                with ui.dialog() as edit_d, ui.card().classes('w-96 p-5 bg-[#1e293b] border border-slate-600 shadow-2xl'):
                    with ui.row().classes('w-full justify-between items-center mb-4'):
                        ui.label('管理快捷命令').classes('text-lg font-bold text-white')
                        ui.button(icon='close', on_click=edit_d.close).props('flat round dense color=grey')
                    name_input = ui.input('按钮名称', value=existing_cmd['name'] if existing_cmd else '').classes('w-full mb-3').props('outlined dense dark bg-color="slate-800"')
                    cmd_input = ui.textarea('执行命令', value=existing_cmd['cmd'] if existing_cmd else '').classes('w-full mb-4').props('outlined dense dark bg-color="slate-800" rows=4')

                    async def save():
                        name = name_input.value.strip()
                        cmd = cmd_input.value.strip()
                        if not name or not cmd:
                            return ui.notify('内容不能为空', type='negative')
                        if 'quick_commands' not in ADMIN_CONFIG:
                            ADMIN_CONFIG['quick_commands'] = []
                        if existing_cmd:
                            existing_cmd['name'] = name
                            existing_cmd['cmd'] = cmd
                        else:
                            ADMIN_CONFIG['quick_commands'].append({'name': name, 'cmd': cmd, 'id': str(uuid.uuid4())[:8]})
                        await save_admin_config()
                        edit_d.close()
                        render_quick_commands.refresh()
                        ui.notify('命令已保存', type='positive')

                    async def delete_current():
                        if existing_cmd and 'quick_commands' in ADMIN_CONFIG:
                            ADMIN_CONFIG['quick_commands'].remove(existing_cmd)
                            await save_admin_config()
                            edit_d.close()
                            render_quick_commands.refresh()
                            ui.notify('命令已删除', type='positive')

                    with ui.row().classes('w-full justify-between mt-2'):
                        if existing_cmd:
                            ui.button('删除', icon='delete', color='red', on_click=delete_current).props('flat dense')
                        else:
                            ui.element('div')
                        ui.button('保存', icon='save', on_click=save).classes('bg-blue-600 text-white font-bold rounded-lg border-b-4 border-blue-800 active:border-b-0 active:translate-y-[2px]')
                edit_d.open()

            terminal_box = None
            ssh_dialog = None

            async def _start_terminal():
                await asyncio.sleep(0.15)
                try:
                    if terminal_box:
                        terminal_box.clear()
                except:
                    pass
                ssh = WebSSH(terminal_box, server_conf)
                terminal_state['instance'] = ssh
                await ssh.connect()

            async def _cleanup():
                try:
                    if terminal_state['instance']:
                        terminal_state['instance'].close()
                except:
                    pass
                ssh_dialog_state['opening'] = False
                ssh_dialog_state['dialog'] = None
                logger.info(f"[SingleSSH] dialog cleaned up | key={server_dialog_key}")

            async def _close_dialog():
                await _cleanup()
                if ssh_dialog:
                    ssh_dialog.close()

            with ui.dialog().props('persistent') as ssh_dialog, ui.card().classes('w-full max-w-6xl h-[85vh] flex flex-col p-0 overflow-hidden bg-slate-900 border border-slate-700 shadow-2xl'):
                with ui.row().classes('w-full items-center justify-between px-4 py-3 border-b border-slate-700 bg-[#111827]'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('terminal').classes('text-green-400')
                        with ui.column().classes('gap-0'):
                            ui.label(f"SSH Console · {server_conf.get('ssh_user', 'root')}@{server_conf.get('ssh_host') or 'IP'}").classes('text-slate-100 font-bold')
                            ui.label('实时交互终端，支持快捷命令和连续输入').classes('text-xs text-slate-500')
                    ui.button(icon='close', on_click=lambda: asyncio.create_task(_close_dialog())).props('flat round dense color=grey')

                with ui.row().classes('w-full items-center justify-between gap-3 px-4 py-2 bg-slate-800 border-b border-slate-700'):
                    with ui.row().classes('items-center gap-2'):
                        ui.badge('已自动连接', color='green').props('outline rounded')
                        ui.badge('交互模式', color='blue').props('outline rounded')
                    ui.label('提示：若刚打开终端，请等待 1~2 秒完成连接').classes('text-xs text-slate-400')

                terminal_box = ui.element('div').classes('w-full min-h-0 flex-grow bg-black overflow-hidden flex items-center justify-center')
                with terminal_box:
                    ui.label('正在初始化 SSH 终端...').classes('text-slate-500 text-sm')

                with ui.column().classes('w-full px-4 py-3 bg-slate-800 border-t border-slate-700 gap-2'):
                    render_quick_commands()

            ssh_dialog_state['dialog'] = ssh_dialog
            logger.info(f"[SingleSSH] dialog opened | key={server_dialog_key}")
            ssh_dialog.open()
            asyncio.create_task(_start_terminal())

        @ui.refreshable
        async def render_node_list():
            xui_nodes = await fetch_inbounds_safe(server_conf, force_refresh=False)
            if xui_nodes is None:
                xui_nodes = []
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
                                ui.button(icon='edit', on_click=lambda i=n: open_inbound_dialog(mgr, i, on_edit_success)).props(btn_props).classes('text-blue-400 hover:bg-slate-600')
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
                except Exception as e:
                    logger.error(f"SSH 强制刷新失败: {e}")
            else:
                try:
                    await fetch_inbounds_safe(server_conf, force_refresh=True)
                except:
                    pass
            render_node_list.refresh()

        REFRESH_CURRENT_NODES = reload_and_refresh_ui

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
                ui.label(f"节点: {node_data.get('remark')}").classes('text-sm font-bold text-gray-800')
                ui.label('即将执行以下操作：').classes('text-xs text-gray-500 mt-2')

                domain_to_del = None
                raw_link = node_data.get('_raw_link', '')
                if raw_link and '://' in raw_link:
                    try:
                        from urllib.parse import parse_qs, urlparse
                        query = urlparse(raw_link).query
                        params = parse_qs(query)
                        if 'sni' in params:
                            domain_to_del = params['sni'][0]
                        elif 'host' in params:
                            domain_to_del = params['host'][0]
                    except:
                        pass

                with ui.column().classes('ml-2 gap-1 mt-1'):
                    ui.label('1. 停止 Xray 服务并清除残留进程').classes('text-xs text-gray-600')
                    ui.label('2. 删除 Xray 配置文件').classes('text-xs text-gray-600')
                    if domain_to_del and ADMIN_CONFIG.get('cf_root_domain') in domain_to_del:
                        ui.label(f'3. 🗑️ 自动删除 CF 解析: {domain_to_del}').classes('text-xs text-red-500 font-bold')
                    else:
                        ui.label('3. 跳过 DNS 清理 (非托管域名)').classes('text-xs text-gray-400')

                async def start_uninstall():
                    d.close()
                    notification = ui.notification(message='正在执行卸载与清理...', timeout=0, spinner=True)
                    if domain_to_del:
                        cf = CloudflareHandler()
                        if cf.token and cf.root_domain and (cf.root_domain in domain_to_del):
                            ok, msg = await cf.delete_record_by_domain(domain_to_del)
                            if ok:
                                safe_notify(f"☁️ {msg}", 'positive')
                            else:
                                safe_notify(f"⚠️ DNS 删除失败: {msg}", 'warning')
                    success, output = await run.io_bound(lambda: _ssh_exec_wrapper(server_conf, XHTTP_UNINSTALL_SCRIPT))
                    notification.dismiss()
                    if success:
                        safe_notify('✅ 服务已卸载，进程已清理', 'positive')
                    else:
                        safe_notify(f'⚠️ SSH 卸载可能有残留: {output}', 'warning')
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
                        ip_addr = server_conf.get('ssh_host') or server_conf.get('url', '').replace('http://', '').replace('https://', '').split(':')[0]
                        ui.label(ip_addr).classes('text-xs font-mono font-bold text-slate-400 bg-[#0f172a] px-2 py-0.5 rounded border border-slate-700')
                        ui.label(runtime_snapshot.get('os', '--')).classes('text-xs text-slate-400 bg-slate-800 px-2 py-0.5 rounded border border-slate-700')

                        @ui.refreshable
                        def live_status_badge():
                            import time as _time
                            is_online = False
                            now_ts = _time.time()
                            probe_cache = PROBE_DATA_CACHE.get(server_conf['url'])
                            if probe_cache and (now_ts - probe_cache.get('last_updated', 0) < 20):
                                is_online = True
                            elif server_conf.get('_status') == 'online':
                                is_online = True
                            if is_online:
                                ui.badge('Online', color='green').props('rounded outline size=xs')
                            else:
                                ui.badge('Offline', color='grey').props('rounded outline size=xs')

                        live_status_badge()
                        ui.timer(3.0, live_status_badge.refresh)

            with ui.row().classes('items-center justify-end'):
                if server_conf.get('ssh_host'):
                    ui.button(icon='terminal', on_click=open_ssh_page).props('flat round size=lg color=green').classes('bg-[#0f172a] border border-slate-700 shadow-md').tooltip('打开 SSH 页面')

        ui.element('div').classes('h-4 flex-shrink-0')

        with ui.card().classes('w-full flex-shrink-0 p-0 rounded-xl border border-slate-700 border-b-[4px] border-b-slate-800 shadow-lg overflow-hidden bg-slate-900 flex flex-col'):
            with ui.row().classes('w-full items-center justify-between px-4 py-3 border-b border-slate-700 bg-[#0f172a]'):
                with ui.row().classes('items-center gap-2'):
                    ui.icon('monitor_heart').classes('text-cyan-400')
                    ui.label('VPS 运行信息').classes('text-sm font-black text-slate-300 uppercase tracking-wide')
                source_text = 'SSH 实时采集' if runtime_snapshot.get('source') == 'ssh' else '探针缓存 / 回退数据'
                ui.label(source_text).classes('text-xs text-slate-500')

            with ui.column().classes('w-full gap-4 p-4 bg-[#111827]'):
                with ui.grid().classes('w-full grid-cols-1 xl:grid-cols-2 gap-4 items-stretch'):
                    with ui.card().classes('w-full h-full bg-[#0f172a] border border-slate-700 rounded-2xl shadow-md p-4 gap-4'):
                        os_logo_url, os_logo_name = get_os_visual(runtime_snapshot.get('os', '--'))
                        render_section_header('系统信息', 'developer_board', 'text-blue-400', '操作系统 / 内核 / 架构 / 在线时间')
                        with ui.column().classes('w-full flex-1 items-center justify-center gap-2 py-2 px-3 rounded-2xl bg-slate-800/40 border border-slate-700 min-h-[88px]'):
                            ui.image(os_logo_url).classes('w-9 h-9 object-contain')
                            ui.label(runtime_snapshot.get('os', '--')).classes('text-base font-black text-slate-50 text-center break-all max-w-full')
                        with ui.column().classes('w-full gap-3 flex-1 justify-center'):
                            render_metric_row('处理器架构', format_arch_text(runtime_snapshot.get('arch', '--')))
                            render_metric_row('系统内核', runtime_snapshot.get('kernel', '--'))
                            render_metric_row('在线运行时间', runtime_snapshot.get('uptime', '--'))

                    with ui.card().classes('w-full h-full bg-[#0f172a] border border-slate-700 rounded-2xl shadow-md p-4 gap-4'):
                        render_section_header('内存信息', 'memory', 'text-green-400', '系统内存 / 缓存 / SWAP 使用情况', right_renderer=lambda: ui.label(f"已用内存：{clamp_percent(runtime_snapshot.get('mem_usage_pct', 0)):.0f}%").classes('text-sm font-black text-slate-100'))
                        with ui.column().classes('w-full flex-1 gap-3 justify-center'):
                            render_metric_row('系统总内存', fmt_gb(runtime_snapshot.get('mem_total_gb')))
                            render_metric_row('空闲内存', fmt_gb(runtime_snapshot.get('mem_free_gb')))
                            render_metric_row('真实使用内存', fmt_gb(runtime_snapshot.get('mem_used_gb')))
                            render_metric_row('系统缓存', fmt_gb(runtime_snapshot.get('mem_cache_gb')))
                            render_metric_row('SWAP 虚拟内存', f"{fmt_gb(runtime_snapshot.get('swap_used_gb'))} / {fmt_gb(runtime_snapshot.get('swap_total_gb'))}", f"剩余 {fmt_gb(runtime_snapshot.get('swap_free_gb'))} · 使用率 {clamp_percent(runtime_snapshot.get('swap_usage_pct', 0)):.0f}%")

                with ui.card().classes('w-full bg-[#0f172a] border border-slate-700 rounded-2xl shadow-md p-4 gap-4'):
                    render_section_header('磁盘信息', 'storage', 'text-amber-400', '根分区容量、已用空间、剩余空间与占用率')
                    with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-3'):
                        render_metric_row('磁盘设备', runtime_snapshot.get('disk_device', '/'))
                        render_metric_row('总容量', fmt_gb(runtime_snapshot.get('disk_total_gb')))
                        render_metric_row('空闲剩余', fmt_gb(runtime_snapshot.get('disk_free_gb')))
                        render_metric_row('已用容量', f"{fmt_gb(runtime_snapshot.get('disk_used_gb'))} ({clamp_percent(runtime_snapshot.get('disk_usage_pct', 0)):.0f}%)")

        ui.element('div').classes('h-6 flex-shrink-0')

        with ui.card().classes('w-full flex-shrink-0 flex flex-col p-0 rounded-xl border border-slate-700 border-b-[4px] border-b-slate-800 shadow-sm overflow-hidden bg-[#1e293b]'):
            with ui.row().classes('w-full items-center justify-between p-3 bg-[#0f172a] border-b border-slate-700 gap-3 flex-wrap'):
                with ui.row().classes('items-center gap-2'):
                    ui.label('节点列表').classes('text-sm font-black text-slate-400 uppercase tracking-wide ml-1')
                    if server_conf.get('probe_installed') and server_conf.get('ssh_host'):
                        ui.badge('Root 模式', color='teal').props('outline rounded size=xs')
                    elif server_conf.get('user'):
                        ui.badge('API 托管模式', color='blue').props('outline rounded size=xs')
                with ui.row().classes('items-center gap-2 flex-wrap justify-end'):
                    from app.services.deployment import open_deploy_hysteria_dialog, open_deploy_snell_dialog, open_deploy_xhttp_dialog

                    ui.button('一键部署 XHTTP', icon='rocket_launch', on_click=lambda: open_deploy_xhttp_dialog(server_conf, reload_and_refresh_ui)).props('unelevated').classes(btn_blue)
                    ui.button('一键部署 Hy2', icon='bolt', on_click=lambda: open_deploy_hysteria_dialog(server_conf, reload_and_refresh_ui)).props('unelevated').classes(btn_blue)
                    ui.button('一键部署 Snell', icon='security', on_click=lambda: open_deploy_snell_dialog(server_conf, reload_and_refresh_ui)).props('unelevated').classes(btn_blue)
                    if has_manager_access:
                        async def on_add_success():
                            ui.notify('添加节点成功')
                            await reload_and_refresh_ui()
                        ui.button('新建 XUI 节点', icon='add', on_click=lambda: open_inbound_dialog(mgr, None, on_add_success)).props('unelevated').classes(btn_green)
                    else:
                        ui.button('探针只读', icon='visibility', on_click=None).props('unelevated disabled').classes('bg-slate-700 text-slate-400 rounded-lg px-4 py-2 border-b-4 border-slate-800 text-xs font-bold opacity-70')

            with ui.element('div').classes('grid w-full gap-4 font-bold text-slate-500 border-b border-slate-700 pb-2 pt-2 px-2 text-xs uppercase tracking-wider bg-[#1e293b]').style(SINGLE_COLS_NO_PING):
                ui.label('节点名称').classes('text-left pl-2')
                for h in ['类型', '流量', '协议', '端口', '状态', '操作']:
                    ui.label(h).classes('text-center')

            with ui.scroll_area().classes('w-full h-[264px] bg-[#0f172a] p-1 flex-shrink-0'):
                await render_node_list()

        if has_manager_access and not NODES_DATA.get(server_conf['url']):
            ui.timer(0.2, lambda: asyncio.create_task(reload_and_refresh_ui()), once=True)


async def render_aggregated_view(server_list, show_ping=False, token=None, initial_page=1):
    parent_client = ui.context.client
    list_container = ui.column().classes('w-full gap-3 p-1')

    cols_ping = 'grid-template-columns: 2fr 2fr 1.5fr 1.5fr 1fr 1fr 1.5fr'
    cols_no_ping = 'grid-template-columns: 2fr 2fr 1.5fr 1.5fr 1fr 1fr 0.5fr 1.5fr'

    try:
        is_all_servers = (len(server_list) == len(SERVERS_CACHE) and not show_ping)
        use_special_mode = is_all_servers or show_ping
        current_css = COLS_SPECIAL_WITH_PING if use_special_mode else COLS_NO_PING
    except:
        current_css = cols_ping if show_ping else cols_no_ping

    PAGE_SIZE = 30
    total_items = len(server_list)
    total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE
    if initial_page > total_pages:
        initial_page = 1
    if initial_page < 1:
        initial_page = 1

    def render_page(page_num):
        list_container.clear()
        CURRENT_VIEW_STATE['page'] = page_num

        with list_container:
            with ui.row().classes('w-full justify-between items-center px-2 mb-2'):
                ui.label(f'共 {total_items} 台服务器 (第 {page_num}/{total_pages} 页)').classes('text-xs text-slate-400 font-bold')
                if total_pages > 1:
                    ui.pagination(1, total_pages, direction_links=True, value=page_num).props('dense flat color=blue text-color=slate-400 active-text-color=white').on_value_change(lambda e: handle_pagination_click(e.value))

            with ui.element('div').classes('grid w-full gap-4 font-bold text-slate-500 border-b border-slate-700 pb-2 px-6 mb-1 uppercase tracking-wider text-xs bg-[#1e293b] rounded-t-lg pt-3').style(current_css):
                ui.label('服务器').classes('text-left pl-1')
                ui.label('节点名称').classes('text-left pl-1')
                if use_special_mode:
                    ui.label('在线状态 / IP').classes('text-center')
                else:
                    ui.label('所在组').classes('text-center')
                ui.label('已用流量').classes('text-center')
                ui.label('协议').classes('text-center')
                ui.label('端口').classes('text-center')
                if not use_special_mode:
                    ui.label('状态').classes('text-center')
                ui.label('操作').classes('text-center')

            start_idx = (page_num - 1) * PAGE_SIZE
            end_idx = start_idx + PAGE_SIZE
            current_page_data = server_list[start_idx:end_idx]

            for srv in current_page_data:
                panel_n = NODES_DATA.get(srv['url'], []) or []
                custom_n = srv.get('custom_nodes', []) or []
                for cn in custom_n:
                    cn['_is_custom'] = True
                all_nodes = panel_n + custom_n

                if not all_nodes:
                    draw_row(srv, None, current_css, use_special_mode, is_first=True)
                    continue

                for index, node in enumerate(all_nodes):
                    draw_row(srv, node, current_css, use_special_mode, is_first=(index == 0))

            if total_pages > 1:
                with ui.row().classes('w-full justify-center mt-4'):
                    ui.pagination(1, total_pages, direction_links=True, value=page_num).props('dense flat color=blue text-color=slate-400 active-text-color=white').on_value_change(lambda e: handle_pagination_click(e.value))

    def handle_pagination_click(new_page):
        try:
            target_page = int(new_page)
        except:
            return

        current_scope = CURRENT_VIEW_STATE.get('scope', 'ALL')
        current_data = CURRENT_VIEW_STATE.get('data', None)
        print(f"👉 [Debug] 翻页至: {target_page} (自然浏览)", flush=True)

        with parent_client:
            from app.ui.pages.content_router import refresh_content

            asyncio.create_task(refresh_content(scope=current_scope, data=current_data, force_refresh=False, sync_name_action=True, page_num=target_page, manual_client=parent_client))

    render_page(initial_page)
