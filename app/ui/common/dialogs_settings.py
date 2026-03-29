from nicegui import ui

from app.core.state import ADMIN_CONFIG
from app.storage.repositories import save_admin_config
from app.ui.common.notifications import safe_notify


def open_cloudflare_settings_dialog():
    with ui.dialog() as d, ui.card().classes('w-[500px] p-6 flex flex-col gap-4'):
        with ui.row().classes('items-center gap-2 text-orange-600 mb-2'):
            ui.icon('cloud', size='md')
            ui.label('Cloudflare API 配置').classes('text-lg font-bold')

        ui.label('用于自动解析域名、开启 CDN 和设置 SSL (Flexible)。').classes('text-xs text-gray-500')

        cf_token = ui.input('API Token', value=ADMIN_CONFIG.get('cf_api_token', '')).props('outlined dense type=password').classes('w-full')
        ui.label('权限要求: Zone.DNS (Edit), Zone.Settings (Edit)').classes('text-[10px] text-gray-400 ml-1')

        cf_domain_root = ui.input('根域名 (例如: example.com)', value=ADMIN_CONFIG.get('cf_root_domain', '')).props('outlined dense').classes('w-full')

        async def save_cf():
            ADMIN_CONFIG['cf_api_token'] = cf_token.value.strip()
            ADMIN_CONFIG['cf_root_domain'] = cf_domain_root.value.strip()
            await save_admin_config()
            safe_notify('✅ Cloudflare 配置已保存', 'positive')
            d.close()

        with ui.row().classes('w-full justify-end mt-4'):
            ui.button('取消', on_click=d.close).props('flat color=grey')
            ui.button('保存配置', on_click=save_cf).classes('bg-orange-600 text-white shadow-md')
    d.open()


def open_probe_settings_dialog():
    with ui.dialog() as d, ui.card().classes('w-full max-w-2xl p-6 flex flex-col gap-4'):
        with ui.row().classes('justify-between items-center w-full border-b pb-2'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('tune', color='primary').classes('text-xl')
                ui.label('探针与监控设置').classes('text-lg font-bold')
            ui.button(icon='close', on_click=d.close).props('flat round dense color=grey')

        with ui.scroll_area().classes('w-full h-[60vh] pr-4'):
            with ui.column().classes('w-full gap-6'):
                with ui.column().classes('w-full bg-blue-50 p-4 rounded-lg border border-blue-100'):
                    ui.label('📡 主控端外部地址 (Agent连接地址)').classes('text-sm font-bold text-blue-900')
                    ui.label('Agent 将向此地址推送数据。请填写 http://公网IP:端口 或 https://域名').classes('text-xs text-blue-700 mb-2')
                    default_url = ADMIN_CONFIG.get('manager_base_url', 'http://xui-manager:8080')
                    url_input = ui.input(value=default_url, placeholder='http://1.2.3.4:8080').classes('w-full bg-white').props('outlined dense')

                with ui.column().classes('w-full'):
                    ui.label('🚀 三网延迟测速目标 (Ping)').classes('text-sm font-bold text-gray-700')
                    ui.label('修改后需点击“更新探针”才能在服务器上生效。').classes('text-xs text-gray-400 mb-2')

                    with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-3 gap-3'):
                        ping_ct = ui.input('电信目标 IP', value=ADMIN_CONFIG.get('ping_target_ct', '202.102.192.68')).props('outlined dense')
                        ping_cu = ui.input('联通目标 IP', value=ADMIN_CONFIG.get('ping_target_cu', '112.122.10.26')).props('outlined dense')
                        ping_cm = ui.input('移动目标 IP', value=ADMIN_CONFIG.get('ping_target_cm', '211.138.180.2')).props('outlined dense')

                with ui.column().classes('w-full'):
                    ui.label('🤖 Telegram 通知 ').classes('text-sm font-bold text-gray-700')
                    ui.label('用于掉线报警等通知 (当前版本尚未实装)').classes('text-xs text-gray-400 mb-2')

                    with ui.grid().classes('w-full grid-cols-1 sm:grid-cols-2 gap-3'):
                        tg_token = ui.input('Bot Token', value=ADMIN_CONFIG.get('tg_bot_token', '')).props('outlined dense')
                        tg_id = ui.input('Chat ID', value=ADMIN_CONFIG.get('tg_chat_id', '')).props('outlined dense')

        async def save_settings():
            url_val = url_input.value.strip().rstrip('/')
            if url_val:
                ADMIN_CONFIG['manager_base_url'] = url_val

            ADMIN_CONFIG['ping_target_ct'] = ping_ct.value.strip()
            ADMIN_CONFIG['ping_target_cu'] = ping_cu.value.strip()
            ADMIN_CONFIG['ping_target_cm'] = ping_cm.value.strip()

            ADMIN_CONFIG['tg_bot_token'] = tg_token.value.strip()
            ADMIN_CONFIG['tg_chat_id'] = tg_id.value.strip()

            await save_admin_config()
            safe_notify('✅ 设置已保存 (请记得重新安装/更新探针以应用新配置)', 'positive')
            d.close()

        ui.button('保存设置', icon='save', on_click=save_settings).classes('w-full bg-slate-900 text-white shadow-lg h-12')
    d.open()
