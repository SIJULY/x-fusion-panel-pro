import asyncio

from nicegui import run, ui

from app.core.config import (
    HYSTERIA_INSTALL_SCRIPT_TEMPLATE,
    SNELL_INSTALL_SCRIPT_TEMPLATE,
    XHTTP_INSTALL_SCRIPT_TEMPLATE,
)
from app.services.cloudflare import CloudflareHandler
from app.services.ssh import _ssh_exec_wrapper
from app.storage.repositories import save_servers
from app.utils.encoding import parse_vless_link_to_node


async def open_deploy_xhttp_dialog(server_conf, callback):
    # 1. 准备 IP
    target_host = server_conf.get('ssh_host') or server_conf.get('url', '').replace('http://', '').replace('https://', '').split(':')[0]
    real_ip = target_host
    import re, socket
    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target_host):
        try:
            real_ip = await run.io_bound(socket.gethostbyname, target_host)
        except:
            from app.ui.common.notifications import safe_notify

            safe_notify(f"❌ 无法解析 IP: {target_host}", "negative")
            return

    # 2. 检查 CF
    cf_handler = CloudflareHandler()
    if not cf_handler.token or not cf_handler.root_domain:
        from app.ui.common.notifications import safe_notify

        safe_notify("❌ 请先配置 Cloudflare API", "negative")
        return

    # 3. 生成域名
    import random, string
    rand_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    sub_prefix = f"node-{real_ip.replace('.', '-')}-{rand_suffix}"
    target_domain = f"{sub_prefix}.{cf_handler.root_domain}"

    with ui.dialog() as d, ui.card().classes('w-[500px] p-0 gap-0 overflow-hidden rounded-xl bg-[#1e293b] border border-slate-700 shadow-2xl'):
        with ui.column().classes('w-full bg-[#0f172a] p-6 gap-2 border-b border-slate-700'):
            with ui.row().classes('items-center gap-2 text-white'):
                ui.icon('rocket_launch', size='md').classes('text-blue-400')
                ui.label('部署 XHTTP-Reality (V76)').classes('text-lg font-bold')
            ui.label(f"部署目标: {target_domain}").classes('text-xs text-green-400 font-mono')

        with ui.column().classes('w-full p-6 gap-4'):
            ui.label('节点备注名称').classes('text-xs font-bold text-slate-500 mb-[-8px]')
            remark_input = ui.input(placeholder=f'默认: Reality-{target_domain}').props('outlined dense clearable dark').classes('w-full')
            log_area = ui.log().classes('w-full h-48 bg-black text-green-400 text-[11px] font-mono p-3 rounded border border-slate-700 hidden transition-all')

        with ui.row().classes('w-full p-4 bg-[#0f172a] border-t border-slate-700 justify-end gap-3'):
            btn_cancel = ui.button('取消', on_click=d.close).props('flat color=grey')

            async def run_deploy_script():
                try:
                    log_area.push(f"🔄 [CF] 添加解析: {target_domain} -> {real_ip}...")
                    success, msg = await cf_handler.auto_configure(real_ip, sub_prefix)
                    if not success:
                        raise Exception(f"CF配置失败: {msg}")

                    log_area.push(f"🚀 [SSH] 开始执行安装脚本...")

                    deploy_cmd = f"""
cat > /tmp/install_xhttp.sh << 'EOF_SCRIPT'
{XHTTP_INSTALL_SCRIPT_TEMPLATE}
EOF_SCRIPT
bash /tmp/install_xhttp.sh "{target_domain}"
"""
                    success, output = await run.io_bound(lambda: _ssh_exec_wrapper(server_conf, deploy_cmd))

                    if success:
                        match = re.search(r'DEPLOY_SUCCESS_LINK: (vless://.*)', output)
                        if match:
                            link = match.group(1).strip()
                            log_area.push("✅ 部署成功！正在保存...")

                            custom_name = remark_input.value.strip()
                            final_remark = custom_name if custom_name else f"Reality-{target_domain}"
                            node_data = parse_vless_link_to_node(link, remark_override=final_remark)

                            if node_data:
                                if 'custom_nodes' not in server_conf:
                                    server_conf['custom_nodes'] = []
                                server_conf['custom_nodes'].append(node_data)
                                await save_servers()
                                from app.ui.common.notifications import safe_notify

                                safe_notify(f"✅ 节点已添加", "positive")
                                await asyncio.sleep(1)
                                d.close()
                                if callback:
                                    await callback()
                            else:
                                log_area.push("❌ 链接解析失败")
                        else:
                            log_area.push("❌ 未捕获链接，请检查日志")
                            log_area.push(output[-500:])
                    else:
                        log_area.push(f"❌ SSH 执行出错: {output}")
                except Exception as e:
                    log_area.push(f"❌ 异常: {str(e)}")
                finally:
                    btn_deploy.props(remove='loading')
                    btn_cancel.enable()

            async def start_process():
                btn_cancel.disable()
                btn_deploy.props('loading')
                log_area.classes(remove='hidden')

                log_area.push("🔍 正在检查端口占用 (80/443)...")

                check_cmd = "netstat -tlpn | grep -E ':80 |:443 ' || lsof -i :80 -i :443"
                is_occupied = False
                check_output = ""

                try:
                    success, output = await run.io_bound(lambda: _ssh_exec_wrapper(server_conf, check_cmd))
                    if success and output.strip():
                        is_occupied = True
                        check_output = output.strip()
                except:
                    pass

                if is_occupied:
                    log_area.push("⚠️ 端口被占用！等待确认...")

                    with ui.dialog() as confirm_d, ui.card().classes('w-96 p-5 border-t-4 border-red-500 shadow-xl bg-[#1e293b]'):
                        with ui.row().classes('items-center gap-2 text-red-500 mb-2'):
                            ui.icon('warning', size='md')
                            ui.label('端口冲突警告').classes('font-bold text-lg')

                        ui.label('检测到 80 或 443 端口被占用：').classes('text-sm text-slate-300 mb-2')

                        short_log = "\n".join(check_output.split("\n")[:5])
                        ui.code(short_log).classes('w-full text-xs bg-black text-slate-300 p-2 rounded mb-3')

                        ui.label('继续部署将【强制杀掉】这些进程。').classes('text-xs font-bold text-red-400')

                        with ui.row().classes('w-full justify-end gap-2 mt-4'):
                            ui.button('取消', on_click=lambda: [confirm_d.close(), d.close()]).props('flat color=grey')

                            async def confirm_force():
                                confirm_d.close()
                                log_area.push("⚔️ 用户确认强制霸占，继续...")
                                await run_deploy_script()

                            ui.button('强制部署', color='red', on_click=confirm_force).props('unelevated')

                    confirm_d.open()

                else:
                    log_area.push("✅ 端口空闲，开始部署...")
                    await run_deploy_script()

            btn_deploy = ui.button('开始部署', on_click=start_process).classes('bg-blue-600 text-white shadow-lg font-bold')

    d.open()


async def open_deploy_hysteria_dialog(server_conf, callback):
    # --- 1. IP 获取逻辑 ---
    target_host = server_conf.get('ssh_host') or server_conf.get('url', '').replace('http://', '').replace('https://', '').split(':')[0]
    real_ip = target_host
    import re, socket, urllib.parse, uuid, asyncio

    if not re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", target_host):
        try:
            real_ip = await run.io_bound(socket.gethostbyname, target_host)
        except:
            from app.ui.common.notifications import safe_notify

            safe_notify(f"❌ 无法解析 IP: {target_host}", "negative")
            return

    with ui.dialog() as d, ui.card().classes('w-[500px] p-0 gap-0 overflow-hidden rounded-xl bg-[#1e293b] border border-slate-700 shadow-2xl'):
        with ui.column().classes('w-full bg-[#0f172a] border-b border-slate-700 p-6 gap-2'):
            with ui.row().classes('items-center gap-2 text-white'):
                ui.icon('bolt', size='md').classes('text-blue-400')
                ui.label('部署 Hysteria 2 (Surge 兼容版)').classes('text-lg font-bold')
            ui.label(f"服务器 IP: {real_ip}").classes('text-xs text-gray-400 font-mono')

        with ui.column().classes('w-full p-6 gap-4'):
            name_input = ui.input('节点备注 (可选)', placeholder='例如: 狮城 Hy2').props('outlined dense dark').classes('w-full')
            sni_input = ui.input('伪装域名 (SNI)', value='www.bing.com').props('outlined dense dark').classes('w-full')

            enable_hopping = ui.checkbox('启用端口跳跃', value=True).props('dark').classes('text-sm font-bold text-slate-300')
            with ui.row().classes('w-full items-center gap-2'):
                hop_start = ui.number('起始端口', value=20000, format='%.0f').props('outlined dense dark').classes('flex-1').bind_visibility_from(enable_hopping, 'value')
                ui.label('-').classes('text-slate-400').bind_visibility_from(enable_hopping, 'value')
                hop_end = ui.number('结束端口', value=50000, format='%.0f').props('outlined dense dark').classes('flex-1').bind_visibility_from(enable_hopping, 'value')

            log_area = ui.log().classes('w-full h-48 bg-black text-green-400 text-[11px] font-mono p-3 rounded border border-slate-700 hidden transition-all')

        with ui.row().classes('w-full p-4 bg-[#0f172a] border-t border-slate-700 justify-end gap-3'):
            btn_cancel = ui.button('取消', on_click=d.close).props('flat color=grey')

            async def start_process():
                btn_cancel.disable()
                btn_deploy.props('loading')
                log_area.classes(remove='hidden')
                try:
                    hy2_password = str(uuid.uuid4()).replace('-', '')[:16]
                    params = {
                        "password": hy2_password,
                        "sni": sni_input.value,
                        "enable_hopping": "true" if enable_hopping.value else "false",
                        "port_range_start": int(hop_start.value),
                        "port_range_end": int(hop_end.value),
                    }

                    script_content = HYSTERIA_INSTALL_SCRIPT_TEMPLATE.format(**params)
                    deploy_cmd = f"cat > /tmp/install_hy2.sh << 'EOF_SCRIPT'\n{script_content}\nEOF_SCRIPT\nbash /tmp/install_hy2.sh"

                    log_area.push(f"🚀 [SSH] 连接到 {real_ip} 开始安装...")
                    success, output = await run.io_bound(lambda: _ssh_exec_wrapper(server_conf, deploy_cmd))

                    if success:
                        match = re.search(r'HYSTERIA_DEPLOY_SUCCESS_LINK: (hy2://.*)', output)
                        if match:
                            link = match.group(1).strip()
                            log_area.push("🎉 部署成功！")

                            custom_name = name_input.value.strip()
                            node_name = custom_name if custom_name else f"Hy2-{real_ip[-3:]}"

                            if enable_hopping.value:
                                final_port_display = f"{int(hop_start.value)}-{int(hop_end.value)}"
                            else:
                                try:
                                    final_port_display = int(link.split('@')[1].split(':')[1].split('?')[0])
                                except:
                                    final_port_display = 443

                            if '#' in link:
                                link = link.split('#')[0]
                            final_raw_link = f"{link}#{urllib.parse.quote(node_name)}"

                            new_node = {
                                "id": str(uuid.uuid4()),
                                "remark": node_name,
                                "port": final_port_display,
                                "protocol": "hysteria2",
                                "settings": {},
                                "streamSettings": {},
                                "enable": True,
                                "_is_custom": True,
                                "_raw_link": final_raw_link,
                            }
                            if 'custom_nodes' not in server_conf:
                                server_conf['custom_nodes'] = []
                            server_conf['custom_nodes'].append(new_node)
                            await save_servers()

                            from app.ui.common.notifications import safe_notify

                            safe_notify(f"✅ 节点 {node_name} 已添加", "positive")
                            await asyncio.sleep(1)
                            d.close()
                            if callback:
                                await callback()
                        else:
                            log_area.push("❌ 未捕获链接")
                            log_area.push(output[-500:])
                    else:
                        log_area.push(f"❌ SSH 失败: {output}")
                except Exception as e:
                    log_area.push(f"❌ 异常: {e}")
                    print(e)
                finally:
                    btn_cancel.enable()
                    btn_deploy.props(remove='loading')

            btn_deploy = ui.button('开始部署', on_click=start_process).props('unelevated').classes('bg-blue-600 text-white')
    d.open()


async def open_deploy_snell_dialog(server_conf, callback):
    # 解析目标 IP 作为兜底
    target_host = server_conf.get('ssh_host') or server_conf.get('url', '').replace('http://', '').replace('https://', '').split(':')[0]
    import random, string, uuid, urllib.parse

    with ui.dialog() as d, ui.card().classes('w-[500px] p-0 gap-0 overflow-hidden rounded-xl bg-[#1e293b] border border-slate-700 shadow-2xl'):
        with ui.column().classes('w-full bg-[#0f172a] border-b border-slate-700 p-6 gap-2'):
            with ui.row().classes('items-center gap-2 text-white'):
                ui.icon('security', size='md').classes('text-blue-400')
                ui.label('部署 Snell 节点 (v5 最新版)').classes('text-lg font-bold')
            ui.label(f"目标服务器: {target_host}").classes('text-xs text-gray-400 font-mono')

        with ui.column().classes('w-full p-6 gap-4'):
            name_input = ui.input('节点备注', placeholder='例如: HK-Snell-v5').props('outlined dense dark').classes('w-full')

            with ui.row().classes('w-full gap-2 items-center'):
                rand_port = random.randint(30000, 60000)
                rand_psk = ''.join(random.choices(string.ascii_letters + string.digits, k=20))

                port_input = ui.number('端口', value=rand_port, format='%.0f').props('outlined dense dark').classes('w-1/3')
                psk_input = ui.input('密钥 (PSK)', value=rand_psk).props('outlined dense dark').classes('flex-grow')

            log_area = ui.log().classes('w-full h-48 bg-black text-green-400 text-[11px] font-mono p-3 rounded border border-slate-700 hidden transition-all')

        with ui.row().classes('w-full p-4 bg-[#0f172a] border-t border-slate-700 justify-end gap-3'):
            btn_cancel = ui.button('取消', on_click=d.close).props('flat color=grey')

            async def start_process():
                btn_cancel.disable()
                btn_deploy.props('loading')
                log_area.classes(remove='hidden')
                try:
                    params = {
                        "port": int(port_input.value),
                        "psk": psk_input.value,
                        "target_ip": target_host,
                    }
                    script_content = SNELL_INSTALL_SCRIPT_TEMPLATE.format(**params)
                    deploy_cmd = f"cat > /tmp/install_snell.sh << 'EOF_SCRIPT'\n{script_content}\nEOF_SCRIPT\nbash /tmp/install_snell.sh"

                    log_area.push(f"🚀 [SSH] 开始在 {target_host} 安装 Snell v5 ...")
                    success, output = await run.io_bound(lambda: _ssh_exec_wrapper(server_conf, deploy_cmd))

                    if success:
                        import re
                        match = re.search(r'SNELL_DEPLOY_SUCCESS_LINK: (snell://.*)', output)
                        if match:
                            link = match.group(1).strip()
                            log_area.push("🎉 Snell v5 部署成功并已启动！")

                            custom_name = name_input.value.strip() or f"Snell-v5-{target_host[-3:]}"

                            if '#' in link:
                                link = link.split('#')[0]
                            final_raw_link = f"{link}#{urllib.parse.quote(custom_name)}"

                            new_node = {
                                "id": str(uuid.uuid4()),
                                "remark": custom_name,
                                "port": params['port'],
                                "protocol": "snell",
                                "settings": {},
                                "streamSettings": {},
                                "enable": True,
                                "_is_custom": True,
                                "_raw_link": final_raw_link,
                            }
                            if 'custom_nodes' not in server_conf:
                                server_conf['custom_nodes'] = []
                            server_conf['custom_nodes'].append(new_node)
                            await save_servers()

                            from app.ui.common.notifications import safe_notify

                            safe_notify(f"✅ 节点 {custom_name} 已添加", "positive")
                            await asyncio.sleep(1)
                            d.close()
                            if callback:
                                await callback()
                        else:
                            log_area.push("❌ 部署失败：未能成功启动服务。")
                            log_area.push(output[-500:])
                    else:
                        log_area.push(f"❌ SSH 连接失败: {output}")
                finally:
                    btn_cancel.enable()
                    btn_deploy.props(remove='loading')

            btn_deploy = ui.button('开始部署', on_click=start_process).props('unelevated').classes('bg-blue-600 text-white')
    d.open()
