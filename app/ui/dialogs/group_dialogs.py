from nicegui import ui

from app.core.state import ADMIN_CONFIG, CURRENT_VIEW_STATE, SERVERS_CACHE
from app.storage.repositories import save_admin_config, save_servers
from app.ui.common.notifications import safe_notify
from app.utils.geo import detect_country_group


def open_quick_group_create_dialog(callback=None):
    selection_map = {s['url']: False for s in SERVERS_CACHE}
    ui_rows = {}

    with ui.dialog() as d, ui.card().classes('w-full max-w-lg h-[85vh] flex flex-col p-0 bg-[#1e293b] border border-slate-700 shadow-2xl'):
        with ui.column().classes('w-full p-4 border-b border-slate-700 bg-[#0f172a] gap-3 flex-shrink-0'):
            with ui.row().classes('w-full justify-between items-center'):
                ui.label('新建分组 (标签模式)').classes('text-lg font-bold text-slate-200')
                ui.button(icon='close', on_click=d.close).props('flat round dense color=grey')

            name_input = ui.input('分组名称', placeholder='例如: 甲骨文云').props('outlined dense dark').classes('w-full')
            search_input = ui.input(placeholder='🔍 搜索筛选服务器...').props('outlined dense clearable dark').classes('w-full')

            def on_search(e):
                keyword = str(e.value).lower().strip()
                for url, item in ui_rows.items():
                    is_match = keyword in item['search_text']
                    item['row'].set_visibility(is_match)
            search_input.on_value_change(on_search)

        with ui.column().classes('w-full flex-grow overflow-hidden relative bg-[#1e293b]'):
            with ui.row().classes('w-full p-2 bg-[#172033] justify-between items-center border-b border-slate-700 flex-shrink-0'):
                ui.label('勾选加入该组:').classes('text-xs font-bold text-slate-400 ml-2')
                with ui.row().classes('gap-1'):
                    ui.button('全选', on_click=lambda: toggle_visible(True)).props('flat dense size=xs color=blue')
                    ui.button('清空', on_click=lambda: toggle_visible(False)).props('flat dense size=xs color=grey')

            with ui.scroll_area().classes('w-full flex-grow p-2'):
                with ui.column().classes('w-full gap-1'):
                    try:
                        sorted_srv = sorted(SERVERS_CACHE, key=lambda x: str(x.get('name', '')))
                    except:
                        sorted_srv = SERVERS_CACHE

                    for s in sorted_srv:
                        search_key = f"{s['name']} {s['url']}".lower()

                        with ui.row().classes('w-full items-center p-2 hover:bg-slate-700 rounded border border-transparent transition cursor-pointer group') as row:
                            chk = ui.checkbox(value=False).props('dense dark color=blue')
                            chk.on('click.stop', lambda: None)
                            chk.on_value_change(lambda e, u=s['url']: selection_map.update({u: e.value}))
                            row.on('click', lambda _, c=chk: c.set_value(not c.value))

                            ui.label(s['name']).classes('text-sm font-bold text-slate-300 ml-2 truncate flex-grow select-none group-hover:text-white')

                            detected = "未知"
                            try:
                                detected = detect_country_group(s['name'], s)
                            except:
                                pass
                            ui.label(detected).classes('text-xs text-slate-500 font-mono')

                        ui_rows[s['url']] = {'row': row, 'chk': chk, 'search_text': search_key}

            def toggle_visible(state):
                count = 0
                for item in ui_rows.values():
                    if item['row'].visible:
                        item['chk'].value = state
                        count += 1
                if state and count > 0:
                    safe_notify(f"已选中 {count} 个", "positive")

        async def save():
            new_name = name_input.value.strip()
            if not new_name:
                return safe_notify('名称不能为空', 'warning')
            existing = set(ADMIN_CONFIG.get('custom_groups', []))
            if new_name in existing:
                return safe_notify('分组已存在', 'warning')
            if 'custom_groups' not in ADMIN_CONFIG:
                ADMIN_CONFIG['custom_groups'] = []
            ADMIN_CONFIG['custom_groups'].append(new_name)
            await save_admin_config()

            count = 0
            for s in SERVERS_CACHE:
                if selection_map.get(s['url'], False):
                    if 'tags' not in s:
                        s['tags'] = []
                    if new_name not in s['tags']:
                        s['tags'].append(new_name)
                        count += 1
                    if s.get('group') == new_name:
                        s['group'] = detect_country_group(s['name'], None)

            if count > 0:
                await save_servers()
            from app.ui.components.sidebar import render_sidebar_content

            render_sidebar_content.refresh()
            safe_notify(f'✅ 分组 "{new_name}" 创建成功', 'positive')
            d.close()
            if callback:
                await callback(new_name)

        with ui.row().classes('w-full p-4 border-t border-slate-700 bg-[#0f172a] justify-end gap-2 flex-shrink-0'):
            ui.button('取消', on_click=d.close).props('flat color=grey')
            ui.button('创建并保存', on_click=save).classes('bg-blue-600 text-white shadow-md')
    d.open()


def open_group_sort_dialog():
    current_groups = ADMIN_CONFIG.get('probe_custom_groups', [])
    if not current_groups:
        safe_notify("暂无自定义视图", "warning")
        return

    temp_list = list(current_groups)

    with ui.dialog() as d, ui.card().classes('w-[400px] max-w-[95vw] h-[60vh] flex flex-col p-0 gap-0 bg-[#1e293b] border border-slate-700 shadow-2xl'):
        with ui.row().classes('w-full p-4 border-b border-slate-700 justify-between items-center bg-[#0f172a] flex-shrink-0'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('sort', color='blue').classes('text-lg')
                ui.label('视图排序').classes('font-bold text-slate-200 text-base')
            ui.button(icon='close', on_click=d.close).props('flat round dense color=grey')

        with ui.scroll_area().classes('w-full flex-grow p-3'):
            list_container = ui.column().classes('w-full gap-2')

        def render_list():
            list_container.clear()
            with list_container:
                for i, name in enumerate(temp_list):
                    with ui.row().classes('w-full p-3 items-center gap-3 border border-slate-700 rounded-lg bg-[#0f172a] shadow-sm transition-all hover:border-blue-500'):
                        ui.label(str(i + 1)).classes('text-xs text-slate-500 font-mono w-4 text-center font-bold')
                        ui.label(name).classes('font-bold text-slate-300 flex-grow text-sm truncate')

                        with ui.row().classes('gap-1'):
                            if i > 0:
                                ui.button(icon='arrow_upward', on_click=lambda _, idx=i: move_item(idx, -1)) \
                                    .props('flat dense round size=xs color=blue-4').classes('hover:bg-slate-700')
                            else:
                                ui.element('div').classes('w-6')

                            if i < len(temp_list) - 1:
                                ui.button(icon='arrow_downward', on_click=lambda _, idx=i: move_item(idx, 1)) \
                                    .props('flat dense round size=xs color=blue-4').classes('hover:bg-slate-700')
                            else:
                                ui.element('div').classes('w-6')

        def move_item(index, direction):
            target = index + direction
            if 0 <= target < len(temp_list):
                temp_list[index], temp_list[target] = temp_list[target], temp_list[index]
                render_list()

        render_list()

        async def save():
            ADMIN_CONFIG['probe_custom_groups'] = temp_list
            await save_admin_config()
            safe_notify("✅ 分组顺序已更新", "positive")
            d.close()
            try:
                from app.ui.pages.probe_page import render_probe_page

                await render_probe_page()
            except:
                pass

        with ui.row().classes('w-full p-4 border-t border-slate-700 bg-[#0f172a] flex-shrink-0'):
            ui.button('保存顺序', icon='save', on_click=save).classes('w-full bg-blue-600 text-white shadow-lg hover:bg-blue-500')

    d.open()


def open_unified_group_manager(mode='manage'):
    if 'probe_custom_groups' not in ADMIN_CONFIG:
        ADMIN_CONFIG['probe_custom_groups'] = []

    state = {
        'current_group': None,
        'selected_urls': set(),
        'checkboxes': {},
        'page': 1,
        'search_text': ''
    }

    view_list_container = None
    server_list_container = None
    title_input = None
    pagination_ref = None

    with ui.dialog() as d, ui.card().classes('w-full max-w-5xl h-[90vh] flex flex-col p-0 gap-0 bg-[#1e293b] border border-slate-700 shadow-2xl'):
        with ui.row().classes('w-full p-3 bg-[#0f172a] border-b border-slate-700 items-center gap-2 overflow-x-auto flex-shrink-0'):
            ui.label('视图列表:').classes('font-bold text-slate-400 mr-2 text-xs')
            ui.button('➕ 新建分组', on_click=lambda: load_group_data(None)).props('unelevated color=green text-color=white size=sm')
            ui.separator().props('vertical dark').classes('mx-2 h-6')
            view_list_container = ui.row().classes('gap-2 items-center flex-nowrap')
            ui.space()
            ui.button(icon='close', on_click=d.close).props('flat round dense color=grey')

        with ui.row().classes('w-full p-4 bg-[#1e293b] border-b border-slate-700 items-center gap-4 flex-shrink-0 wrap'):
            title_input = ui.input('视图名称', placeholder='请输入分组名称...').props('outlined dense dark').classes('min-w-[200px] flex-grow font-bold')
            ui.input(placeholder='🔍 搜索服务器...', on_change=lambda e: update_search(e.value)).props('outlined dense dense dark').classes('w-48')

            with ui.row().classes('gap-2'):
                ui.button('全选本页', on_click=lambda: toggle_page_all(True)).props('flat dense size=sm color=blue')
                ui.button('清空本页', on_click=lambda: toggle_page_all(False)).props('flat dense size=sm color=grey')

        with ui.scroll_area().classes('w-full flex-grow p-4 bg-[#0f172a]'):
            server_list_container = ui.column().classes('w-full gap-2')

        with ui.row().classes('w-full p-2 justify-center bg-[#1e293b] border-t border-slate-700'):
            pagination_ref = ui.row()

        with ui.row().classes('w-full p-4 bg-[#0f172a] border-t border-slate-700 justify-between items-center flex-shrink-0'):
            ui.button('删除此视图', icon='delete', color='red', on_click=lambda: delete_current_group()).props('flat')
            ui.button('保存当前配置', icon='save', on_click=lambda: save_current_group()).classes('bg-blue-600 text-white shadow-lg')

    def update_search(val):
        state['search_text'] = str(val).lower().strip()
        state['page'] = 1
        render_servers()

    def render_views():
        view_list_container.clear()
        groups = ADMIN_CONFIG.get('probe_custom_groups', [])
        with view_list_container:
            for g in groups:
                is_active = (g == state['current_group'])
                btn_props = 'unelevated color=blue' if is_active else 'outline color=grey-5 text-color=grey-4'
                ui.button(g, on_click=lambda _, name=g: load_group_data(name)).props(f'{btn_props} size=sm')

    def load_group_data(group_name):
        state['current_group'] = group_name
        state['page'] = 1
        state['selected_urls'] = set()

        if group_name:
            for s in SERVERS_CACHE:
                if (group_name in s.get('tags', [])) or (s.get('group') == group_name):
                    state['selected_urls'].add(s['url'])

        render_views()
        title_input.value = group_name if group_name else ''
        if not group_name:
            title_input.run_method('focus')
        render_servers()

    def render_servers():
        server_list_container.clear()
        pagination_ref.clear()
        state['checkboxes'] = {}

        if not SERVERS_CACHE:
            with server_list_container:
                ui.label('暂无服务器').classes('text-center text-slate-500 mt-10 w-full')
            return

        all_srv = SERVERS_CACHE
        if state['search_text']:
            all_srv = [s for s in all_srv if state['search_text'] in s.get('name', '').lower() or state['search_text'] in s.get('url', '').lower()]

        try:
            sorted_servers = sorted(all_srv, key=lambda x: str(x.get('name', '')))
        except:
            sorted_servers = all_srv

        PAGE_SIZE = 48
        total_items = len(sorted_servers)
        total_pages = (total_items + PAGE_SIZE - 1) // PAGE_SIZE
        if state['page'] > total_pages:
            state['page'] = 1
        if state['page'] < 1:
            state['page'] = 1

        start_idx = (state['page'] - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        current_page_items = sorted_servers[start_idx:end_idx]

        with server_list_container:
            ui.label(f"共 {total_items} 台 (第 {state['page']}/{total_pages} 页)").classes('text-xs text-slate-400 mb-2')

            with ui.grid().classes('w-full grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2'):
                for s in current_page_items:
                    url = s.get('url')
                    if not url:
                        continue
                    is_checked = url in state['selected_urls']

                    bg_cls = 'bg-blue-900/30 border-blue-500/50' if is_checked else 'bg-[#172033] border-slate-700'

                    with ui.row().classes(f'items-center p-2 border rounded cursor-pointer hover:bg-slate-700 transition {bg_cls}') as row:
                        chk = ui.checkbox(value=is_checked).props('dense dark color=green')
                        state['checkboxes'][url] = chk

                        def toggle_row(c=chk, r=row, u=url):
                            c.value = not c.value
                            update_selection(u, c.value)
                            if c.value:
                                r.classes(add='bg-blue-900/30 border-blue-500/50', remove='bg-[#172033] border-slate-700')
                            else:
                                r.classes(remove='bg-blue-900/30 border-blue-500/50', add='bg-[#172033] border-slate-700')

                        row.on('click', toggle_row)
                        chk.on('click.stop', lambda _, c=chk, r=row, u=url: [update_selection(u, c.value),
                            r.classes(add='bg-blue-900/30 border-blue-500/50', remove='bg-[#172033] border-slate-700') if c.value else r.classes(remove='bg-blue-900/30 border-blue-500/50', add='bg-[#172033] border-slate-700')])

                        with ui.column().classes('gap-0 ml-2 overflow-hidden'):
                            ui.label(s.get('name', 'Unknown')).classes('text-sm font-bold truncate text-slate-200')
                            if is_checked:
                                ui.label('已选中').classes('text-[10px] text-green-400 font-bold')
                            else:
                                ui.label(s.get('group', '')).classes('text-[10px] text-slate-500')

        if total_pages > 1:
            with pagination_ref:
                p = ui.pagination(1, total_pages, direction_links=True).props('dense color=blue text-color=slate-400 active-text-color=white')
                p.value = state['page']
                p.on('update:model-value', lambda e: [state.update({'page': e.args}), render_servers()])

    def update_selection(url, checked):
        if checked:
            state['selected_urls'].add(url)
        else:
            state['selected_urls'].discard(url)

    def toggle_page_all(val):
        for url in state['checkboxes'].keys():
            if val:
                state['selected_urls'].add(url)
            else:
                state['selected_urls'].discard(url)
        render_servers()

    async def save_current_group():
        old_name = state['current_group']
        new_name = title_input.value.strip()
        if not new_name:
            return safe_notify("名称不能为空", "warning")

        groups = ADMIN_CONFIG.get('probe_custom_groups', [])

        if not old_name:
            if new_name in groups:
                return safe_notify("名称已存在", "negative")
            groups.append(new_name)
        elif new_name != old_name:
            if new_name in groups:
                return safe_notify("名称已存在", "negative")
            idx = groups.index(old_name)
            groups[idx] = new_name
            for s in SERVERS_CACHE:
                if 'tags' in s and old_name in s['tags']:
                    s['tags'].remove(old_name)
                    s['tags'].append(new_name)

        for s in SERVERS_CACHE:
            if 'tags' not in s:
                s['tags'] = []
            if s['url'] in state['selected_urls']:
                if new_name not in s['tags']:
                    s['tags'].append(new_name)
            else:
                if new_name in s['tags']:
                    s['tags'].remove(new_name)

        ADMIN_CONFIG['probe_custom_groups'] = groups
        await save_admin_config()
        await save_servers()
        safe_notify(f"✅ 保存成功", "positive")
        load_group_data(new_name)
        try:
            from app.ui.pages.probe_page import render_probe_page

            await render_probe_page()
        except:
            pass

    async def delete_current_group():
        target = state['current_group']
        if not target:
            return
        if target in ADMIN_CONFIG.get('probe_custom_groups', []):
            ADMIN_CONFIG['probe_custom_groups'].remove(target)
            await save_admin_config()
        for s in SERVERS_CACHE:
            if 'tags' in s and target in s['tags']:
                s['tags'].remove(target)
        await save_servers()
        safe_notify("🗑️ 已删除", "positive")
        load_group_data(None)
        try:
            from app.ui.pages.probe_page import render_probe_page

            await render_probe_page()
        except:
            pass

    def init():
        render_views()
        load_group_data(None)

    ui.timer(0.1, init, once=True)
    d.open()


def open_combined_group_management(group_name):
    ui_rows = {}

    with ui.dialog() as d, ui.card().classes('w-[95vw] max-w-[600px] h-[85vh] flex flex-col p-0 gap-0 overflow-hidden bg-[#1e293b] border border-slate-700 shadow-2xl'):
        with ui.row().classes('w-full justify-between items-center p-4 bg-[#0f172a] border-b border-slate-700 flex-shrink-0'):
            with ui.row().classes('items-center gap-2'):
                ui.icon('settings', color='primary').classes('text-xl')
                ui.label(f'管理分组: {group_name}').classes('text-lg font-bold text-slate-200')
            ui.button(icon='close', on_click=d.close).props('flat round dense color=grey')

        with ui.column().classes('w-full flex-grow overflow-hidden p-0'):
            with ui.column().classes('w-full p-4 border-b border-slate-700 bg-[#1e293b] gap-3 flex-shrink-0'):
                ui.label('分组名称').classes('text-xs font-bold text-slate-500 mb-[-5px]')
                name_input = ui.input(value=group_name).props('outlined dense dark').classes('w-full')

                ui.label('搜索筛选').classes('text-xs font-bold text-slate-500 mb-[-5px]')
                search_input = ui.input(placeholder='🔍 搜名称 / IP...').props('outlined dense clearable dark').classes('w-full')

                def on_search(e):
                    keyword = str(e.value).lower().strip()
                    for url, item in ui_rows.items():
                        is_match = keyword in item['search_text']
                        item['row'].set_visibility(is_match)

                search_input.on_value_change(on_search)

            with ui.column().classes('w-full flex-grow overflow-hidden relative bg-[#0f172a]'):
                with ui.row().classes('w-full p-2 bg-[#172033] justify-between items-center border-b border-slate-700 flex-shrink-0'):
                    ui.label('成员选择:').classes('text-xs font-bold text-slate-400 ml-2')
                    with ui.row().classes('gap-1'):
                        ui.button('全选 (当前)', on_click=lambda: toggle_visible(True)).props('flat dense size=xs color=blue')
                        ui.button('清空', on_click=lambda: toggle_visible(False)).props('flat dense size=xs color=grey')

                with ui.scroll_area().classes('w-full flex-grow p-2'):
                    with ui.column().classes('w-full gap-1'):
                        selection_map = {}

                        try:
                            sorted_servers = sorted(SERVERS_CACHE, key=lambda x: str(x.get('name', '')))
                        except:
                            sorted_servers = SERVERS_CACHE

                        if not sorted_servers:
                            ui.label('暂无服务器数据').classes('w-full text-center text-slate-500 mt-4')

                        for s in sorted_servers:
                            tags = s.get('tags', [])
                            if not isinstance(tags, list):
                                tags = []
                            is_in_group = group_name in tags
                            if s.get('group') == group_name:
                                is_in_group = True

                            selection_map[s['url']] = is_in_group

                            ip_addr = s['url'].split('//')[-1].split(':')[0]
                            search_key = f"{s['name']} {ip_addr}".lower()

                            bg_cls = 'bg-blue-900/30 border-blue-500/50' if is_in_group else 'bg-[#1e293b] border-slate-700'

                            with ui.row().classes(f'w-full items-center p-2 hover:bg-slate-700 rounded border transition cursor-pointer {bg_cls}') as row:
                                chk = ui.checkbox(value=is_in_group).props('dense dark color=green')

                                def toggle_row(c=chk, r=row, u=s['url']):
                                    c.set_value(not c.value)
                                    if c.value:
                                        r.classes(add='bg-blue-900/30 border-blue-500/50', remove='bg-[#1e293b] border-slate-700')
                                    else:
                                        r.classes(remove='bg-blue-900/30 border-blue-500/50', add='bg-[#1e293b] border-slate-700')

                                row.on('click', toggle_row)
                                chk.on('click.stop', lambda: None)

                                chk.on_value_change(lambda e, u=s['url']: selection_map.update({u: e.value}))

                                with ui.column().classes('gap-0 ml-2 flex-grow overflow-hidden'):
                                    with ui.row().classes('items-center gap-2'):
                                        ui.label(s['name']).classes('text-sm font-bold truncate text-slate-300')

                                try:
                                    real_region = detect_country_group(s['name'], None)
                                    ui.label(real_region).classes('text-xs font-mono text-slate-500')
                                except:
                                    pass

                            ui_rows[s['url']] = {
                                'row': row,
                                'chk': chk,
                                'search_text': search_key
                            }

                def toggle_visible(state):
                    count = 0
                    for item in ui_rows.values():
                        if item['row'].visible:
                            item['chk'].value = state
                            if state:
                                item['row'].classes(add='bg-blue-900/30 border-blue-500/50', remove='bg-[#1e293b] border-slate-700')
                            else:
                                item['row'].classes(remove='bg-blue-900/30 border-blue-500/50', add='bg-[#1e293b] border-slate-700')
                            count += 1
                    if state and count > 0:
                        safe_notify(f"已选中当前显示的 {count} 个服务器", "positive")

        with ui.row().classes('w-full p-4 border-t border-slate-700 bg-[#0f172a] justify-between items-center flex-shrink-0'):
            async def delete_group():
                with ui.dialog() as confirm_d, ui.card().classes('bg-[#1e293b] border border-slate-700'):
                    ui.label(f'确定永久删除分组 "{group_name}"?').classes('font-bold text-red-500')
                    ui.label('服务器将保留，仅移除此标签。').classes('text-xs text-slate-400')
                    with ui.row().classes('w-full justify-end mt-4 gap-2'):
                        ui.button('取消', on_click=confirm_d.close).props('flat dense color=grey')

                        async def do_del():
                            if 'custom_groups' in ADMIN_CONFIG and group_name in ADMIN_CONFIG['custom_groups']:
                                ADMIN_CONFIG['custom_groups'].remove(group_name)

                            for s in SERVERS_CACHE:
                                if 'tags' in s and group_name in s['tags']:
                                    s['tags'].remove(group_name)
                                if s.get('group') == group_name:
                                    try:
                                        s['group'] = detect_country_group(s['name'], None)
                                    except:
                                        s['group'] = '默认分组'

                            await save_admin_config()
                            await save_servers()
                            confirm_d.close()
                            d.close()

                            from app.ui.components.sidebar import render_sidebar_content
                            from app.ui.pages.content_router import refresh_content

                            render_sidebar_content.refresh()
                            if CURRENT_VIEW_STATE.get('scope') == 'TAG' and CURRENT_VIEW_STATE.get('data') == group_name:
                                await refresh_content('ALL')
                            else:
                                safe_notify(f'分组 "{group_name}" 已删除', 'positive')

                        ui.button('确认删除', color='red', on_click=do_del).props('unelevated')
                confirm_d.open()

            ui.button('删除分组', icon='delete', color='red', on_click=delete_group).props('flat')

            async def save_changes():
                new_name = name_input.value.strip()
                if not new_name:
                    return safe_notify('分组名称不能为空', 'warning')

                if new_name != group_name:
                    if 'custom_groups' in ADMIN_CONFIG:
                        if group_name in ADMIN_CONFIG['custom_groups']:
                            idx = ADMIN_CONFIG['custom_groups'].index(group_name)
                            ADMIN_CONFIG['custom_groups'][idx] = new_name
                        else:
                            ADMIN_CONFIG['custom_groups'].append(new_name)
                    await save_admin_config()

                for s in SERVERS_CACHE:
                    if 'tags' not in s:
                        s['tags'] = []
                    should_have_tag = selection_map.get(s['url'], False)

                    if should_have_tag:
                        if new_name not in s['tags']:
                            s['tags'].append(new_name)
                        if new_name != group_name and group_name in s['tags']:
                            s['tags'].remove(group_name)
                    else:
                        if new_name in s['tags']:
                            s['tags'].remove(new_name)
                        if group_name in s['tags']:
                            s['tags'].remove(group_name)

                await save_servers()
                d.close()
                from app.ui.components.sidebar import render_sidebar_content
                from app.ui.pages.content_router import refresh_content

                render_sidebar_content.refresh()

                if CURRENT_VIEW_STATE.get('scope') == 'TAG' and CURRENT_VIEW_STATE.get('data') == group_name:
                    await refresh_content('TAG', new_name, force_refresh=True)

                safe_notify('分组设置已保存', 'positive')

            ui.button('保存修改', icon='save', on_click=save_changes).classes('bg-blue-600 text-white shadow-lg')

    d.open()


def open_create_group_dialog():
    with ui.dialog() as d, ui.card().classes('w-full max-w-sm flex flex-col gap-4 p-6'):
        ui.label('新建自定义分组').classes('text-lg font-bold mb-2')

        name_input = ui.input('分组名称', placeholder='例如: 微软云 / 生产环境').classes('w-full').props('outlined')

        async def save_new_group():
            new_name = name_input.value.strip()
            if not new_name:
                safe_notify("分组名称不能为空", "warning")
                return

            from app.services.server_ops import get_all_groups
            existing_groups = set(get_all_groups())
            if new_name in existing_groups:
                safe_notify("该分组已存在", "warning")
                return

            if 'custom_groups' not in ADMIN_CONFIG:
                ADMIN_CONFIG['custom_groups'] = []
            ADMIN_CONFIG['custom_groups'].append(new_name)
            await save_admin_config()

            d.close()
            from app.ui.components.sidebar import render_sidebar_content

            render_sidebar_content.refresh()
            safe_notify(f"已创建分组: {new_name}", "positive")

        with ui.row().classes('w-full justify-end gap-2 mt-4'):
            ui.button('取消', on_click=d.close).props('flat color=grey')
            ui.button('保存', on_click=save_new_group).classes('bg-blue-600 text-white')
    d.open()
