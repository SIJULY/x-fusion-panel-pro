import base64
import json
from urllib.parse import quote


def parse_vless_link_to_node(link, remark_override=None):
    """将 vless:// 链接解析为面板节点格式的字典"""
    try:
        if not link.startswith("vless://"):
            return None

        import urllib.parse

        main_part = link.replace("vless://", "")

        remark = "XHTTP-Reality"
        if "#" in main_part:
            main_part, remark = main_part.split("#", 1)
            remark = urllib.parse.unquote(remark)

        if remark_override:
            remark = remark_override

        params = {}
        if "?" in main_part:
            main_part, query_str = main_part.split("?", 1)
            params = dict(urllib.parse.parse_qsl(query_str))

        if "@" in main_part:
            user_info, host_port = main_part.split("@", 1)
            uuid = user_info
        else:
            return None

        if ":" in host_port:
            host, port = host_port.rsplit(":", 1)
        else:
            host = host_port
            port = 443

        final_link = link
        if remark_override:
            if "#" in final_link:
                final_link = final_link.split("#")[0]
            final_link = f"{final_link}#{urllib.parse.quote(remark)}"

        node = {
            "id": uuid,
            "remark": remark,
            "port": int(port),
            "protocol": "vless",
            "settings": {
                "clients": [{"id": uuid, "flow": params.get("flow", "")}],
                "decryption": "none",
            },
            "streamSettings": {
                "network": params.get("type", "tcp"),
                "security": params.get("security", "none"),
                "xhttpSettings": {
                    "path": params.get("path", ""),
                    "mode": params.get("mode", "auto"),
                    "host": params.get("host", ""),
                },
                "realitySettings": {
                    "serverName": params.get("sni", ""),
                    "shortId": params.get("sid", ""),
                    "publicKey": params.get("pbk", ""),
                },
            },
            "enable": True,
            "_is_custom": True,
            "_raw_link": final_link,
        }
        return node

    except Exception as e:
        print(f"[Error] 解析 VLESS 链接失败: {e}")
        return None


def safe_base64(s):
    return base64.urlsafe_b64encode(s.encode('utf-8')).decode('utf-8')


def decode_base64_safe(s):
    try:
        missing_padding = len(s) % 4
        if missing_padding:
            s += '=' * (4 - missing_padding)
        return base64.urlsafe_b64decode(s).decode('utf-8')
    except:
        try:
            return base64.b64decode(s).decode('utf-8')
        except:
            return ""


def generate_converted_link(raw_link, target, domain_prefix):
    """
    生成经过 SubConverter 转换的订阅链接
    target: surge, clash
    """
    if not raw_link or not domain_prefix:
        return ""

    converter_base = f"{domain_prefix}/convert"
    encoded_url = quote(raw_link)

    params = f"target={target}&url={encoded_url}&insert=false&list=true&ver=4&udp=true&scv=true"

    return f"{converter_base}?{params}"


def generate_node_link(node, server_host):
    try:
        clean_host = server_host
        if '://' in clean_host:
            clean_host = clean_host.split('://')[-1]
        if ':' in clean_host and not clean_host.startswith('['):
            clean_host = clean_host.split(':')[0]

        p = node['protocol']
        remark = node['remark']
        port = node['port']
        add = node.get('listen') or clean_host

        s = json.loads(node['settings']) if isinstance(node['settings'], str) else node['settings']
        st = json.loads(node['streamSettings']) if isinstance(node['streamSettings'], str) else node['streamSettings']
        net = st.get('network', 'tcp')
        tls = st.get('security', 'none')
        path = ""
        host = ""

        if net == 'ws':
            path = st.get('wsSettings', {}).get('path', '/')
            host = st.get('wsSettings', {}).get('headers', {}).get('Host', '')
        elif net == 'grpc':
            path = st.get('grpcSettings', {}).get('serviceName', '')

        if p == 'vmess':
            v = {
                "v": "2",
                "ps": remark,
                "add": add,
                "port": port,
                "id": s['clients'][0]['id'],
                "aid": "0",
                "scy": "auto",
                "net": net,
                "type": "none",
                "host": host,
                "path": path,
                "tls": tls,
            }
            return "vmess://" + safe_base64(json.dumps(v))

        elif p == 'vless':
            params = f"type={net}&security={tls}"
            if path:
                params += f"&path={path}" if net != 'grpc' else f"&serviceName={path}"
            if host:
                params += f"&host={host}"
            return f"vless://{s['clients'][0]['id']}@{add}:{port}?{params}#{remark}"

        elif p == 'trojan':
            return f"trojan://{s['clients'][0]['password']}@{add}:{port}?type={net}&security={tls}#{remark}"

        elif p == 'shadowsocks':
            cred = f"{s['method']}:{s['password']}"
            return f"ss://{safe_base64(cred)}@{add}:{port}#{remark}"

    except Exception:
        return ""
    return ""


def generate_detail_config(node, server_host):
    try:
        clean_host = server_host.replace('http://', '').replace('https://', '')
        if ':' in clean_host and not clean_host.startswith('['):
            clean_host = clean_host.split(':')[0]

        remark = node.get('remark', 'Unnamed').replace(',', '_').replace('=', '_').strip()
        address = node.get('listen') or clean_host
        port = node['port']

        if node.get('_is_custom'):
            raw_link = node.get('_raw_link', '')

            if raw_link.startswith('snell://'):
                from urllib.parse import parse_qs, urlparse

                parsed = urlparse(raw_link)
                psk = parsed.username
                s_host = parsed.hostname or address
                s_port = parsed.port or port

                params = parse_qs(parsed.query)
                version = params.get('version', ['4'])[0]

                return f"{remark} = snell, {s_host}, {s_port}, psk={psk}, version={version}, tfo=true, reuse=true"

            elif raw_link.startswith('hy2://'):
                from urllib.parse import parse_qs, urlparse

                parsed = urlparse(raw_link)
                password = parsed.username
                h_host = parsed.hostname or address

                if str(port) and '-' in str(port):
                    h_port = port
                else:
                    h_port = parsed.port or port

                params = parse_qs(parsed.query)
                sni = params.get('sni', [''])[0] or params.get('peer', [''])[0]

                line = f"{remark} = hysteria2, {h_host}, {h_port}, password={password}"
                if sni:
                    line += f", sni={sni}"
                line += ", skip-cert-verify=true, download-bandwidth=500, udp-relay=true"
                return line

            elif raw_link.startswith('vless://'):
                return f"// Surge 暂未原生支持 XHTTP: {remark}"

        protocol = node['protocol']
        settings = json.loads(node['settings']) if isinstance(node['settings'], str) else node['settings']
        stream = json.loads(node['streamSettings']) if isinstance(node['streamSettings'], str) else node['streamSettings']
        net = stream.get('network', 'tcp')
        security = stream.get('security', 'none')
        tls = (security == 'tls') or (security == 'reality')

        if protocol == 'vmess':
            uuid = settings['clients'][0]['id']
            line = f"{remark} = vmess, {address}, {port}, username={uuid}"
            if net == 'ws':
                ws_set = stream.get('wsSettings', {})
                path = ws_set.get('path', '/')
                panel_host = ws_set.get('headers', {}).get('Host', '')
                sni = ""
                if tls:
                    tls_set = stream.get('tlsSettings', {})
                    sni = tls_set.get('serverName', '')
                line += f", ws=true, ws-path={path}"
                if tls and sni:
                    pass
                elif panel_host:
                    line += f", ws-headers=Host:{panel_host}"
            if tls:
                line += ", tls=true"
                tls_set = stream.get('tlsSettings', {})
                sni = tls_set.get('serverName', '')
                if sni:
                    line += f", sni={sni}"
                line += ", skip-cert-verify=true"
            line += ", tfo=true, udp-relay=true"
            return line

        elif protocol == 'trojan':
            password = settings['clients'][0]['password']
            line = f"{remark} = trojan, {address}, {port}, password={password}"
            if tls:
                line += ", tls=true"
                sni = stream.get('tlsSettings', {}).get('serverName', '')
                if sni:
                    line += f", sni={sni}"
                line += ", skip-cert-verify=true"
            line += ", tfo=true, udp-relay=true"
            return line

    except Exception as e:
        return f"// Config Error: {str(e)}"

    return ""
