import asyncio
import json
import random
import uuid
from datetime import datetime

from nicegui import run, ui

from app.ui.common.notifications import safe_notify


class InboundEditor:
    @staticmethod
    def _bytes_to_gb(total_bytes):
        try:
            total_bytes = int(total_bytes or 0)
            if total_bytes <= 0:
                return None
            return round(total_bytes / (1024 ** 3), 2)
        except:
            return None

    @staticmethod
    def _gb_to_bytes(total_gb):
        try:
            if total_gb in [None, '']:
                return 0
            total_gb = float(total_gb)
            if total_gb <= 0:
                return 0
            return int(total_gb * (1024 ** 3))
        except:
            raise ValueError('总流量格式无效')

    @staticmethod
    def _expiry_to_input(expiry_time):
        try:
            expiry_time = int(expiry_time or 0)
            if expiry_time <= 0:
                return ''
            if expiry_time < 10 ** 12:
                expiry_time *= 1000
            return datetime.fromtimestamp(expiry_time / 1000).strftime('%Y-%m-%d %H:%M')
        except:
            return ''

    @staticmethod
    def _input_to_expiry(value):
        if not value:
            return 0
        try:
            dt = datetime.strptime(value.replace('T', ' '), '%Y-%m-%d %H:%M')
            return int(dt.timestamp() * 1000)
        except:
            raise ValueError('到期时间格式无效')

    @staticmethod
    def _to_dict(value):
        if isinstance(value, dict):
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, dict) else {}
            except:
                return {}
        return {}

    @staticmethod
    def _to_list(value):
        if isinstance(value, list):
            return value
        if isinstance(value, str) and value.strip():
            try:
                parsed = json.loads(value)
                return parsed if isinstance(parsed, list) else []
            except:
                return []
        return []

    @staticmethod
    def _csv_to_list(value):
        return [x.strip() for x in str(value or '').split(',') if x.strip()]

    @staticmethod
    def _list_to_csv(values):
        return ', '.join([str(x).strip() for x in (values or []) if str(x).strip()])

    def __init__(self, mgr, data=None, on_success=None, is_3x_ui=False):
        self.mgr = mgr
        self.cb = on_success
        self.is_edit = data is not None
        self.is_3x_ui = is_3x_ui  # 核心状态：记录面板血统

        if not data:
            random_port = random.randint(10000, 65000)
            # 智能初始化：针对 3x-ui 默认生成防阻断配置
            default_email = f"{uuid.uuid4().hex[:8]}@fusion.com" if self.is_3x_ui else ''
            
            self.d = {
                'enable': True,
                'remark': '',
                'port': random_port,
                'protocol': 'vless' if self.is_3x_ui else 'vmess',
                'settings': {
                    'clients': [{'id': str(uuid.uuid4()), 'alterId': 0, 'email': default_email, 'flow': ''}],
                    'disableInsecureEncryption': False,
                },
                'streamSettings': {'network': 'tcp', 'security': 'none'},
                # 【防坑神器】如果是 3x-ui，默认【关闭】Sniffing，防止 Surge 等客户端断流
                'sniffing': {'enabled': not self.is_3x_ui, 'destOverride': ['http', 'tls']},
                'total': 0,
                'expiryTime': 0,
                'tag': '',
                'listen': '',
            }
            if self.is_3x_ui:
                self.d['settings']['clients'][0]['limitIp'] = 0
                self.d['settings']['clients'][0]['subId'] = uuid.uuid4().hex[:16]
        else:
            self.d = data.copy()

        if 'streamSettings' not in self.d and self.d.get('stream_settings'):
            self.d['streamSettings'] = self.d.get('stream_settings')

        self.d['settings'] = self._to_dict(self.d.get('settings'))
        self.d['streamSettings'] = self._to_dict(self.d.get('streamSettings'))
        self.d['sniffing'] = self._to_dict(self.d.get('sniffing'))
        self.d['expiryTime'] = int(self.d.get('expiryTime') or self.d.get('expiry_time') or 0)
        if 'total' not in self.d and self.d.get('totalGB'):
            self.d['total'] = self._gb_to_bytes(self.d.get('totalGB'))

        self.settings = self.d['settings']
        self.stream = self.d['streamSettings']
        self.sniffing = self.d['sniffing']

        self.d.setdefault('tag', '')
        self.d.setdefault('listen', '')
        self.d.setdefault('total', 0)

        self.sniffing.setdefault('enabled', True)
        self.sniffing.setdefault('destOverride', ['http', 'tls'])

        self.stream.setdefault('network', 'tcp')
        self.stream.setdefault('security', 'none')
        self.stream.setdefault('tcpSettings', {'header': {'type': 'none', 'request': {'path': ['/'], 'headers': {'Host': []}}}})
        self.stream.setdefault('wsSettings', {'path': '/', 'headers': {'Host': ''}})
        self.stream.setdefault('grpcSettings', {'serviceName': '', 'multiMode': False})
        self.stream.setdefault('xhttpSettings', {'mode': 'auto', 'path': '/', 'host': ''})
        self.stream.setdefault('tlsSettings', {'serverName': '', 'alpn': [], 'allowInsecure': False, 'certificates': []})
        self.stream.setdefault('realitySettings', {'serverName': '', 'publicKey': '', 'privateKey': '', 'shortId': '', 'spiderX': '/', 'fingerprint': 'chrome'})

        self._normalize_protocol_settings()

    def _normalize_protocol_settings(self):
        protocol = self.d.get('protocol', 'vmess')
        if protocol in ['vmess', 'vless']:
            clients = self._to_list(self.settings.get('clients'))
            if not clients:
                clients = [{'id': str(uuid.uuid4()), 'alterId': 0, 'email': '', 'flow': ''}]
            for client in clients:
                client.setdefault('id', str(uuid.uuid4()))
                client.setdefault('alterId', 0)
                if self.is_3x_ui:
                    client.setdefault('email', f"{uuid.uuid4().hex[:8]}@fusion.com")
                    client.setdefault('subId', uuid.uuid4().hex[:16])
                    client.setdefault('limitIp', 0)
                else:
                    client.setdefault('email', '')
                client.setdefault('flow', '')
            self.settings['clients'] = clients
            if protocol == 'vmess':
                self.settings.setdefault('disableInsecureEncryption', False)
            if protocol == 'vless':
                self.settings.setdefault('decryption', 'none')
        elif protocol == 'trojan':
            clients = self._to_list(self.settings.get('clients'))
            if not clients:
                clients = [{'password': uuid.uuid4().hex[:8], 'email': '', 'flow': ''}]
            for client in clients:
                client.setdefault('password', uuid.uuid4().hex[:8])
                if self.is_3x_ui:
                    client.setdefault('email', f"{uuid.uuid4().hex[:8]}@fusion.com")
                    client.setdefault('subId', uuid.uuid4().hex[:16])
                    client.setdefault('limitIp', 0)
                else:
                    client.setdefault('email', '')
                client.setdefault('flow', '')
            self.settings['clients'] = clients
        elif protocol == 'shadowsocks':
            self.settings.setdefault('method', 'aes-256-gcm')
            self.settings.setdefault('password', uuid.uuid4().hex[:10])
            self.settings.setdefault('network', 'tcp,udp')
        elif protocol == 'dokodemo-door':
            self.settings.setdefault('address', '1.1.1.1')
            self.settings.setdefault('port', 53)
            self.settings.setdefault('network', 'tcp,udp')
        elif protocol == 'socks':
            self.settings.setdefault('auth', 'noauth')
            self.settings.setdefault('udp', False)
            accounts = self._to_list(self.settings.get('accounts'))
            self.settings['accounts'] = accounts
        elif protocol == 'http':
            accounts = self._to_list(self.settings.get('accounts'))
            self.settings['accounts'] = accounts

    def _make_label(self, text, tooltip=None):
        row = ui.row().classes('w-32 justify-end items-center gap-1 shrink-0')
        with row:
            ui.label(text).classes('text-sm text-slate-400 font-bold tracking-wide')
            if tooltip:
                ui.icon('help', size='14px').classes('text-slate-500 cursor-help hover:text-slate-300 transition-colors').tooltip(tooltip)
        return row

    def build_ui(self, dlg):
        with ui.card().classes('w-full max-w-4xl p-0 flex flex-col gap-0 overflow-hidden shadow-2xl bg-[#1e293b] border border-slate-700'):
            # --- 标题栏 ---
            with ui.row().classes('w-full justify-between items-center px-6 py-4 border-b border-slate-700 bg-[#0f172a]'):
                with ui.row().classes('items-center gap-2'):
                    ui.label('添加入站' if not self.is_edit else '编辑入站').classes('text-lg font-black text-slate-200 tracking-wide')
                    if self.is_3x_ui:
                        ui.badge('3x-ui 专属特权开启', color='purple').props('outline rounded size=xs')
                ui.button(icon='close', on_click=dlg.close).props('flat round dense color=grey')

            # --- 内容区 ---
            with ui.scroll_area().classes('w-full h-[65vh] px-8 py-6'):
                with ui.column().classes('w-full gap-5'):
                    # Row 1: 备注 & 启用
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('备注：')
                            self.rem = ui.input(value=self.d.get('remark')).classes('flex-1 min-w-0').props('dense outlined dark')
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('启用：')
                            self.ena = ui.switch(value=self.d.get('enable', True))

                    # Row 2: 协议
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('协议：')
                            pro_opts = ['vmess', 'vless', 'trojan', 'shadowsocks', 'dokodemo-door', 'socks', 'http']
                            
                            self.pro = ui.select(pro_opts, value=self.d.get('protocol', 'vmess')).classes('flex-1 min-w-0').props('dense outlined dark options-dense')
                            def on_protocol_change(e):
                                self.d['protocol'] = e.value
                                self._normalize_protocol_settings()
                                self.render_dynamic_settings.refresh()
                            self.pro.on_value_change(on_protocol_change)

                    # Row 3: 监听 IP
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('监听 IP：', '留空默认监听所有 IP (0.0.0.0)')
                            self.listen_input = ui.input(value=self.d.get('listen', '')).classes('flex-1 min-w-0').props('dense outlined dark')

                    # Row 4: 端口 & 总流量
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('端口：')
                            self.prt = ui.number(value=self.d['port'], format='%.0f').classes('flex-1 min-w-0').props('dense outlined dark')
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('总流量(GB)：', '留空或 0 为不限制')
                            self.total_gb = ui.number(value=self._bytes_to_gb(self.d.get('total')), format='%.2f').classes('flex-1 min-w-0').props('dense outlined dark clearable')

                    # Row 5: 到期时间
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('到期时间：', '留空为不限')
                            self.expiry_time = ui.input(value=self._expiry_to_input(self.d.get('expiryTime'))).classes('flex-1 min-w-0').props('dense outlined dark type=datetime-local clearable')

                    ui.element('div').classes('w-full h-px bg-slate-700/50 my-1')

                    # --- 动态变化区域 (认证、网络、TLS、嗅探) ---
                    self.render_dynamic_settings()

            # --- 底部按钮区 ---
            with ui.row().classes('w-full justify-end items-center px-6 py-4 border-t border-slate-700 bg-[#0f172a] gap-3'):
                ui.button('关 闭', on_click=dlg.close).props('outline color=grey').classes('text-slate-300')
                ui.button('添 加' if not self.is_edit else '保 存', on_click=lambda: self.save(dlg)).props('unelevated color=primary px-6 font-bold')

    @ui.refreshable
    def render_dynamic_settings(self):
        protocol = self.d.get('protocol', 'vmess')
        # 1. 协议专属认证配置
        with ui.column().classes('w-full gap-5'):
            if protocol in ['vmess', 'vless']:
                client = self.settings.get('clients', [{}])[0]
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('id：')
                        id_inp = ui.input(value=client.get('id', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        id_inp.on_value_change(lambda e, c=client: c.update({'id': e.value}))
                        ui.button(icon='casino', on_click=lambda inp=id_inp: inp.set_value(str(uuid.uuid4()))).props('flat dense padding=xs color=primary').tooltip('重新生成')

                # 【3x-ui 专属客户管控台】
                if self.is_3x_ui:
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('伪装邮箱：', '3x-ui 内部统计标识')
                            em_inp = ui.input(value=client.get('email', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                            em_inp.on_value_change(lambda e, c=client: c.update({'email': e.value}))
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('设备 IP 限制：', '单用户同时在线 IP 限制, 0为不限制')
                            lim_inp = ui.number(value=client.get('limitIp', 0), format='%.0f').classes('flex-1 min-w-0').props('dense outlined dark')
                            lim_inp.on_value_change(lambda e, c=client: c.update({'limitIp': int(e.value or 0)}))
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('Sub ID：', '3x-ui 专属订阅参数')
                            sub_inp = ui.input(value=client.get('subId', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                            sub_inp.on_value_change(lambda e, c=client: c.update({'subId': e.value}))
                            ui.button(icon='casino', on_click=lambda inp=sub_inp: inp.set_value(uuid.uuid4().hex[:16])).props('flat dense padding=xs color=primary')

                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    if protocol == 'vmess':
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('额外 ID：')
                            alt_inp = ui.number(value=client.get('alterId', 0), format='%.0f').classes('flex-1 min-w-0').props('dense outlined dark')
                            alt_inp.on_value_change(lambda e, c=client: c.update({'alterId': int(e.value or 0)}))
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('禁用不安全加密：')
                            dis_enc = ui.switch(value=bool(self.settings.get('disableInsecureEncryption', False)))
                            dis_enc.on_value_change(lambda e: self.settings.update({'disableInsecureEncryption': bool(e.value)}))
                    elif protocol == 'vless':
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('Flow：')
                            flow_opts = ['', 'xtls-rprx-vision', 'xtls-rprx-vision-udp443']
                            flow_sel = ui.select(flow_opts, value=client.get('flow', '')).classes('flex-1 min-w-0').props('dense outlined dark options-dense')
                            flow_sel.on_value_change(lambda e, c=client: c.update({'flow': e.value}))

            elif protocol == 'trojan':
                client = self.settings.get('clients', [{}])[0]
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('密码：')
                        pwd_inp = ui.input(value=client.get('password', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        pwd_inp.on_value_change(lambda e, c=client: c.update({'password': e.value}))
                        ui.button(icon='casino', on_click=lambda inp=pwd_inp: inp.set_value(uuid.uuid4().hex[:8])).props('flat dense padding=xs color=primary')
                
                # 【3x-ui Trojan 管控台】
                if self.is_3x_ui:
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('伪装邮箱：')
                            em_inp = ui.input(value=client.get('email', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                            em_inp.on_value_change(lambda e, c=client: c.update({'email': e.value}))
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('设备 IP 限制：')
                            lim_inp = ui.number(value=client.get('limitIp', 0), format='%.0f').classes('flex-1 min-w-0').props('dense outlined dark')
                            lim_inp.on_value_change(lambda e, c=client: c.update({'limitIp': int(e.value or 0)}))
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('Sub ID：')
                            sub_inp = ui.input(value=client.get('subId', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                            sub_inp.on_value_change(lambda e, c=client: c.update({'subId': e.value}))
                            ui.button(icon='casino', on_click=lambda inp=sub_inp: inp.set_value(uuid.uuid4().hex[:16])).props('flat dense padding=xs color=primary')

            elif protocol == 'shadowsocks':
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('加密方式：')
                        methods = ['aes-256-gcm', 'aes-128-gcm', 'chacha20-ietf-poly1305', '2022-blake3-aes-128-gcm']
                        m_sel = ui.select(methods, value=self.settings.get('method', 'aes-256-gcm')).classes('flex-1 min-w-0').props('dense outlined dark options-dense')
                        m_sel.on_value_change(lambda e: self.settings.update({'method': e.value}))
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('密码：')
                        p_inp = ui.input(value=self.settings.get('password', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        p_inp.on_value_change(lambda e: self.settings.update({'password': e.value}))
                        ui.button(icon='casino', on_click=lambda inp=p_inp: inp.set_value(uuid.uuid4().hex[:10])).props('flat dense padding=xs color=primary')
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('网络：')
                        net_opts = ['tcp', 'udp', 'tcp,udp']
                        ss_net = ui.select(net_opts, value=self.settings.get('network', 'tcp,udp')).classes('flex-1 min-w-0').props('dense outlined dark options-dense')
                        ss_net.on_value_change(lambda e: self.settings.update({'network': e.value}))
            elif protocol == 'dokodemo-door':
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('目标地址：')
                        addr_inp = ui.input(value=self.settings.get('address', '1.1.1.1')).classes('flex-1 min-w-0').props('dense outlined dark')
                        addr_inp.on_value_change(lambda e: self.settings.update({'address': e.value}))
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('目标端口：')
                        p_num = ui.number(value=self.settings.get('port', 53), format='%.0f').classes('flex-1 min-w-0').props('dense outlined dark')
                        p_num.on_value_change(lambda e: self.settings.update({'port': int(e.value or 53)}))
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('网络：')
                        net_opts = ['tcp', 'udp', 'tcp,udp']
                        dd_net = ui.select(net_opts, value=self.settings.get('network', 'tcp,udp')).classes('flex-1 min-w-0').props('dense outlined dark options-dense')
                        dd_net.on_value_change(lambda e: self.settings.update({'network': e.value}))
            elif protocol == 'socks':
                accounts = self.settings.get('accounts', [])
                is_auth = self.settings.get('auth', 'noauth') == 'password'
                if is_auth and not accounts:
                    accounts = [{'user': uuid.uuid4().hex[:8], 'pass': uuid.uuid4().hex[:8]}]
                    self.settings['accounts'] = accounts
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('密码认证：')
                        auth_sw = ui.switch(value=is_auth)
                        def on_auth_change(e):
                            self.settings['auth'] = 'password' if e.value else 'noauth'
                            if e.value and not self.settings.get('accounts'):
                                self.settings['accounts'] = [{'user': uuid.uuid4().hex[:8], 'pass': uuid.uuid4().hex[:8]}]
                            self.render_dynamic_settings.refresh()
                        auth_sw.on_value_change(on_auth_change)
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        if is_auth:
                            self._make_label('用户名：')
                            usr_inp = ui.input(value=accounts[0].get('user', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                            usr_inp.on_value_change(lambda e: accounts[0].update({'user': e.value}))
                        else:
                            self._make_label('启用 udp：')
                            udp_sw = ui.switch(value=bool(self.settings.get('udp', False)))
                            udp_sw.on_value_change(lambda e: self.settings.update({'udp': bool(e.value)}))
                if is_auth:
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('密码：')
                            pwd_inp = ui.input(value=accounts[0].get('pass', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                            pwd_inp.on_value_change(lambda e: accounts[0].update({'pass': e.value}))
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('启用 udp：')
                            udp_sw = ui.switch(value=bool(self.settings.get('udp', False)))
                            udp_sw.on_value_change(lambda e: self.settings.update({'udp': bool(e.value)}))

            elif protocol == 'http':
                accounts = self.settings.get('accounts', [])
                is_auth = len(accounts) > 0
                if is_auth and not accounts:
                    accounts = [{'user': uuid.uuid4().hex[:8], 'pass': uuid.uuid4().hex[:8]}]
                    self.settings['accounts'] = accounts
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('密码认证：')
                        auth_sw = ui.switch(value=is_auth)
                        def on_http_auth_change(e):
                            if e.value:
                                self.settings['accounts'] = [{'user': uuid.uuid4().hex[:8], 'pass': uuid.uuid4().hex[:8]}]
                            else:
                                self.settings['accounts'] = []
                            self.render_dynamic_settings.refresh()
                        auth_sw.on_value_change(on_http_auth_change)
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        if is_auth:
                            self._make_label('用户名：')
                            usr_inp = ui.input(value=accounts[0].get('user', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                            usr_inp.on_value_change(lambda e: accounts[0].update({'user': e.value}))

                if is_auth:
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('密码：')
                            pwd_inp = ui.input(value=accounts[0].get('pass', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                            pwd_inp.on_value_change(lambda e: accounts[0].update({'pass': e.value}))


        # 2. 传输配置 (Network)
        net_val = self.stream.get('network', 'tcp')
        with ui.row().classes('w-full gap-4 items-center no-wrap mt-2'):
            with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                self._make_label('传输网络：')
                net_opts = ['tcp', 'kcp', 'ws', 'http', 'quic', 'grpc']
                if self.is_3x_ui:
                    net_opts.append('xhttp')  # 3x-ui 专属神级伪装协议
                net_sel = ui.select(net_opts, value=net_val).classes('flex-1 min-w-0').props('dense outlined dark options-dense')
                def on_net_change(e):
                    self.stream['network'] = e.value
                    self.render_dynamic_settings.refresh()
                net_sel.on_value_change(on_net_change)

        # 3. 传输协议细节配置 (HTTP伪装, WS Path 等)
        with ui.column().classes('w-full gap-5'):
            if net_val == 'tcp':
                tcp_header = self.stream.setdefault('tcpSettings', {}).setdefault('header', {})
                is_http = tcp_header.get('type', 'none') == 'http'
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('http 伪装：')
                        http_sw = ui.switch(value=is_http)
                        def on_http_cam_change(e):
                            tcp_header['type'] = 'http' if e.value else 'none'
                            self.render_dynamic_settings.refresh()
                        http_sw.on_value_change(on_http_cam_change)
                if is_http:
                    tcp_req = tcp_header.setdefault('request', {})
                    with ui.row().classes('w-full gap-4 items-center no-wrap'):
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('请求路径：')
                            path_inp = ui.input(value=self._list_to_csv(tcp_req.get('path', ['/']))).classes('flex-1 min-w-0').props('dense outlined dark')
                            path_inp.on_value_change(lambda e: tcp_req.update({'path': self._csv_to_list(e.value) or ['/']}))
                        with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                            self._make_label('请求 Host：')
                            host_inp = ui.input(value=self._list_to_csv(tcp_req.setdefault('headers', {}).get('Host', []))).classes('flex-1 min-w-0').props('dense outlined dark')
                            host_inp.on_value_change(lambda e: tcp_req['headers'].update({'Host': self._csv_to_list(e.value)}))
            elif net_val == 'ws':
                ws = self.stream.setdefault('wsSettings', {})
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('路径：')
                        w_path = ui.input(value=ws.get('path', '/')).classes('flex-1 min-w-0').props('dense outlined dark')
                        w_path.on_value_change(lambda e: ws.update({'path': e.value or '/'}))
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('请求头 Host：')
                        w_host = ui.input(value=ws.get('headers', {}).get('Host', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        w_host.on_value_change(lambda e: ws.setdefault('headers', {}).update({'Host': e.value}))
            elif net_val == 'grpc':
                grpc = self.stream.setdefault('grpcSettings', {})
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('serviceName：')
                        g_svc = ui.input(value=grpc.get('serviceName', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        g_svc.on_value_change(lambda e: grpc.update({'serviceName': e.value}))
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('multiMode：')
                        g_mul = ui.switch(value=bool(grpc.get('multiMode', False)))
                        g_mul.on_value_change(lambda e: grpc.update({'multiMode': bool(e.value)}))
            elif net_val == 'xhttp' and self.is_3x_ui:
                xh = self.stream.setdefault('xhttpSettings', {})
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/3 items-center no-wrap gap-2'):
                        self._make_label('Mode：')
                        mode_opts = ['auto', 'h2', 'h3']
                        m_sel = ui.select(mode_opts, value=xh.get('mode', 'auto')).classes('flex-1 min-w-0').props('dense outlined dark options-dense')
                        m_sel.on_value_change(lambda e: xh.update({'mode': e.value}))
                    with ui.row().classes('w-1/3 items-center no-wrap gap-2'):
                        self._make_label('Path：')
                        xp = ui.input(value=xh.get('path', '/')).classes('flex-1 min-w-0').props('dense outlined dark')
                        xp.on_value_change(lambda e: xh.update({'path': e.value or '/'}))
                    with ui.row().classes('w-1/3 items-center no-wrap gap-2'):
                        self._make_label('Host：')
                        xhst = ui.input(value=xh.get('host', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        xhst.on_value_change(lambda e: xh.update({'host': e.value}))

        # 4. TLS/底层安全 配置
        sec_val = self.stream.get('security', 'none')
        with ui.row().classes('w-full gap-4 items-center no-wrap mt-2'):
            with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                self._make_label('底层安全：')
                sec_opts = ['none', 'tls']
                if self.is_3x_ui:
                    sec_opts.append('reality') # 3x-ui 王牌特性
                
                sec_sel = ui.select(sec_opts, value=sec_val).classes('flex-1 min-w-0').props('dense outlined dark options-dense')
                def on_sec_change(e):
                    self.stream['security'] = e.value
                    self.render_dynamic_settings.refresh()
                sec_sel.on_value_change(on_sec_change)

        if sec_val == 'tls':
            tls = self.stream.setdefault('tlsSettings', {})
            certs = tls.get('certificates', []) if isinstance(tls.get('certificates', []), list) else []
            cert0 = certs[0] if certs else {}
            with ui.column().classes('w-full gap-5'):
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('域名：')
                        sni_inp = ui.input(value=tls.get('serverName', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        sni_inp.on_value_change(lambda e: tls.update({'serverName': e.value}))
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('ALPN：')
                        alpn_inp = ui.input(value=self._list_to_csv(tls.get('alpn', []))).classes('flex-1 min-w-0').props('dense outlined dark')
                        alpn_inp.on_value_change(lambda e: tls.update({'alpn': self._csv_to_list(e.value)}))
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('公钥文件路径：')
                        pub_inp = ui.input(value=cert0.get('certificateFile', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        def update_pub(e):
                            if not certs: certs.append({})
                            certs[0]['certificateFile'] = e.value
                            tls['certificates'] = certs
                        pub_inp.on_value_change(update_pub)
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('密钥文件路径：')
                        key_inp = ui.input(value=cert0.get('keyFile', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        def update_key(e):
                            if not certs: certs.append({})
                            certs[0]['keyFile'] = e.value
                            tls['certificates'] = certs
                        key_inp.on_value_change(update_key)
        
        elif sec_val == 'reality':
            rea = self.stream.setdefault('realitySettings', {})
            with ui.column().classes('w-full gap-5'):
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('目标网站 (SNI)：')
                        sni_inp = ui.input(value=rea.get('serverName', 'www.microsoft.com')).classes('flex-1 min-w-0').props('dense outlined dark')
                        sni_inp.on_value_change(lambda e: rea.update({'serverName': e.value}))
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('Short ID：')
                        sid_inp = ui.input(value=rea.get('shortId', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        sid_inp.on_value_change(lambda e: rea.update({'shortId': e.value}))
                        ui.button(icon='casino', on_click=lambda inp=sid_inp: inp.set_value(uuid.uuid4().hex[:8])).props('flat dense padding=xs color=primary')
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('公钥 (pbk)：')
                        pbk_inp = ui.input(value=rea.get('publicKey', '')).classes('flex-1 min-w-0').props('dense outlined dark')
                        pbk_inp.on_value_change(lambda e: rea.update({'publicKey': e.value}))
                    with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                        self._make_label('私钥 (面板内部)：')
                        prv_inp = ui.input(value=rea.get('privateKey', '')).classes('flex-1 min-w-0').props('dense outlined dark type=password')
                        prv_inp.on_value_change(lambda e: rea.update({'privateKey': e.value}))

        # 5. 嗅探配置 (Sniffing) - 防断流机制
        is_sniff = bool(self.sniffing.get('enabled', not self.is_3x_ui))
        with ui.column().classes('w-full gap-5 mt-2'):
            with ui.row().classes('w-full gap-4 items-center no-wrap'):
                with ui.row().classes('w-1/2 items-center no-wrap gap-2'):
                    self._make_label('sniffing：', '流量嗅探。部分客户端开启可能导致断流。')
                    snf_sw = ui.switch(value=is_sniff)
                    def on_snf_change(e):
                        self.sniffing['enabled'] = bool(e.value)
                        self.render_dynamic_settings.refresh()
                    snf_sw.on_value_change(on_snf_change)

            if is_sniff:
                with ui.row().classes('w-full gap-4 items-center no-wrap'):
                    with ui.row().classes('w-full items-center no-wrap gap-2'):
                        self._make_label('destOverride：')
                        dest_inp = ui.input(value=self._list_to_csv(self.sniffing.get('destOverride', ['http', 'tls']))).classes('flex-1 min-w-0').props('dense outlined dark')
                        dest_inp.on_value_change(lambda e: self.sniffing.update({'destOverride': self._csv_to_list(e.value)}))


    def _build_stream_settings(self):
        # State is automatically managed in self.stream directly by the on_value_change callbacks
        return self.stream

    def _build_settings(self):
        protocol = self.d.get('protocol', 'vmess')
        if protocol in ['vmess', 'vless']:
            settings = {
                'clients': self.settings.get('clients', []),
                'disableInsecureEncryption': bool(self.settings.get('disableInsecureEncryption', False)),
            }
            if protocol == 'vless':
                settings['decryption'] = self.settings.get('decryption', 'none')
            return settings
        if protocol == 'trojan':
            return {'clients': self.settings.get('clients', [])}
        if protocol == 'shadowsocks':
            return {
                'method': self.settings.get('method', 'aes-256-gcm'),
                'password': self.settings.get('password', ''),
                'network': self.settings.get('network', 'tcp,udp'),
            }
        if protocol == 'dokodemo-door':
            return {
                'address': self.settings.get('address', '1.1.1.1'),
                'port': int(self.settings.get('port', 53)),
                'network': self.settings.get('network', 'tcp,udp'),
            }
        if protocol == 'socks':
            return {
                'auth': self.settings.get('auth', 'password'),
                'accounts': self.settings.get('accounts', []),
                'udp': bool(self.settings.get('udp', False)),
            }
        if protocol == 'http':
            return {
                'accounts': self.settings.get('accounts', [])
            }
        return self.settings

    async def save(self, dlg):
        self.d['remark'] = self.rem.value
        self.d['enable'] = self.ena.value
        try:
            port_val = int(self.prt.value)
            if port_val <= 0 or port_val > 65535:
                raise ValueError
            self.d['port'] = port_val
        except:
            safe_notify('请输入有效端口', 'negative')
            return

        try:
            self.d['settings'] = self._build_settings()
            self.d['streamSettings'] = self._build_stream_settings()
            self.d['total'] = self._gb_to_bytes(self.total_gb.value)
            self.d['totalGB'] = round(self.d['total'] / (1024 ** 3), 2) if self.d['total'] > 0 else 0
            self.d['expiryTime'] = self._input_to_expiry(self.expiry_time.value)
            self.d['expiry_time'] = self.d['expiryTime']
            self.d['listen'] = (self.listen_input.value or '').strip()
            self.d['tag'] = self.d.get('tag', '')

            success, msg = False, ''
            is_ssh_manager = hasattr(self.mgr, '_exec_remote_script')
            api_payload = self.d.copy()
            if not is_ssh_manager:
                for k in ['settings', 'streamSettings', 'sniffing']:
                    if isinstance(api_payload.get(k), dict):
                        api_payload[k] = json.dumps(api_payload[k], ensure_ascii=False)

            if is_ssh_manager:
                if self.is_edit:
                    success, msg = await self.mgr.update_inbound(self.d['id'], self.d)
                else:
                    success, msg = await self.mgr.add_inbound(self.d)
            else:
                if self.is_edit:
                    success, msg = await run.io_bound(self.mgr.update_inbound, api_payload['id'], api_payload)
                else:
                    success, msg = await run.io_bound(self.mgr.add_inbound, api_payload)

            if success:
                safe_notify(f'✅ {msg}', 'positive')
                dlg.close()
                if self.cb:
                    res = self.cb()
                    if asyncio.iscoroutine(res):
                        await res
            else:
                safe_notify(f'❌ 失败: {msg}', 'negative', timeout=5000)
        except Exception as e:
            safe_notify(f'❌ 系统异常: {str(e)}', 'negative', timeout=6000)


async def open_inbound_dialog(mgr, data, cb, is_3x_ui=False):
    # 接收并传递 is_3x_ui 状态
    with ui.dialog() as d:
        InboundEditor(mgr, data, cb, is_3x_ui).build_ui(d)
    d.open()


async def delete_inbound(mgr, id, cb):
    try:
        success, msg = False, ''
        is_ssh_manager = hasattr(mgr, '_exec_remote_script')

        if is_ssh_manager:
            success, msg = await mgr.delete_inbound(id)
        else:
            success, msg = await run.io_bound(mgr.delete_inbound, id)

        if success:
            safe_notify(f'✅ {msg}', 'positive')
            if cb:
                res = cb()
                if asyncio.iscoroutine(res):
                    await res
        else:
            safe_notify(f'❌ 删除失败: {msg}', 'negative')
    except Exception as e:
        safe_notify(f'❌ 系统异常: {str(e)}', 'negative')


async def delete_inbound_with_confirm(mgr, inbound_id, inbound_remark, callback):
    with ui.dialog() as d, ui.card().classes('bg-[#1e293b] border border-slate-700'):
        ui.label('删除确认').classes('text-lg font-bold text-red-500')
        ui.label(f'您确定要永久删除节点 [{inbound_remark}] 吗？').classes('text-base text-slate-200 mt-2')
        ui.label('此操作不可恢复。').classes('text-xs text-slate-400 mb-4')

        with ui.row().classes('w-full justify-end gap-3 mt-2'):
            ui.button('取消', on_click=d.close).props('outline color=grey').classes('text-slate-300')

            async def do_delete():
                d.close()
                await delete_inbound(mgr, inbound_id, callback)

            ui.button('确定删除', color='red', on_click=do_delete).props('unelevated font-bold')
    d.open()
