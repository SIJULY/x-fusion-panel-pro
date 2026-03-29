import base64
import io
import uuid

import pyotp
import qrcode
from fastapi import Request
from nicegui import app, ui

from app.core.config import ADMIN_PASS, ADMIN_USER
from app.core.state import ADMIN_CONFIG
from app.storage.repositories import save_admin_config
from app.ui.common.notifications import safe_copy_to_clipboard
from app.utils.geo import fetch_geo_from_ip


def login_page(request: Request):
    ui.add_head_html('''
    <script>
        document.addEventListener('DOMContentLoaded', function() {
            let fp = localStorage.getItem('fp_device_id');
            if (!fp) {
                fp = 'dev-' + Math.random().toString(36).substr(2, 9) + '-' + Date.now().toString(36);
                localStorage.setItem('fp_device_id', fp);
            }
            document.cookie = "fp_device_id=" + fp + "; path=/; max-age=315360000";
        });
    </script>
    ''')

    container = ui.card().classes('absolute-center w-full max-w-sm p-8 shadow-2xl rounded-xl bg-white')

    def render_step1():
        container.clear()
        with container:
            ui.label('X-Fusion Panel').classes('text-2xl font-extrabold mb-2 w-full text-center text-slate-800')
            ui.label('请登录以继续').classes('text-sm text-gray-400 mb-6 w-full text-center')

            username = ui.input('账号').props('outlined dense').classes('w-full mb-3')
            password = ui.input('密码', password=True).props('outlined dense').classes('w-full mb-6').on('keydown.enter', lambda: check_cred())

            def check_cred():
                if username.value == ADMIN_USER and password.value == ADMIN_PASS:
                    check_mfa()
                else:
                    ui.notify('账号或密码错误', color='negative', position='top')

            ui.button('下一步', on_click=check_cred).classes('w-full bg-slate-900 text-white shadow-lg h-10')
            ui.label('© Powered by 小龙女她爸').classes('text-xs text-gray-400 mt-6 w-full text-center font-mono opacity-80')

    def check_mfa():
        secret = ADMIN_CONFIG.get('mfa_secret')
        if not secret:
            new_secret = pyotp.random_base32()
            render_setup(new_secret)
        else:
            render_verify(secret)

    def render_setup(secret):
        container.clear()

        totp_uri = pyotp.totp.TOTP(secret).provisioning_uri(name=ADMIN_USER, issuer_name="X-Fusion Panel")
        qr = qrcode.make(totp_uri)
        img_buffer = io.BytesIO()
        qr.save(img_buffer, format='PNG')
        img_b64 = base64.b64encode(img_buffer.getvalue()).decode('utf-8')

        with container:
            ui.label('绑定二次验证 (MFA)').classes('text-xl font-bold mb-2 w-full text-center')
            ui.label('请使用 Authenticator App 扫描').classes('text-xs text-gray-400 mb-2 w-full text-center')

            with ui.row().classes('w-full justify-center mb-2'):
                ui.image(f'data:image/png;base64,{img_b64}').style('width: 180px; height: 180px')

            with ui.row().classes('w-full justify-center items-center gap-1 mb-4 bg-gray-100 p-1 rounded cursor-pointer').on('click', lambda: safe_copy_to_clipboard(secret)):
                ui.label(secret).classes('text-xs font-mono text-gray-600')
                ui.icon('content_copy').classes('text-gray-400 text-xs')

            code = ui.input('验证码', placeholder='6位数字').props('outlined dense input-class=text-center').classes('w-full mb-4')

            async def confirm():
                totp = pyotp.TOTP(secret)
                if totp.verify(code.value):
                    ADMIN_CONFIG['mfa_secret'] = secret
                    await save_admin_config()
                    ui.notify('绑定成功', type='positive')
                    finish()
                else:
                    ui.notify('验证码错误', type='negative')

            ui.button('确认绑定', on_click=confirm).classes('w-full bg-green-600 text-white h-10')

    def render_verify(secret):
        container.clear()
        with container:
            ui.label('安全验证').classes('text-xl font-bold mb-6 w-full text-center')
            with ui.column().classes('w-full items-center mb-6'):
                ui.icon('verified_user').classes('text-6xl text-blue-600 mb-2')
                ui.label('请输入 Authenticator 动态码').classes('text-xs text-gray-400')

            code = ui.input(placeholder='------').props('outlined input-class=text-center text-xl tracking-widest').classes('w-full mb-6')
            code.on('keydown.enter', lambda: verify())
            ui.timer(0.1, lambda: ui.run_javascript('document.querySelector(".q-field__native").focus()'), once=True)

            def verify():
                totp = pyotp.TOTP(secret)
                if totp.verify(code.value):
                    finish()
                else:
                    ui.notify('无效的验证码', type='negative', position='top')
                    code.value = ''

            ui.button('验证登录', on_click=verify).classes('w-full bg-slate-900 text-white h-10')
            ui.button('返回', on_click=render_step1).props('flat dense').classes('w-full mt-2 text-gray-400 text-xs')

    def finish():
        app.storage.user['authenticated'] = True

        if 'session_version' not in ADMIN_CONFIG:
            ADMIN_CONFIG['session_version'] = str(uuid.uuid4())[:8]
        app.storage.user['session_version'] = ADMIN_CONFIG['session_version']

        try:
            client_ip = request.headers.get('X-Forwarded-For', request.client.host).split(',')[0].strip()
            client_device_id = request.cookies.get('fp_device_id', 'Unknown_Device')
            app.storage.user['last_known_ip'] = client_ip
            app.storage.user['device_id'] = client_device_id
            geo = fetch_geo_from_ip(client_ip)
            if geo and len(geo) >= 4:
                app.storage.user['login_region'] = f"{geo[2]}-{geo[3]}"
            else:
                app.storage.user['login_region'] = '未知区域'
        except:
            pass

        ui.navigate.to('/')

    render_step1()


def check_auth(request: Request):
    """
    检查用户是否已登录，且会话版本是否有效
    """
    if not app.storage.user.get('authenticated', False):
        return False

    current_global_ver = ADMIN_CONFIG.get('session_version', 'init')
    user_ver = app.storage.user.get('session_version', '')

    if current_global_ver != user_ver:
        return False

    return True
