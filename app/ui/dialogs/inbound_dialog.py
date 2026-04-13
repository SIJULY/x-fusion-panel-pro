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
            return datetime.fromtimestamp(expiry_time / 1000).strftime('%Y-%m-%dT%H:%M')
        except:
            return ''

    @staticmethod
    def _input_to_expiry(value):
        if not value:
            return 0
        try:
            dt = datetime.strptime(value, '%Y-%m-%dT%H:%M')
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

    def __init__(self, mgr, data=None, on_success=None):
        self.mgr = mgr
        self.cb = on_success
        self.is_edit = data is not None
        self.auth_box = None
        self.auth_title_label = None
        self.stream_box = None
        self.sniffing_dest_box = None
        self.sniffing_dest = None
        self.ss_network_input = None

        if not data:
            random_port = random.randint(10000, 65000)
            self.d = {
                'enable': True,
                'remark': '',
                'port': random_port,
                'protocol': 'vmess',
                'settings': {
                    'clients': [{'id': str(uuid.uuid4()), 'alterId': 0, 'email': '', 'flow': ''}],
                    'disableInsecureEncryption': False,
                    'decryption': 'none',
                },
                'streamSettings': {'network': 'tcp', 'security': 'none'},
                'sniffing': {'enabled': True, 'destOverride': ['http', 'tls']},
                'total': 0,
                'expiryTime': 0,
                'tag': '',
                'listen': '',
            }
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
        self.stream.setdefault('sockopt', {'acceptProxyProtocol': False})
        self.stream.setdefault('tcpSettings', {
            'header': {'type': 'none', 'request': {'path': ['/'], 'headers': {'Host': []}}}
        })
        self.stream.setdefault('wsSettings', {
            'path': '/',
            'headers': {'Host': ''},
            'maxEarlyData': 0,
            'earlyDataHeaderName': 'Sec-WebSocket-Protocol',
        })
        self.stream.setdefault('grpcSettings', {'serviceName': '', 'multiMode': False, 'authority': ''})
        self.stream.setdefault('httpupgradeSettings', {'path': '/', 'host': ''})
        self.stream.setdefault('xhttpSettings', {'path': '/', 'host': '', 'mode': 'auto'})
        self.stream.setdefault('tlsSettings', {
            'serverName': '',
            'alpn': [],
            'allowInsecure': False,
            'certificates': [],
        })
        self.stream.setdefault('realitySettings', {
            'serverName': '',
            'publicKey': '',
            'privateKey': '',
            'shortId': '',
            'spiderX': '/',
            'fingerprint': 'chrome',
            'show': False,
        })

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
                client.setdefault('email', '')
                client.setdefault('flow', '')
            self.settings['clients'] = clients
            self.settings.setdefault('disableInsecureEncryption', False)
            self.settings.setdefault('decryption', 'none')
        elif protocol == 'trojan':
            clients = self._to_list(self.settings.get('clients'))
            if not clients:
                clients = [{'password': uuid.uuid4().hex[:8], 'email': '', 'flow': ''}]
            for client in clients:
                client.setdefault('password', uuid.uuid4().hex[:8])
                client.setdefault('email', '')
                client.setdefault('flow', '')
            self.settings['clients'] = clients
        elif protocol == 'shadowsocks':
            self.settings.setdefault('method', 'aes-256-gcm')
            self.settings.setdefault('password', uuid.uuid4().hex[:10])
            self.settings.setdefault('network', 'tcp,udp')
        elif protocol == 'socks':
            self.settings.setdefault('auth', 'password')
            self.settings.setdefault('udp', False)
            accounts = self._to_list(self.settings.get('accounts'))
            if not accounts:
                accounts = [{'user': 'admin', 'pass': 'admin'}]
            for account in accounts:
                account.setdefault('user', 'admin')
                account.setdefault('pass', 'admin')
            self.settings['accounts'] = accounts

    def _get_auth_title(self):
        protocol = self.d.get('protocol', 'vmess')
        if protocol in ['vmess', 'vless']:
            return '用户'
        if protocol == 'trojan':
            return '密码'
        if protocol == 'shadowsocks':
            return '加密与密码'
        if protocol == 'socks':
            return '认证与账户'
        return '用户'

    def ui(self, dlg):
        with ui.card().classes('w-full max-w-5xl p-6 flex flex-col gap-4 overflow-auto'):
            title = '编辑节点' if self.is_edit else '新建节点'
            
            # --- 关键修改位置：调整标题、开关与关闭按钮的层级布局 ---
            with ui.row().classes('w-full justify-between items-center mb-2'):
                # 左侧：标题 + 启用开关
                with ui.row().classes('items-center gap-4'):
                    ui.label(title).classes('text-xl font-bold')
                    self.ena = ui.switch('启用', value=self.d.get('enable', True))
                # 右侧：独立的关闭按钮（自动靠到右上角）
                ui.button(icon='close', on_click=dlg.close).props('flat round dense color=grey')

            with ui.row().classes('w-full gap-4'):
                self.rem = ui.input('节点名称', value=self.d.get('remark')).classes('flex-grow')

            with ui.row().classes('w-full gap-4 items-end'):
                self.pro = ui.select(['vmess', 'vless', 'trojan', 'shadowsocks', 'socks'], value=self.d['protocol'], label='协议', on_change=self.on_protocol_change).classes('w-1/4')
                self.prt = ui.number('端口', value=self.d['port'], format='%.0f').classes('w-1/4')
                ui.button(icon='shuffle', on_click=lambda: self.prt.set_value(int(run.io_bound(lambda: __import__('random').randint(10000, 60000))))).props('flat dense').tooltip('随机端口')

            with ui.row().classes('w-full no-wrap items-end gap-4'):
                self.total_gb = ui.number('总流量(GB)', value=self._bytes_to_gb(self.d.get('total')), format='%.2f').classes('flex-1 min-w-0').props('clearable')
                self.expiry_time = ui.input('到期时间', value=self._expiry_to_input(self.d.get('expiryTime')), placeholder='留空为不限').props('type=datetime-local').classes('flex-1 min-w-0')

            self.auth_title_label = ui.label(self._get_auth_title()).classes('text-sm font-medium text-gray-600')
            self.auth_box = ui.column().classes('w-full gap-3')
            self.refresh_auth_ui()

            with ui.expansion('传输设置', icon='lan', value=True).classes('w-full'):
                with ui.column().classes('w-full gap-3 pt-3'):
                    with ui.row().classes('w-full gap-4 items-end'):
                        self.net = ui.select(['tcp', 'ws', 'grpc'], value=self.stream.get('network', 'tcp'), label='传输协议', on_change=self.on_stream_change).classes('w-1/3')
                        self.sec = ui.select(['none', 'tls', 'reality'], value=self.stream.get('security', 'none'), label='安全', on_change=self.on_stream_change).classes('w-1/3')
                    self.stream_box = ui.column().classes('w-full gap-3')
                    self.refresh_stream_ui()

            with ui.expansion('更多设置', icon='tune', value=False).classes('w-full'):
                with ui.column().classes('w-full gap-3 pt-3'):
                    with ui.row().classes('w-full gap-4'):
                        self.listen_input = ui.input('监听地址', value=self.d.get('listen', ''), placeholder='留空=全部监听').classes('w-1/3')
                        self.tag_input = ui.input('Tag', value=self.d.get('tag', ''), placeholder='可选').classes('w-1/3')
                        self.sniffing_enabled = ui.switch('启用嗅探', value=bool(self.sniffing.get('enabled', True)), on_change=self.on_sniffing_change).classes('mt-2')
                    if self.pro.value == 'shadowsocks':
                        self.ss_network_input = ui.input('网络', value=self.settings.get('network', 'tcp,udp'), placeholder='如: tcp,udp').classes('w-1/3')
                    self.sniffing_dest_box = ui.column().classes('w-full')
                    self.refresh_sniffing_ui()

            ui.label('高级配置默认关闭，按需展开即可。').classes('text-xs text-gray-500')

            with ui.row().classes('w-full justify-end mt-4'):
                ui.button('保存', on_click=lambda: self.save(dlg)).props('color=primary')

    def on_protocol_change(self, e):
        self.d['protocol'] = e.value
        self._normalize_protocol_settings()
        if self.auth_title_label:
            self.auth_title_label.set_text(self._get_auth_title())
        self.refresh_auth_ui()

    def on_stream_change(self, _=None):
        self.refresh_stream_ui()

    def on_sniffing_change(self, _=None):
        self.refresh_sniffing_ui()

    def refresh_auth_ui(self):
        if not self.auth_box:
            return
        self.auth_box.clear()
        self._normalize_protocol_settings()
        protocol = self.d.get('protocol', 'vmess')

        with self.auth_box:
            if protocol in ['vmess', 'vless']:
                client = self.settings.get('clients', [{}])[0]
                self.settings['clients'] = [client]
                with ui.row().classes('w-full gap-3 items-end'):
                    id_input = ui.input('UUID', value=client.get('id', '')).classes('flex-1')
                    id_input.on_value_change(lambda e, c=client: c.update({'id': e.value}))
                    ui.button(icon='casino', on_click=lambda inp=id_input: inp.set_value(str(uuid.uuid4()))).props('flat dense').tooltip('生成 UUID')
            elif protocol == 'trojan':
                client = self.settings.get('clients', [{}])[0]
                self.settings['clients'] = [client]
                with ui.row().classes('w-full gap-3 items-end'):
                    pwd_input = ui.input('密码', value=client.get('password', '')).classes('flex-1')
                    pwd_input.on_value_change(lambda e, c=client: c.update({'password': e.value}))
                    ui.button(icon='casino', on_click=lambda inp=pwd_input: inp.set_value(uuid.uuid4().hex[:8])).props('flat dense').tooltip('生成密码')
            elif protocol == 'shadowsocks':
                with ui.row().classes('w-full gap-4'):
                    ui.select(['aes-256-gcm', 'chacha20-ietf-poly1305', 'aes-128-gcm'], value=self.settings.get('method', 'aes-256-gcm'), label='加密').classes('w-1/2').on_value_change(lambda e: self.settings.update({'method': e.value}))
                    ui.input('密码', value=self.settings.get('password', '')).classes('w-1/2').on_value_change(lambda e: self.settings.update({'password': e.value}))
            elif protocol == 'socks':
                accounts = self.settings.get('accounts', [{}])
                account = accounts[0] if accounts else {'user': 'admin', 'pass': 'admin'}
                self.settings['accounts'] = [account]
                with ui.row().classes('w-full gap-4'):
                    ui.select(['noauth', 'password'], value=self.settings.get('auth', 'password'), label='认证方式').classes('w-1/4').on_value_change(lambda e: self.settings.update({'auth': e.value}))
                    ui.switch('UDP', value=bool(self.settings.get('udp', False))).classes('mt-2').on_value_change(lambda e: self.settings.update({'udp': bool(e.value)}))
                if self.settings.get('auth', 'password') != 'noauth':
                    with ui.row().classes('w-full gap-3 items-end'):
                        ui.input('ID', value=account.get('user', '')).classes('w-1/2').on_value_change(lambda e, a=account: a.update({'user': e.value}))
                        ui.input('密码', value=account.get('pass', '')).classes('w-1/2').on_value_change(lambda e, a=account: a.update({'pass': e.value}))

    def refresh_stream_ui(self):
        if not self.stream_box:
            return
        self.stream_box.clear()
        net = self.net.value if hasattr(self, 'net') else self.stream.get('network', 'tcp')
        sec = self.sec.value if hasattr(self, 'sec') else self.stream.get('security', 'none')

        tcp = self.stream.setdefault('tcpSettings', {'header': {'type': 'none', 'request': {'path': ['/'], 'headers': {'Host': []}}}})
        tcp_header = tcp.setdefault('header', {'type': 'none', 'request': {'path': ['/'], 'headers': {'Host': []}}})
        tcp_request = tcp_header.setdefault('request', {'path': ['/'], 'headers': {'Host': []}})
        tcp_headers = tcp_request.setdefault('headers', {'Host': []})

        ws = self.stream.setdefault('wsSettings', {'path': '/', 'headers': {'Host': ''}, 'maxEarlyData': 0, 'earlyDataHeaderName': 'Sec-WebSocket-Protocol'})
        ws.setdefault('headers', {})
        grpc = self.stream.setdefault('grpcSettings', {'serviceName': '', 'multiMode': False, 'authority': ''})
        tls = self.stream.setdefault('tlsSettings', {'serverName': '', 'alpn': [], 'allowInsecure': False, 'certificates': []})
        reality = self.stream.setdefault('realitySettings', {'serverName': '', 'publicKey': '', 'privateKey': '', 'shortId': '', 'spiderX': '/', 'fingerprint': 'chrome', 'show': False})

        with self.stream_box:
            if net == 'tcp':
                with ui.row().classes('w-full gap-4'):
                    ui.select(['none', 'http'], value=tcp_header.get('type', 'none'), label='TCP 伪装').classes('w-1/3').on_value_change(lambda e: (tcp_header.update({'type': e.value}), self.refresh_stream_ui()))
                    if tcp_header.get('type', 'none') == 'http':
                        ui.input('HTTP Path', value=self._list_to_csv(tcp_request.get('path', ['/']))).classes('w-1/3').on_value_change(lambda e: tcp_request.update({'path': self._csv_to_list(e.value) or ['/']}))
                        ui.input('HTTP Host', value=self._list_to_csv(tcp_headers.get('Host', []))).classes('w-1/3').on_value_change(lambda e: tcp_headers.update({'Host': self._csv_to_list(e.value)}))
            elif net == 'ws':
                with ui.row().classes('w-full gap-4'):
                    ui.input('WS Path', value=ws.get('path', '/')).classes('w-1/3').on_value_change(lambda e: ws.update({'path': e.value or '/'}))
                    ui.input('WS Host', value=ws.get('headers', {}).get('Host', '')).classes('w-1/3').on_value_change(lambda e: ws['headers'].update({'Host': e.value}))
                    ui.number('EarlyData', value=int(ws.get('maxEarlyData', 0) or 0), format='%.0f').classes('w-1/3').on_value_change(lambda e: ws.update({'maxEarlyData': int(e.value or 0)}))
                ui.input('EarlyData Header', value=ws.get('earlyDataHeaderName', 'Sec-WebSocket-Protocol')).classes('w-full').on_value_change(lambda e: ws.update({'earlyDataHeaderName': e.value or 'Sec-WebSocket-Protocol'}))
            elif net == 'grpc':
                with ui.row().classes('w-full gap-4'):
                    ui.input('gRPC Service Name', value=grpc.get('serviceName', '')).classes('w-1/3').on_value_change(lambda e: grpc.update({'serviceName': e.value}))
                    ui.input('Authority', value=grpc.get('authority', '')).classes('w-1/3').on_value_change(lambda e: grpc.update({'authority': e.value}))
                    ui.switch('MultiMode', value=bool(grpc.get('multiMode', False))).classes('mt-2').on_value_change(lambda e: grpc.update({'multiMode': bool(e.value)}))
            if sec in ['tls', 'reality']:
                certs = tls.get('certificates', []) if isinstance(tls.get('certificates', []), list) else []
                cert0 = certs[0] if certs else {}
                with ui.row().classes('w-full gap-4'):
                    sni_default = tls.get('serverName', '') if sec == 'tls' else reality.get('serverName', '')
                    self.sni_input = ui.input('伪装域名 / SNI', value=sni_default, placeholder='如: www.example.com').classes('w-1/3')
                    self.alpn_input = ui.input('ALPN', value=self._list_to_csv(tls.get('alpn', [])), placeholder='如: h2,http/1.1').classes('w-1/3')
                    self.allow_insecure = ui.switch('跳过证书校验', value=bool(tls.get('allowInsecure', False))).classes('mt-2')
                if sec == 'tls':
                    ui.label('仅当你启用 TLS 时，才需要填写下面这些证书相关参数。').classes('text-xs text-gray-500')
                with ui.row().classes('w-full gap-4'):
                    self.cert_file_input = ui.input('证书路径 certFile', value=cert0.get('certificateFile', ''), placeholder='/root/fullchain.pem').classes('w-1/2')
                    self.key_file_input = ui.input('私钥路径 keyFile', value=cert0.get('keyFile', ''), placeholder='/root/privkey.pem').classes('w-1/2')

            if sec == 'reality':
                with ui.row().classes('w-full gap-4'):
                    self.public_key_input = ui.input('公钥 publicKey', value=reality.get('publicKey', '')).classes('w-1/3')
                    self.private_key_input = ui.input('私钥 privateKey', value=reality.get('privateKey', '')).classes('w-1/3')
                    self.short_id_input = ui.input('Short ID', value=reality.get('shortId', '')).classes('w-1/3')
                with ui.row().classes('w-full gap-4'):
                    self.spider_x_input = ui.input('SpiderX', value=reality.get('spiderX', '/')).classes('w-1/3')
                    self.fp_input = ui.select(['chrome', 'firefox', 'safari', 'ios', 'android', 'random'], value=reality.get('fingerprint', 'chrome'), label='Fingerprint').classes('w-1/3')
                    self.show_input = ui.switch('show', value=bool(reality.get('show', False))).classes('mt-2')

    def refresh_sniffing_ui(self):
        if not self.sniffing_dest_box:
            return
        self.sniffing_dest_box.clear()
        with self.sniffing_dest_box:
            if bool(self.sniffing_enabled.value) if hasattr(self, 'sniffing_enabled') else bool(self.sniffing.get('enabled', True)):
                self.sniffing_dest = ui.input('Sniffing DestOverride', value=self._list_to_csv(self.sniffing.get('destOverride', ['http', 'tls'])), placeholder='例如: http,tls,quic').classes('w-full')
            else:
                ui.label('嗅探已关闭；如需自定义 http / tls / quic，再打开后填写。').classes('text-xs text-gray-500')

    def _build_stream_settings(self):
        network = self.net.value
        security = self.sec.value
        stream = {'network': network, 'security': security}
        stream['sockopt'] = {'acceptProxyProtocol': False}

        if network == 'tcp':
            header_type = self.stream.get('tcpSettings', {}).get('header', {}).get('type', 'none')
            stream['tcpSettings'] = self.stream.get('tcpSettings', {}) if header_type == 'http' else {'header': {'type': 'none'}}
        elif network == 'ws':
            stream['wsSettings'] = self.stream.get('wsSettings', {})
        elif network == 'grpc':
            stream['grpcSettings'] = self.stream.get('grpcSettings', {})

        if security in ['tls', 'reality']:
            certs = []
            cert_file = self.cert_file_input.value.strip() if hasattr(self, 'cert_file_input') and self.cert_file_input.value else ''
            key_file = self.key_file_input.value.strip() if hasattr(self, 'key_file_input') and self.key_file_input.value else ''
            if cert_file or key_file:
                certs.append({'certificateFile': cert_file, 'keyFile': key_file})
            stream['tlsSettings'] = {
                'serverName': self.sni_input.value.strip() if hasattr(self, 'sni_input') and self.sni_input.value else '',
                'alpn': self._csv_to_list(self.alpn_input.value if hasattr(self, 'alpn_input') else ''),
                'allowInsecure': bool(self.allow_insecure.value) if hasattr(self, 'allow_insecure') else False,
                'certificates': certs,
            }

        if security == 'reality':
            stream['realitySettings'] = {
                'serverName': self.sni_input.value.strip() if hasattr(self, 'sni_input') and self.sni_input.value else '',
                'publicKey': self.public_key_input.value.strip() if hasattr(self, 'public_key_input') and self.public_key_input.value else '',
                'privateKey': self.private_key_input.value.strip() if hasattr(self, 'private_key_input') and self.private_key_input.value else '',
                'shortId': self.short_id_input.value.strip() if hasattr(self, 'short_id_input') and self.short_id_input.value else '',
                'spiderX': self.spider_x_input.value.strip() if hasattr(self, 'spider_x_input') and self.spider_x_input.value else '/',
                'fingerprint': self.fp_input.value if hasattr(self, 'fp_input') else 'chrome',
                'show': bool(self.show_input.value) if hasattr(self, 'show_input') else False,
            }

        return stream

    def _build_settings(self):
        protocol = self.pro.value
        if protocol in ['vmess', 'vless']:
            self._normalize_protocol_settings()
            settings = {
                'clients': self.settings.get('clients', []),
                'decryption': self.settings.get('decryption', 'none') if protocol == 'vless' else self.settings.get('decryption', 'none'),
                'disableInsecureEncryption': bool(self.settings.get('disableInsecureEncryption', False)),
            }
            if protocol == 'vmess':
                settings.pop('decryption', None)
            return settings
        if protocol == 'trojan':
            return {'clients': self.settings.get('clients', [])}
        if protocol == 'shadowsocks':
            network_value = self.ss_network_input.value if self.ss_network_input else self.settings.get('network', 'tcp,udp')
            self.settings['network'] = network_value
            return {
                'method': self.settings.get('method', 'aes-256-gcm'),
                'password': self.settings.get('password', ''),
                'network': network_value,
            }
        if protocol == 'socks':
            return {
                'auth': self.settings.get('auth', 'password'),
                'accounts': self.settings.get('accounts', []),
                'udp': bool(self.settings.get('udp', False)),
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
            self.d['protocol'] = self.pro.value
            self.d['settings'] = self._build_settings()
            self.d['streamSettings'] = self._build_stream_settings()
            self.d['total'] = self._gb_to_bytes(self.total_gb.value)
            self.d['totalGB'] = round(self.d['total'] / (1024 ** 3), 2) if self.d['total'] > 0 else 0
            self.d['expiryTime'] = self._input_to_expiry(self.expiry_time.value)
            self.d['expiry_time'] = self.d['expiryTime']
            self.d['listen'] = (self.listen_input.value or '').strip()
            self.d['tag'] = (self.tag_input.value or '').strip()
            sniffing_enabled = bool(self.sniffing_enabled.value)
            sniffing_dest_value = self.sniffing_dest.value if sniffing_enabled and self.sniffing_dest else self._list_to_csv(self.sniffing.get('destOverride', ['http', 'tls']))
            self.d['sniffing'] = {
                'enabled': sniffing_enabled,
                'destOverride': self._csv_to_list(sniffing_dest_value) if sniffing_enabled else self._csv_to_list(sniffing_dest_value or 'http,tls'),
            }

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


async def open_inbound_dialog(mgr, data, cb):
    with ui.dialog() as d:
        InboundEditor(mgr, data, cb).ui(d)
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
    with ui.dialog() as d, ui.card():
        ui.label('删除确认').classes('text-lg font-bold text-red-600')
        ui.label(f'您确定要永久删除节点 [{inbound_remark}] 吗？').classes('text-base mt-2')
        ui.label('此操作不可恢复。').classes('text-xs text-gray-400 mb-4')

        with ui.row().classes('w-full justify-end gap-2'):
            ui.button('取消', on_click=d.close).props('flat color=grey')

            async def do_delete():
                d.close()
                await delete_inbound(mgr, inbound_id, callback)

            ui.button('确定删除', color='red', on_click=do_delete)
    d.open()
