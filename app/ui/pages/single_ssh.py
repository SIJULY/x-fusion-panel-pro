import asyncio
import base64
import os
import tempfile
import time as time_module
import uuid

from nicegui import run, ui

from app.core.state import ADMIN_CONFIG
from app.services.ssh import WebSSH, _ssh_exec_wrapper
from app.storage.repositories import save_admin_config
from app.ui.common.notifications import safe_notify
from app.ui.dialogs import server_dialog as _server_dialog


def cleanup_ssh_route_terminal(server_key=None):
    return _server_dialog.cleanup_ssh_route_terminal(server_key=server_key)


async def render_single_ssh_view(server_conf):
    from app.services.sftp import (
        create_empty_remote_file,
        delete_remote_path,
        download_remote_file,
        get_parent_remote_path,
        is_probably_text_file,
        join_remote_path,
        list_remote_dir,
        make_remote_dir,
        normalize_remote_path,
        read_remote_file,
        rename_remote_path,
        upload_remote_file,
        write_remote_file,
    )
    from app.ui.pages.content_router import content_container, refresh_content

    _sync_resolve_ip = _server_dialog._sync_resolve_ip
    SSH_PAGE_TERMINALS = _server_dialog.SSH_PAGE_TERMINALS

    server_key = server_conf.get('url') or server_conf.get('ssh_host') or str(id(server_conf))
    cleanup_ssh_route_terminal(server_key)

    current_client = None
    try:
        current_client = ui.context.client
    except:
        pass

    if content_container:
        content_container.clear()
        content_container.classes(remove='overflow-y-auto block', add='h-full min-h-0 overflow-hidden flex flex-col p-4 gap-4')

    terminal_state = {'instance': None}
    file_state = {'current_path': '/', 'entries': [], 'loading': False}
    tree_state = {'expanded': {'/'}, 'selected': '/', 'cache': {}, 'loading': set()}
    path_input = None

    editor_state = {
        'dialog': None,
        'files': {},
        'active_path': None,
        'refresh_tabs': None,
    }

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

    def format_file_size(size):
        try:
            size = float(size or 0)
            for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
                if size < 1024 or unit == 'TB':
                    return f'{size:.1f} {unit}' if unit != 'B' else f'{int(size)} B'
                size /= 1024
        except:
            return '--'

    def format_mtime(value):
        try:
            if not value:
                return '--'
            return time_module.strftime('%Y-%m-%d %H:%M', time_module.localtime(value))
        except:
            return '--'

    def basename(path):
        if path == '/':
            return '/'
        return path.rstrip('/').split('/')[-1] or '/'

    def exec_quick_cmd(cmd_text):
        if terminal_state['instance'] and terminal_state['instance'].active:
            terminal_state['instance'].channel.send(cmd_text + '\n')
            safe_notify(f'已发送: {cmd_text[:20]}...', 'positive')
        else:
            safe_notify('SSH 正在连接或已断开，请稍后重试', 'warning')

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

    async def ensure_tree_children(path, force=False):
        path = normalize_remote_path(path)
        if not force and path in tree_state['cache']:
            return
        tree_state['loading'].add(path)
        render_tree.refresh()
        try:
            entries = await run.io_bound(list_remote_dir, server_conf, path)
            tree_state['cache'][path] = [e for e in entries if e.get('is_dir')]
        except Exception:
            tree_state['cache'][path] = []
        finally:
            tree_state['loading'].discard(path)
            render_tree.refresh()

    async def refresh_remote_dir(target_path=None):
        nonlocal path_input
        if target_path is not None:
            normalized = normalize_remote_path(target_path)
            file_state['current_path'] = normalized
            tree_state['selected'] = normalized
        file_state['loading'] = True
        render_file_list.refresh()
        try:
            file_state['entries'] = await run.io_bound(list_remote_dir, server_conf, file_state['current_path'])
            await ensure_tree_children(file_state['current_path'], force=True)
            if path_input:
                path_input.value = file_state['current_path']
                path_input.update()
        except Exception as e:
            file_state['entries'] = []
            safe_notify(f'读取目录失败: {e}', 'negative')
        finally:
            file_state['loading'] = False
            render_file_list.refresh()
            render_tree.refresh()

    async def change_dir(target_path):
        target_path = normalize_remote_path(target_path)
        tree_state['expanded'].add(get_parent_remote_path(target_path))
        await refresh_remote_dir(target_path)

    async def go_parent_dir():
        await refresh_remote_dir(get_parent_remote_path(file_state['current_path']))

    async def toggle_tree_node(path):
        path = normalize_remote_path(path)
        if path in tree_state['expanded']:
            tree_state['expanded'].discard(path)
            render_tree.refresh()
            return
        tree_state['expanded'].add(path)
        await ensure_tree_children(path)
        render_tree.refresh()

    async def select_tree_node(path):
        await change_dir(path)

    async def handle_entry_open(entry):
        if entry.get('is_dir'):
            await change_dir(entry.get('path', '/'))
        else:
            await open_file_editor(entry)

    def detect_language(filename):
        ext = os.path.splitext(filename)[1].lower()
        mapping = {
            '.py': 'python', '.js': 'javascript', '.json': 'json',
            '.html': 'html', '.css': 'css', '.sh': 'shell',
            '.yaml': 'yaml', '.yml': 'yaml', '.xml': 'xml',
            '.sql': 'sql', '.md': 'markdown', '.conf': 'ini', '.ini': 'ini',
            '.service': 'ini', '.env': 'ini', '.vue': 'html', '.jsx': 'javascript',
        }
        return mapping.get(ext, 'plaintext')

    def switch_tab(path):
        if path not in editor_state['files']:
            return
        editor_state['active_path'] = path
        f_data = editor_state['files'][path]

        b64 = base64.b64encode(f_data['content'].encode('utf-8')).decode('utf-8')
        js = f'''
            if (window.editorInstance) {{
                window.isSwitchingTab = true;
                const text = decodeURIComponent(escape(window.atob("{b64}")));
                window.editorInstance.setValue(text);
                monaco.editor.setModelLanguage(window.editorInstance.getModel(), "{f_data['lang']}");
                window.isSwitchingTab = false;
            }}
        '''
        ui.run_javascript(js)
        if editor_state.get('refresh_tabs'):
            editor_state['refresh_tabs']()

    def close_tab(path):
        if path in editor_state['files']:
            del editor_state['files'][path]

        if not editor_state['files']:
            close_all()
            return

        if editor_state['active_path'] == path:
            switch_tab(list(editor_state['files'].keys())[0])
        else:
            if editor_state.get('refresh_tabs'):
                editor_state['refresh_tabs']()

    async def save_active_file():
        path = editor_state['active_path']
        if not path:
            return
        f_data = editor_state['files'][path]

        s_notify = ui.notification('正在保存...', timeout=0, spinner=True)
        try:
            await run.io_bound(write_remote_file, server_conf, path, f_data['content'])
            f_data['saved_content'] = f_data['content']
            s_notify.dismiss()
            safe_notify(f'✅ {f_data["name"]} 已保存', 'positive')
            if editor_state.get('refresh_tabs'):
                editor_state['refresh_tabs']()
            await refresh_remote_dir(file_state['current_path'])
        except Exception as e:
            s_notify.dismiss()
            safe_notify(f'❌ 保存失败: {e}', 'negative')

    def close_all():
        if editor_state['dialog']:
            editor_state['dialog'].close()
        editor_state.update({'dialog': None, 'files': {}})
        ui.run_javascript('if(window.editorInstance){window.editorInstance.dispose(); window.editorInstance=null;}')

    async def open_file_editor(entry):
        remote_path = entry.get('path', '')
        if not is_probably_text_file(remote_path):
            safe_notify('该文件可能不是文本文件，请下载后本地编辑', 'warning')
            return

        client = ui.context.client

        if remote_path not in editor_state['files']:
            loading_notify = ui.notification(f'正在读取 {entry.get("name", basename(remote_path))}...', timeout=0, spinner=True)
            try:
                result = await run.io_bound(read_remote_file, server_conf, remote_path)
                content = result.get('content', '')
            except Exception as e:
                loading_notify.dismiss()
                safe_notify(f'打开文件失败: {e}', 'negative')
                return
            loading_notify.dismiss()

            editor_state['files'][remote_path] = {
                'name': entry.get('name', basename(remote_path)),
                'content': content,
                'saved_content': content,
                'lang': detect_language(entry.get('name', remote_path)),
            }

        editor_state['active_path'] = remote_path

        if editor_state['dialog'] is not None:
            with client:
                switch_tab(remote_path)
            return

        with client:
            card_id = f'editor_card_{uuid.uuid4().hex[:8]}'
            header_id = f'editor_header_{uuid.uuid4().hex[:8]}'
            container_id = f'monaco_{uuid.uuid4().hex[:8]}'

            with ui.dialog().props('seamless') as editor_d:
                editor_state['dialog'] = editor_d

                with ui.card().props(f'id="{card_id}"').classes('flex flex-col p-0 shadow-[0_20px_50px_rgba(0,0,0,0.5)] border border-slate-600 bg-[#1e293b]') \
                    .style('width: 900px; max-width: 95vw; height: 650px; max-height: 95vh; resize: both; overflow: hidden; position: fixed; top: 10vh; left: 15vw; margin: 0;'):

                    with ui.row().props(f'id="{header_id}"').classes('w-full items-center justify-between bg-[#111827] cursor-move select-none flex-nowrap no-wrap shrink-0 border-b border-slate-700').style('min-height: 38px; padding-right: 8px;'):

                        with ui.row().classes('flex-grow flex-nowrap overflow-x-auto no-scrollbar gap-0 h-full items-end'):
                            @ui.refreshable
                            def render_editor_tabs():
                                for p, f in editor_state['files'].items():
                                    is_active = (p == editor_state['active_path'])
                                    bg_color = 'bg-[#1e293b]' if is_active else 'bg-[#111827]'
                                    txt_color = 'text-blue-400' if is_active else 'text-slate-400'
                                    border = 'border-t-2 border-blue-500' if is_active else 'border-t-2 border-transparent'

                                    with ui.row().classes(f'{bg_color} {border} px-3 py-2 items-center gap-2 cursor-pointer border-r border-slate-700 transition-colors hover:bg-[#1e293b] flex-nowrap group').style('height: 100%;'):
                                        ui.icon('description', size='xs').classes(txt_color)
                                        ui.label(f['name']).classes(f'text-[12px] {txt_color} truncate max-w-[180px] font-mono select-none').on('click', lambda _, path=p: switch_tab(path))

                                        if f['content'] != f['saved_content']:
                                            ui.element('div').classes('w-1.5 h-1.5 rounded-full bg-amber-400 shrink-0')

                                        ui.icon('close', size='xs').classes('text-slate-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer shrink-0').on('click', lambda _, path=p: close_tab(path))

                            editor_state['refresh_tabs'] = render_editor_tabs.refresh
                            render_editor_tabs()

                        with ui.row().classes('gap-2 shrink-0 items-center pl-2'):
                            ui.button('保存 (Save)', icon='save', on_click=save_active_file).props('flat dense').classes('text-green-400 font-bold bg-slate-800 px-3 py-1 rounded hover:bg-slate-700 text-[12px]')
                            ui.button('关闭 (Close)', icon='close', on_click=close_all).props('flat dense').classes('text-slate-400 bg-slate-800 px-3 py-1 rounded hover:bg-slate-700 hover:text-white text-[12px]')

                    with ui.element('div').classes('w-full relative flex-grow bg-[#1e293b]').style('min-height: 0; flex: 1 1 auto;'):
                        ui.element('div').props(f'id="{container_id}"').classes('absolute inset-0')

                    def on_sync(e):
                        if editor_state['active_path']:
                            editor_state['files'][editor_state['active_path']]['content'] = e.value
                            if editor_state.get('refresh_tabs'):
                                editor_state['refresh_tabs']()

                    ui.textarea().props('id="hidden-editor-sync"').classes('hidden').on_value_change(on_sync)
                    ui.button('ready', on_click=lambda: switch_tab(editor_state['active_path'])).props('id="monaco-ready-btn"').classes('hidden')

            editor_d.open()

            ui.run_javascript(f'''
                setTimeout(() => {{
                    const card = document.getElementById("{card_id}");
                    const header = document.getElementById("{header_id}");
                    const monacoContainer = document.getElementById("{container_id}");

                    if (card && header) {{
                        let isDragging = false;
                        let currentX = 0, currentY = 0;
                        let startX, startY;

                        card.style.transition = 'none';

                        header.addEventListener('mousedown', (e) => {{
                            if (e.target.closest('button') || e.target.closest('.group')) return;
                            isDragging = true;

                            const rect = card.getBoundingClientRect();
                            if (card.style.transform) card.style.transform = 'none';
                            if (card.style.position !== 'fixed') {{
                                card.style.position = 'fixed';
                                card.style.margin = '0';
                            }}
                            card.style.left = rect.left + 'px';
                            card.style.top = rect.top + 'px';
                            card.style.width = rect.width + 'px';
                            card.style.height = rect.height + 'px';

                            startX = e.clientX;
                            startY = e.clientY;
                            initialLeft = rect.left;
                            initialTop = rect.top;
                        }});

                        document.addEventListener('mousemove', (e) => {{
                            if (!isDragging) return;
                            e.preventDefault();
                            const dx = e.clientX - startX;
                            const dy = e.clientY - startY;
                            card.style.left = (initialLeft + dx) + 'px';
                            card.style.top = (initialTop + dy) + 'px';
                        }});

                        document.addEventListener('mouseup', () => {{ isDragging = false; }});

                        if (monacoContainer) {{
                            const resizeObserver = new ResizeObserver(() => {{
                                if (window.editorInstance) {{
                                    window.requestAnimationFrame(() => window.editorInstance.layout());
                                }}
                            }});
                            resizeObserver.observe(card);
                        }}
                    }}

                    if(window.editorInstance) {{
                        document.getElementById("monaco-ready-btn").click();
                        return;
                    }}

                    const initMonaco = () => {{
                        require.config({{ paths: {{ 'vs': 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs' }}}});
                        require(['vs/editor/editor.main'], function() {{
                            window.editorInstance = monaco.editor.create(document.getElementById('{container_id}'), {{
                                value: '',
                                language: 'plaintext',
                                theme: 'vs-dark',
                                automaticLayout: true,
                                fontSize: 14,
                                minimap: {{ enabled: false }},
                                scrollBeyondLastLine: false,
                                wordWrap: "on"
                            }});

                            window.editorInstance.onDidChangeModelContent(() => {{
                                if(window.isSwitchingTab) return;
                                const val = window.editorInstance.getValue();
                                const hiddenArea = document.getElementById("hidden-editor-sync");
                                if(hiddenArea) {{
                                    hiddenArea.value = val;
                                    hiddenArea.dispatchEvent(new Event("input"));
                                }}
                            }});

                            document.getElementById("monaco-ready-btn").click();
                        }});
                    }};

                    if (!window.require) {{
                        const script = document.createElement('script');
                        script.src = 'https://cdnjs.cloudflare.com/ajax/libs/monaco-editor/0.44.0/min/vs/loader.min.js';
                        script.onload = initMonaco;
                        document.head.appendChild(script);
                    }} else {{
                        initMonaco();
                    }}
                }}, 150);
            ''')

    async def download_entry(entry):
        remote_path = entry.get('path', '')
        try:
            data = await run.io_bound(download_remote_file, server_conf, remote_path)
            ui.download(data, entry.get('name') or os.path.basename(remote_path) or 'download.bin')
            safe_notify('开始下载文件', 'positive')
        except Exception as e:
            safe_notify(f'下载失败: {e}', 'negative')

    async def confirm_delete_entry(entry):
        target_name = entry.get('name', '未知目标')
        target_path = entry.get('path', '')
        target_type = '目录' if entry.get('is_dir') else '文件'
        with ui.dialog() as d, ui.card().classes('w-96 p-5 bg-[#1e293b] border border-slate-700'):
            ui.label('删除确认').classes('text-lg font-bold text-red-400')
            ui.label(f'确定删除{target_type} [{target_name}] 吗？').classes('text-sm text-slate-300')
            ui.label('目录将递归删除，操作不可恢复。').classes('text-xs text-slate-500')

            async def do_delete():
                try:
                    await run.io_bound(delete_remote_path, server_conf, target_path)
                    safe_notify(f'{target_type}已删除', 'positive')
                    d.close()
                    parent = get_parent_remote_path(target_path)
                    await ensure_tree_children(parent, force=True)
                    await ensure_tree_children(file_state['current_path'], force=True)
                    await refresh_remote_dir(file_state['current_path'])
                except Exception as e:
                    safe_notify(f'删除失败: {e}', 'negative')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('取消', on_click=d.close).props('flat color=grey')
                ui.button('删除', icon='delete', on_click=do_delete).classes('bg-red-600 text-white font-bold rounded-lg border-b-4 border-red-800 active:border-b-0 active:translate-y-[2px]')
        d.open()

    def open_create_dialog(kind):
        label = '文件夹' if kind == 'dir' else '文件'
        with ui.dialog() as d, ui.card().classes('w-96 p-5 bg-[#1e293b] border border-slate-700'):
            ui.label(f'新建{label}').classes('text-lg font-bold text-white')
            name_input = ui.input('名称').classes('w-full').props('outlined dense dark bg-color="slate-800"')

            async def create_target():
                name = (name_input.value or '').strip()
                if not name:
                    safe_notify('名称不能为空', 'warning')
                    return
                target_path = join_remote_path(file_state['current_path'], name)
                try:
                    if kind == 'dir':
                        await run.io_bound(make_remote_dir, server_conf, target_path)
                        await ensure_tree_children(file_state['current_path'], force=True)
                    else:
                        await run.io_bound(create_empty_remote_file, server_conf, target_path)
                    safe_notify(f'{label}创建成功', 'positive')
                    d.close()
                    await refresh_remote_dir(file_state['current_path'])
                except Exception as e:
                    safe_notify(f'创建失败: {e}', 'negative')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('取消', on_click=d.close).props('flat color=grey')
                ui.button('创建', icon='add', on_click=create_target).classes('bg-blue-600 text-white font-bold rounded-lg border-b-4 border-blue-800 active:border-b-0 active:translate-y-[2px]')
        d.open()

    def open_rename_dialog(entry):
        old_name = entry.get('name', '')
        old_path = entry.get('path', '')
        with ui.dialog() as d, ui.card().classes('w-96 p-5 bg-[#1e293b] border border-slate-700'):
            ui.label('重命名').classes('text-lg font-bold text-white')
            new_name_input = ui.input('新名称', value=old_name).classes('w-full').props('outlined dense dark bg-color="slate-800"')

            async def do_rename():
                new_name = new_name_input.value.strip()
                if not new_name or new_name == old_name:
                    d.close()
                    return
                new_path = join_remote_path(get_parent_remote_path(old_path), new_name)
                try:
                    await run.io_bound(rename_remote_path, server_conf, old_path, new_path)
                    safe_notify(f'重命名成功: {new_name}', 'positive')
                    d.close()
                    await refresh_remote_dir(file_state['current_path'])
                except Exception as e:
                    safe_notify(f'重命名失败: {e}', 'negative')

            with ui.row().classes('w-full justify-end gap-2 mt-4'):
                ui.button('取消', on_click=d.close).props('flat color=grey')
                ui.button('确认', on_click=do_rename).classes('bg-blue-600 text-white font-bold rounded-lg')
        d.open()

    def open_chmod_dialog(entry):
        target_path = entry.get('path', '')
        filename = entry.get('name', '')
        current_mode_str = entry.get('mode', '----------')

        owner_r = len(current_mode_str) > 1 and current_mode_str[1] == 'r'
        owner_w = len(current_mode_str) > 2 and current_mode_str[2] == 'w'
        owner_x = len(current_mode_str) > 3 and current_mode_str[3] in ('x', 's', 'S')

        group_r = len(current_mode_str) > 4 and current_mode_str[4] == 'r'
        group_w = len(current_mode_str) > 5 and current_mode_str[5] == 'w'
        group_x = len(current_mode_str) > 6 and current_mode_str[6] in ('x', 's', 'S')

        other_r = len(current_mode_str) > 7 and current_mode_str[7] == 'r'
        other_w = len(current_mode_str) > 8 and current_mode_str[8] == 'w'
        other_x = len(current_mode_str) > 9 and current_mode_str[9] in ('x', 't', 'T')

        with ui.dialog() as d, ui.card().classes('w-80 p-0 bg-[#1e293b] border border-slate-700 shadow-2xl overflow-hidden rounded-lg'):
            with ui.row().classes('w-full items-center justify-between px-4 py-2 bg-[#111827] border-b border-slate-700'):
                with ui.row().classes('items-center gap-2'):
                    ui.element('div').classes('w-3 h-3 rounded-full bg-[#ff5f56]')
                    ui.element('div').classes('w-3 h-3 rounded-full bg-[#ffbd2e]')
                    ui.element('div').classes('w-3 h-3 rounded-full bg-[#27c93f]')
                    ui.label('修改文件权限').classes('text-xs font-bold text-slate-300 ml-2 tracking-wide')
                ui.button(icon='close', on_click=d.close).props('flat round dense size=xs color=grey')

            with ui.column().classes('w-full p-5 gap-0'):
                ui.label(filename).classes('text-xl font-bold text-white mb-4 truncate w-full border-b border-slate-700 pb-2')

                state = {
                    'owner': {'r': owner_r, 'w': owner_w, 'x': owner_x},
                    'group': {'r': group_r, 'w': group_w, 'x': group_x},
                    'other': {'r': other_r, 'w': other_w, 'x': other_x},
                }

                def make_checkbox_group(title, key):
                    with ui.column().classes('w-full gap-1 mb-4'):
                        ui.label(title).classes('text-xs text-slate-400')
                        with ui.row().classes('w-full gap-6 px-3 py-2 bg-[#0f1724] rounded-md border border-slate-700 items-center justify-start'):
                            state[key]['r_chk'] = ui.checkbox('读取', value=state[key]['r']).classes('text-sm text-slate-200')
                            state[key]['w_chk'] = ui.checkbox('写入', value=state[key]['w']).classes('text-sm text-slate-200')
                            state[key]['x_chk'] = ui.checkbox('执行', value=state[key]['x']).classes('text-sm text-slate-200')

                make_checkbox_group('所有者 (Owner)', 'owner')
                make_checkbox_group('组 (Group)', 'group')
                make_checkbox_group('其他 (Others)', 'other')

                async def do_chmod():
                    calc = lambda k: (4 if state[k]['r_chk'].value else 0) + (2 if state[k]['w_chk'].value else 0) + (1 if state[k]['x_chk'].value else 0)

                    new_mode = f"{calc('owner')}{calc('group')}{calc('other')}"

                    s_notify = ui.notification(f'正在修改权限为 {new_mode}...', timeout=0, spinner=True)
                    try:
                        cmd = f"chmod {new_mode} '{target_path}'"
                        success, output = await run.io_bound(lambda: _ssh_exec_wrapper(server_conf, cmd))
                        s_notify.dismiss()
                        if success:
                            safe_notify(f'权限已更新: {new_mode}', 'positive')
                            d.close()
                            await refresh_remote_dir(file_state['current_path'])
                        else:
                            safe_notify(f'修改失败: {output}', 'negative')
                    except Exception as e:
                        s_notify.dismiss()
                        safe_notify(f'修改报错: {e}', 'negative')

                with ui.row().classes('w-full justify-center gap-4 mt-2'):
                    ui.button('确定', on_click=do_chmod).classes('bg-blue-600 text-white font-bold w-24 rounded-md').props('unelevated')
                    ui.button('取消', on_click=d.close).classes('bg-[#23314a] text-slate-300 font-bold w-24 rounded-md').props('unelevated')

        d.open()

    async def handle_direct_upload(e):
        try:
            remote_path = join_remote_path(file_state['current_path'], e.name)

            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(e.content.read())
                tmp_path = tmp.name

            await run.io_bound(upload_remote_file, server_conf, tmp_path, remote_path)

            os.remove(tmp_path)
            safe_notify(f'✅ {e.name} 上传成功', 'positive')
        except Exception as ex:
            safe_notify(f'❌ 上传失败: {ex}', 'negative')
        finally:
            await refresh_remote_dir(file_state['current_path'])

    def make_open_handler(entry):
        async def handler(e=None):
            await handle_entry_open(entry)
        return handler

    def make_edit_handler(entry):
        async def handler(e=None):
            await open_file_editor(entry)
        return handler

    def make_download_handler(entry):
        async def handler(e=None):
            await download_entry(entry)
        return handler

    def make_delete_handler(entry):
        async def handler(e=None):
            await confirm_delete_entry(entry)
        return handler

    def make_rename_handler(entry):
        async def handler(e=None):
            open_rename_dialog(entry)
        return handler

    def make_chmod_handler(entry):
        async def handler(e=None):
            open_chmod_dialog(entry)
        return handler

    @ui.refreshable
    def render_tree():
        def node(path, depth=0):
            display_name = basename(path)
            is_selected = tree_state['selected'] == path
            is_expanded = path in tree_state['expanded']
            children = tree_state['cache'].get(path, []) if is_expanded else []
            loading = path in tree_state['loading']

            row_classes = 'w-full items-center gap-1 px-2 py-1 rounded-sm cursor-pointer transition-colors no-wrap '
            row_classes += 'bg-[#1f2a44] border border-[#31415f]' if is_selected else 'hover:bg-[#182234]'

            with ui.column().classes('w-full gap-0'):
                with ui.row().classes(row_classes).style(f'padding-left: {5 + depth * 16}px'):
                    ui.button(icon='expand_more' if is_expanded else 'chevron_right', on_click=lambda _, p=path: toggle_tree_node(p)).props('flat dense round size=xs color=grey').classes('!min-w-0 !p-0 opacity-80 shrink-0')

                    ui.icon('folder_open' if is_expanded else 'folder').classes('text-amber-400 text-[16px] shrink-0')
                    ui.label(display_name).classes('text-[13px] text-slate-200 cursor-pointer select-none truncate').on('click', lambda _, p=path: select_tree_node(p))

                if loading:
                    ui.label('加载中...').classes('text-[11px] text-slate-500 ml-8 py-0.5')
                if is_expanded:
                    sorted_children = sorted(children, key=lambda x: x.get('name', '').lower())
                    for child in sorted_children:
                        node(child.get('path', '/'), depth + 1)

        with ui.column().classes('w-full gap-0 p-1 bg-[#0f1724] h-full overflow-hidden flex-nowrap'):
            node('/')

    @ui.refreshable
    def render_file_list():
        entries = file_state.get('entries', [])
        sorted_entries = sorted(entries, key=lambda x: (not x.get('is_dir'), x.get('name', '').lower()))

        with ui.column().classes('w-full gap-0 bg-[#0d1524] h-full overflow-hidden flex-nowrap'):
            with ui.row().classes('w-full items-center px-2 py-1.5 text-[12px] text-slate-400 border-b border-slate-700 bg-[#131d2d] flex-nowrap no-wrap tracking-wider'):
                ui.label('文件名').classes('w-[26%] border-r border-slate-700 pl-1 truncate')
                ui.label('大小').classes('w-[12%] border-r border-slate-700 pl-1 truncate')
                ui.label('类型').classes('w-[12%] border-r border-slate-700 pl-1 truncate')
                ui.label('修改时间').classes('w-[20%] border-r border-slate-700 pl-1 truncate')
                ui.label('权限').classes('w-[13%] border-r border-slate-700 pl-1 truncate')
                ui.label('用户/用户组').classes('w-[17%] pl-1 truncate')

            if file_state.get('loading'):
                with ui.column().classes('w-full items-center justify-center py-10 text-slate-500'):
                    ui.spinner('dots', size='2rem', color='primary')
                    ui.label('正在读取远程目录...').classes('text-xs')
                return

            if not sorted_entries:
                with ui.column().classes('w-full items-center justify-center py-10 text-slate-500'):
                    ui.icon('folder_off').classes('text-2xl')
                    ui.label('当前目录为空').classes('text-xs')
                return

            for index, item in enumerate(sorted_entries):
                is_dir = item.get('is_dir', False)
                row_classes = 'w-full items-center px-2 py-1.5 border-b border-[#182232] cursor-default transition-colors hover:bg-[#182234] flex-nowrap no-wrap'

                with ui.row().classes(row_classes) as row:
                    with ui.context_menu().classes('bg-[#1e293b] text-slate-200 border border-slate-700 text-[13px] font-bold min-w-[140px]'):
                        if is_dir:
                            ui.menu_item('📂 打开 (Open)', on_click=make_open_handler(item)).classes('hover:bg-slate-700 py-1')
                            ui.separator().classes('bg-slate-600')
                            ui.menu_item('✏️ 重命名 (Rename)', on_click=make_rename_handler(item)).classes('hover:bg-slate-700 py-1')
                            ui.menu_item('🔑 权限 (Chmod)', on_click=make_chmod_handler(item)).classes('hover:bg-slate-700 py-1')
                            ui.separator().classes('bg-slate-600')
                            ui.menu_item('🗑️ 删除 (Delete)', on_click=make_delete_handler(item)).classes('text-red-400 hover:bg-slate-700 py-1')
                        else:
                            ui.menu_item('📝 打开 / 编辑', on_click=make_edit_handler(item)).classes('hover:bg-slate-700 py-1')
                            ui.menu_item('⬇️ 下载 (Download)', on_click=make_download_handler(item)).classes('hover:bg-slate-700 py-1')
                            ui.separator().classes('bg-slate-600')
                            ui.menu_item('✏️ 重命名 (Rename)', on_click=make_rename_handler(item)).classes('hover:bg-slate-700 py-1')
                            ui.menu_item('🔑 权限 (Chmod)', on_click=make_chmod_handler(item)).classes('hover:bg-slate-700 py-1')
                            ui.separator().classes('bg-slate-600')
                            ui.menu_item('🗑️ 删除 (Delete)', on_click=make_delete_handler(item)).classes('text-red-400 hover:bg-slate-700 py-1')

                    with ui.row().classes('w-[26%] items-center gap-1.5 min-w-0 flex-nowrap no-wrap pl-1'):
                        icon_name = 'folder' if is_dir else 'description'
                        icon_color = 'text-amber-400' if is_dir else 'text-cyan-400'
                        ui.icon(icon_name).classes(f'{icon_color} text-[16px] shrink-0')
                        ui.label(item.get('name', '')).classes('truncate text-[13px] text-slate-200')

                    size_str = '' if is_dir else format_file_size(item.get('size', 0))
                    ui.label(size_str).classes('w-[12%] text-xs text-slate-400 pl-1 truncate')

                    type_str = '文件夹' if is_dir else '文件'
                    ui.label(type_str).classes('w-[12%] text-xs text-slate-400 pl-1 truncate')

                    ui.label(format_mtime(item.get('mtime', 0))).classes('w-[20%] text-xs text-slate-500 pl-1 truncate')

                    ui.label(item.get('mode', '--')).classes('w-[13%] text-xs text-slate-400 font-mono pl-1 truncate')

                    owner_str = item.get('owner', 'root/root')
                    ui.label(owner_str).classes('w-[17%] text-xs text-slate-400 pl-1 truncate')

                row.on('dblclick', make_open_handler(item))

    with content_container:
        with ui.column().classes('w-full max-w-[1440px] mx-auto h-full flex flex-col gap-0 flex-nowrap'):
            with ui.card().classes('w-full p-0 rounded-xl border border-slate-700 border-b-[4px] border-b-slate-800 shadow-lg overflow-hidden bg-slate-900 flex flex-col flex-shrink-0'):
                with ui.row().classes('w-full items-center justify-between px-4 py-3 border-b border-slate-700 bg-[#111827]'):
                    with ui.row().classes('items-center gap-3'):
                        ui.icon('terminal').classes('text-green-400')
                        with ui.column().classes('gap-0'):
                            raw_host = server_conf.get('ssh_host') or server_conf.get('url', '').replace('http://', '').replace('https://', '').split(':')[0]
                            display_ip = raw_host
                            if raw_host and not (':' in raw_host or raw_host.replace('.', '').isdigit()):
                                try:
                                    display_ip = await asyncio.wait_for(run.io_bound(_sync_resolve_ip, raw_host), timeout=1.5)
                                except:
                                    display_ip = raw_host

                            ui.label(f"SSH Console · {server_conf.get('ssh_user', 'root')}@{display_ip}").classes('text-slate-100 font-bold')
                            ui.label(server_conf.get('name', '未命名服务器')).classes('text-xs text-slate-500')
                    
                    with ui.row().classes('items-center gap-2'):
                        ui.button('返回详情', icon='arrow_back', on_click=_back_to_detail).props('outline color=grey').classes('text-slate-200')

                # --- 终极修正：用 @ui.refreshable 绝对掌控按钮状态与颜色，并极致压缩边距 ---
                conn_state = {'connected': True}

                async def _do_reconnect():
                    cleanup_ssh_route_terminal(server_key)
                    safe_notify('⚡️ 正在重新连接 SSH...', 'ongoing')
                    await _start_terminal(terminal_box)

                def _do_disconnect():
                    cleanup_ssh_route_terminal(server_key)
                    terminal_box.clear()
                    with terminal_box:
                        with ui.column().classes('w-full h-full items-center justify-center text-slate-500 gap-2'):
                            ui.icon('link_off', size='3rem').classes('text-slate-600')
                            ui.label('SSH 已手动断开').classes('text-sm font-bold tracking-wider')
                    safe_notify('⛓️‍💥 SSH 连接已掐断', 'warning')

                def toggle_connection():
                    if conn_state['connected']:
                        _do_disconnect()
                        conn_state['connected'] = False
                    else:
                        asyncio.create_task(_do_reconnect())
                        conn_state['connected'] = True
                    render_conn_btn.refresh()

                @ui.refreshable
                def render_conn_btn():
                    if conn_state['connected']:
                        btn = ui.button(icon='bolt', on_click=toggle_connection).props('flat dense round size=sm color=positive').classes('p-1 m-0 min-h-0 min-w-0 transition-all')
                        btn.tooltip('点击断开 SSH')
                    else:
                        btn = ui.button(icon='link_off', on_click=toggle_connection).props('flat dense round size=sm color=negative').classes('p-1 m-0 min-h-0 min-w-0 transition-all')
                        btn.tooltip('点击重连 SSH')

                with ui.row().classes('w-full items-center justify-between px-4 py-1 bg-slate-800 border-b border-slate-700 min-h-[32px]'):
                    with ui.row().classes('items-center gap-2'):
                        ui.badge('独立路由终端', color='green').props('outline rounded')
                        ui.badge('交互模式', color='blue').props('outline rounded')
                    render_conn_btn()
                # ---------------------------------------------

                terminal_box = ui.element('div').classes('w-full bg-black overflow-hidden').style('height: 420px; min-height: 420px; position: relative;')
                with terminal_box:
                    with ui.column().classes('w-full h-full items-center justify-center text-slate-500'):
                        ui.label('正在初始化 SSH 终端...').classes('text-sm')


            with ui.card().classes('w-full p-4 rounded-xl border border-slate-700 border-b-[4px] border-b-slate-800 shadow-lg overflow-hidden bg-slate-900 flex flex-col flex-shrink-0 mt-4'):
                render_quick_commands()

            with ui.card().classes('w-full h-[46vh] min-h-[420px] p-0 rounded-xl border border-slate-700 border-b-[4px] border-b-slate-800 shadow-lg overflow-hidden bg-slate-900 flex flex-col flex-shrink-0 mt-4'):
                with ui.row().classes('w-full items-center justify-between px-3 py-2 bg-[#131d2d] border-b border-slate-700 gap-2 flex-nowrap'):
                    path_input = ui.input(value=file_state['current_path']).classes('flex-grow text-xs h-8 min-w-[200px]').props('dense outlined dark bg-color="slate-900"')

                    with ui.row().classes('items-center gap-1 flex-nowrap no-wrap'):
                        ui.button('历史').props('outline dense size=sm color=grey').classes('h-7 text-slate-400 border-slate-600 hidden sm:block')
                        ui.button(icon='refresh', on_click=lambda: refresh_remote_dir(file_state['current_path'])).props('flat dense size=sm color=grey').classes('h-7 w-7 text-slate-400').tooltip('刷新')
                        ui.button(icon='arrow_upward', on_click=go_parent_dir).props('flat dense size=sm color=grey').classes('h-7 w-7 text-slate-400').tooltip('返回上级')

                        hidden_uploader = ui.upload(on_upload=handle_direct_upload, multiple=True).props('auto-upload').style('display: none;')
                        ui.button(icon='file_upload', on_click=lambda: ui.run_javascript(f'document.getElementById("c{hidden_uploader.id}").querySelector("input[type=file]").click()')).props('flat dense size=sm color=grey').classes('h-7 w-7 text-slate-400').tooltip('上传文件')

                        ui.button(icon='create_new_folder', on_click=lambda: open_create_dialog('dir')).props('flat dense size=sm color=grey').classes('h-7 w-7 text-green-400').tooltip('新建目录')
                        ui.button(icon='note_add', on_click=lambda: open_create_dialog('file')).props('flat dense size=sm color=grey').classes('h-7 w-7 text-blue-400').tooltip('新建文件')

                with ui.row().classes('w-full min-h-0 flex-grow flex-nowrap no-wrap gap-0'):
                    with ui.column().classes('w-[25%] min-w-[150px] h-full border-r border-[#223048] bg-[#0f1724]'):
                        with ui.scroll_area().classes('w-full h-full'):
                            render_tree()

                    with ui.column().classes('w-[75%] h-full bg-[#0d1524]'):
                        with ui.scroll_area().classes('w-full h-full'):
                            render_file_list()

    _server_dialog.logger.info(f"[SingleSSHRoute] page opened | key={server_key}")

    ui.timer(0.05, lambda: _start_terminal(terminal_box), once=True)
    ui.timer(0.05, lambda: ensure_tree_children('/'), once=True)
    ui.timer(0.05, lambda: refresh_remote_dir('/'), once=True)


__all__ = ['cleanup_ssh_route_terminal', 'render_single_ssh_view']
