import asyncio
import json

from nicegui import ui

from app.core.logging import logger
from app.core.state import CURRENT_VIEW_STATE, DASHBOARD_REFS, SERVERS_CACHE
from app.services.dashboard import calculate_dashboard_data
from app.utils.geo import detect_country_group, get_coords_from_name


GLOBE_STRUCTURE = r"""
<style>
    #earth-container {
        width: 100%;
        height: 100%;
        position: relative;
        overflow: hidden;
        border-radius: 12px;
        background-color: #100C2A;
    }

    .earth-stats {
        position: absolute;
        top: 20px;
        left: 20px;
        color: rgba(255, 255, 255, 0.8);
        font-family: 'Consolas', monospace;
        font-size: 12px;
        z-index: 10;
        background: rgba(0, 20, 40, 0.6);
        padding: 10px 15px;
        border: 1px solid rgba(0, 255, 255, 0.3);
        border-radius: 6px;
        backdrop-filter: blur(4px);
        pointer-events: none;
    }
    .earth-stats span { color: #00ffff; font-weight: bold; }
</style>

<div id="earth-container">
    <div class="earth-stats">
        <div>ACTIVE NODES: <span id="node-count">0</span></div>
        <div>REGIONS: <span id="region-count">0</span></div>
    </div>
    <div id="earth-render-area" style="width:100%; height:100%;"></div>
</div>
"""


GLOBE_JS_LOGIC = r"""
(function() {
    var container = document.getElementById('earth-render-area');
    if (!container) return;

    var serverData = window.DASHBOARD_DATA || [];

    var myLat = 39.9;
    var myLon = 116.4;

    var emojiFont = '"Twemoji Country Flags", "Noto Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", sans-serif';

    var nodeCountEl = document.getElementById('node-count');
    var regionCountEl = document.getElementById('region-count');
    function updateStats(data) {
        if(nodeCountEl) nodeCountEl.textContent = data.length;
        const uniqueRegions = new Set(data.map(s => s.name));
        if(regionCountEl) regionCountEl.textContent = uniqueRegions.size;
    }
    updateStats(serverData);

    var existing = echarts.getInstanceByDom(container);
    if (existing) existing.dispose();
    var myChart = echarts.init(container);

    if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition(function(position) {
            myLat = position.coords.latitude;
            myLon = position.coords.longitude;
            var option = buildOption(window.cachedWorldJson, serverData, myLat, myLon);
            myChart.setOption(option);
        });
    }

    window.updateDashboardMap = function(newData) {
        if (!window.cachedWorldJson || !myChart) return;
        serverData = newData;
        updateStats(newData);
        var option = buildOption(window.cachedWorldJson, newData, myLat, myLon);
        myChart.setOption(option);
    };

    const searchKeys = {
        '🇺🇸': 'United States', '🇨🇳': 'China', '🇭🇰': 'China', '🇹🇼': 'China', '🇯🇵': 'Japan', '🇰🇷': 'Korea',
        '🇸🇬': 'Singapore', '🇬🇧': 'United Kingdom', '🇩🇪': 'Germany', '🇫🇷': 'France', '🇷🇺': 'Russia',
        '🇨🇦': 'Canada', '🇦🇺': 'Australia', '🇮🇳': 'India', '🇧🇷': 'Brazil'
    };

    function buildOption(mapGeoJSON, data, userLat, userLon) {
        const mapFeatureNames = mapGeoJSON.features.map(f => f.properties.name);
        const activeMapNames = new Set();

        data.forEach(s => {
            let keyword = null;
            for (let key in searchKeys) {
                if ((s.name && s.name.includes(key))) {
                    keyword = searchKeys[key];
                    break;
                }
            }
            if (keyword && mapFeatureNames.includes(keyword)) {
                activeMapNames.add(keyword);
            }
        });

        const highlightRegions = Array.from(activeMapNames).map(name => ({
            name: name,
            itemStyle: { areaColor: '#0055ff', borderColor: '#00ffff', borderWidth: 1.5, opacity: 0.9 }
        }));

        const scatterData = data.map(s => ({
            name: s.name, value: [s.lon, s.lat], itemStyle: { color: '#00ffff' }
        }));

        scatterData.push({
            name: "ME", value: [userLon, userLat], itemStyle: { color: '#FFD700' },
            symbolSize: 15, label: { show: true, position: 'top', formatter: 'My PC', color: '#FFD700' }
        });

        const linesData = data.map(s => ({
            coords: [[s.lon, s.lat], [userLon, userLat]]
        }));

        return {
            backgroundColor: '#100C2A',
            geo: {
                map: 'world', roam: false, zoom: 1.2, center: [15, 10],
                label: { show: false },
                itemStyle: { areaColor: '#1B2631', borderColor: '#404a59', borderWidth: 1 },
                emphasis: { itemStyle: { areaColor: '#2a333d' }, label: { show: false } },
                regions: highlightRegions
            },
            series: [
                {
                    type: 'lines', coordinateSystem: 'geo', zlevel: 2,
                    effect: { show: true, period: 4, trailLength: 0.5, color: '#00ffff', symbol: 'arrow', symbolSize: 6 },
                    lineStyle: { color: '#00ffff', width: 1, opacity: 0, curveness: 0.2 },
                    data: linesData
                },
                {
                    type: 'scatter', coordinateSystem: 'geo', zlevel: 3, symbol: 'circle', symbolSize: 12,
                    itemStyle: { color: '#00ffff', shadowBlur: 10, shadowColor: '#333' },
                    label: {
                        show: true,
                        position: 'right',
                        formatter: '{b}',
                        color: '#fff',
                        fontSize: 16,
                        fontWeight: 'bold',
                        fontFamily: emojiFont
                    },
                    data: scatterData
                }
            ]
        };
    }

    fetch('/static/world.json')
        .then(response => response.json())
        .then(worldJson => {
            echarts.registerMap('world', worldJson);
            window.cachedWorldJson = worldJson;
            var option = buildOption(worldJson, serverData, myLat, myLon);
            myChart.setOption(option);

            window.addEventListener('resize', () => myChart.resize());
            new ResizeObserver(() => myChart.resize()).observe(container);
        });
})();
"""


async def refresh_dashboard_ui():
    try:
        if not DASHBOARD_REFS.get('servers'):
            return

        data = calculate_dashboard_data()
        if not data:
            return

        if DASHBOARD_REFS.get('servers'):
            DASHBOARD_REFS['servers'].set_text(data['servers'])
        if DASHBOARD_REFS.get('nodes'):
            DASHBOARD_REFS['nodes'].set_text(data['nodes'])
        if DASHBOARD_REFS.get('traffic'):
            DASHBOARD_REFS['traffic'].set_text(data['traffic'])
        if DASHBOARD_REFS.get('subs'):
            DASHBOARD_REFS['subs'].set_text(data['subs'])

        if DASHBOARD_REFS.get('bar_chart'):
            DASHBOARD_REFS['bar_chart'].options['xAxis']['data'] = data['bar_chart']['names']
            DASHBOARD_REFS['bar_chart'].options['series'][0]['data'] = data['bar_chart']['values']
            DASHBOARD_REFS['bar_chart'].update()

        if DASHBOARD_REFS.get('pie_chart'):
            DASHBOARD_REFS['pie_chart'].options['series'][0]['data'] = data['pie_chart']
            DASHBOARD_REFS['pie_chart'].update()

        globe_data_list = []
        seen_locations = set()
        for s in SERVERS_CACHE:
            lat, lon = None, None
            if 'lat' in s and 'lon' in s:
                lat, lon = s['lat'], s['lon']
            else:
                coords = get_coords_from_name(s.get('name', ''))
                if coords:
                    lat, lon = coords[0], coords[1]

            if lat is not None and lon is not None:
                coord_key = (round(lat, 2), round(lon, 2))
                if coord_key not in seen_locations:
                    seen_locations.add(coord_key)
                    flag_only = "📍"
                    try:
                        full_group = detect_country_group(s.get('name', ''), s)
                        flag_only = full_group.split(' ')[0]
                    except:
                        pass
                    globe_data_list.append({'lat': lat, 'lon': lon, 'name': flag_only})

        if CURRENT_VIEW_STATE.get('scope') == 'DASHBOARD':
            json_data = json.dumps(globe_data_list, ensure_ascii=False)
            ui.run_javascript(f'if(window.updateDashboardMap) window.updateDashboardMap({json_data});')

    except Exception as e:
        logger.error(f"UI 更新失败: {e}")


async def load_dashboard_stats():
    global CURRENT_VIEW_STATE
    CURRENT_VIEW_STATE['scope'] = 'DASHBOARD'
    CURRENT_VIEW_STATE['data'] = None

    await asyncio.sleep(0.1)

    from app.ui.pages.content_router import content_container

    content_container.clear()
    content_container.classes(remove='justify-center items-center overflow-hidden p-6', add='overflow-y-auto p-4 pl-6 justify-start')

    init_data = calculate_dashboard_data()
    if not init_data:
        init_data = {
            "servers": "0/0", "nodes": "0", "traffic": "0 GB", "subs": "0",
            "bar_chart": {"names": [], "values": []}, "pie_chart": []
        }

    group_buckets = {}
    for s in SERVERS_CACHE:
        g_name = s.get('group')
        if not g_name or g_name in ['默认分组', '自动注册', '未分组', '自动导入', '🏳️ 其他地区']:
            g_name = detect_country_group(s.get('name', ''))

        if g_name not in group_buckets:
            group_buckets[g_name] = 0
        group_buckets[g_name] += 1

    all_regions = [{'name': k, 'value': v} for k, v in group_buckets.items()]
    all_regions.sort(key=lambda x: x['value'], reverse=True)

    if len(all_regions) > 5:
        top_5 = all_regions[:5]
        others_count = sum(item['value'] for item in all_regions[5:])
        top_5.append({'name': '🏳️ 其他地区', 'value': others_count})
        pie_data_final = top_5
    else:
        pie_data_final = all_regions

    init_data['pie_chart'] = pie_data_final

    with content_container:
        ui.run_javascript("""
        if (window.dashInterval) clearInterval(window.dashInterval);
        window.dashInterval = setInterval(async () => {
            if (document.hidden) return;
            try {
                const res = await fetch('/api/dashboard/live_data');
                if (!res.ok) return;
                const data = await res.json();
                if (data.error) return;

                const ids = ['stat-servers', 'stat-nodes', 'stat-traffic', 'stat-subs'];
                const keys = ['servers', 'nodes', 'traffic', 'subs'];
                ids.forEach((id, i) => {
                    const el = document.getElementById(id);
                    if (el) el.innerText = data[keys[i]];
                });

                const barDom = document.getElementById('chart-bar');
                if (barDom) {
                    const chart = echarts.getInstanceByDom(barDom);
                    if (chart) {
                        chart.setOption({
                            xAxis: { data: data.bar_chart.names },
                            series: [{ data: data.bar_chart.values }]
                        });
                    }
                }
            } catch (e) {}
        }, 3000);
        """)

        ui.label('系统概览').classes('text-3xl font-bold mb-4 text-slate-200 tracking-tight')

        with ui.row().classes('w-full gap-4 mb-6 items-stretch'):
            def create_stat_card(ref_key, dom_id, title, sub_text, icon, gradient, init_val):
                with ui.card().classes(f'flex-1 p-4 shadow-lg border border-white/10 text-white {gradient} rounded-xl relative overflow-hidden'):
                    ui.element('div').classes('absolute -right-4 -top-4 w-24 h-24 bg-white opacity-10 rounded-full blur-xl')
                    with ui.row().classes('items-center justify-between w-full relative z-10'):
                        with ui.column().classes('gap-0'):
                            ui.label(title).classes('opacity-90 text-[11px] font-bold uppercase tracking-wider')
                            DASHBOARD_REFS[ref_key] = ui.label(init_val).props(f'id={dom_id}').classes('text-3xl font-black tracking-tight my-1 drop-shadow-md')
                            ui.label(sub_text).classes('opacity-70 text-[10px] font-medium')
                        ui.icon(icon).classes('text-4xl opacity-80 drop-shadow-sm')

            create_stat_card('servers', 'stat-servers', '在线服务器', 'Online / Total', 'dns', 'bg-gradient-to-br from-blue-600 to-indigo-800', init_data['servers'])
            create_stat_card('nodes', 'stat-nodes', '节点总数', 'Active Nodes', 'hub', 'bg-gradient-to-br from-purple-600 to-fuchsia-800', init_data['nodes'])
            create_stat_card('traffic', 'stat-traffic', '总流量消耗', 'Total Usage', 'bolt', 'bg-gradient-to-br from-emerald-600 to-teal-800', init_data['traffic'])
            create_stat_card('subs', 'stat-subs', '订阅配置', 'Subscriptions', 'rss_feed', 'bg-gradient-to-br from-orange-500 to-red-700', init_data['subs'])

        with ui.row().classes('w-full gap-6 mb-6 flex-wrap xl:flex-nowrap items-stretch'):
            chart_card_cls = 'w-full p-5 shadow-xl border border-slate-700 rounded-xl bg-[#1e293b] flex flex-col'

            with ui.card().classes(f'xl:w-2/3 {chart_card_cls}'):
                with ui.row().classes('w-full justify-between items-center mb-4 border-b border-slate-700 pb-2'):
                    ui.label('📊 服务器流量排行 (GB)').classes('text-base font-bold text-slate-200')
                    with ui.row().classes('items-center gap-1 px-2 py-0.5 bg-green-900/30 rounded-full border border-green-500/30'):
                        ui.element('div').classes('w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse')
                        ui.label('Live').classes('text-[10px] font-bold text-green-400')

                DASHBOARD_REFS['bar_chart'] = ui.echart({
                    'tooltip': {'trigger': 'axis'},
                    'grid': {'left': '2%', 'right': '3%', 'bottom': '2%', 'top': '10%', 'containLabel': True},
                    'xAxis': {'type': 'category', 'data': init_data['bar_chart']['names'], 'axisLabel': {'interval': 0, 'rotate': 30, 'color': '#94a3b8', 'fontSize': 10}},
                    'yAxis': {'type': 'value', 'splitLine': {'lineStyle': {'type': 'dashed', 'color': '#334155'}}, 'axisLabel': {'color': '#94a3b8'}},
                    'series': [{'type': 'bar', 'data': init_data['bar_chart']['values'], 'barWidth': '40%', 'itemStyle': {'borderRadius': [3, 3, 0, 0], 'color': '#6366f1'}}]
                }).classes('w-full h-64').props('id=chart-bar')

            with ui.card().classes(f'xl:w-1/3 {chart_card_cls}'):
                ui.label('🌏 服务器分布').classes('text-base font-bold text-slate-200 mb-4 border-b border-slate-700 pb-2')
                color_palette = ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6', '#6366f1', '#ec4899', '#14b8a6', '#f97316']

                DASHBOARD_REFS['pie_chart'] = ui.echart({
                    'tooltip': {'trigger': 'item', 'formatter': '{b}: <br/><b>{c} 台</b> ({d}%)'},
                    'legend': {'bottom': '0%', 'left': 'center', 'icon': 'circle', 'itemGap': 10, 'textStyle': {'color': '#e2e8f0', 'fontSize': 11}},
                    'color': color_palette,
                    'series': [{
                        'name': '服务器分布',
                        'type': 'pie',
                        'radius': ['45%', '75%'],
                        'center': ['50%', '45%'],
                        'avoidLabelOverlap': False,
                        'itemStyle': {'borderRadius': 4, 'borderColor': '#1e293b', 'borderWidth': 2},
                        'label': {'show': False, 'position': 'center'},
                        'emphasis': {'label': {'show': True, 'fontSize': 16, 'fontWeight': 'bold', 'color': '#fff'}, 'scale': True, 'scaleSize': 5},
                        'labelLine': {'show': False},
                        'data': init_data['pie_chart']
                    }]
                }).classes('w-full h-64').props('id=chart-pie')

        with ui.row().classes('w-full gap-6 mb-6'):
            with ui.card().classes('w-full p-0 shadow-md border-none rounded-xl bg-slate-900 overflow-hidden relative'):
                with ui.row().classes('w-full px-6 py-3 bg-slate-800/50 border-b border-gray-700 justify-between items-center z-10 relative'):
                    with ui.row().classes('gap-2 items-center'):
                        ui.icon('public', color='blue-4').classes('text-xl')
                        ui.label('全球节点实景 (Global View)').classes('text-base font-bold text-white')
                    DASHBOARD_REFS['map_info'] = ui.label('Live Rendering').classes('text-[10px] text-gray-400')

                globe_data_list = []
                seen_locations = set()
                total_server_count = len(SERVERS_CACHE)

                for s in SERVERS_CACHE:
                    lat, lon = None, None
                    if 'lat' in s:
                        lat, lon = s['lat'], s['lon']
                    else:
                        c = get_coords_from_name(s.get('name', ''))
                        if c:
                            lat, lon = c[0], c[1]
                    if lat:
                        k = (round(lat, 2), round(lon, 2))
                        if k not in seen_locations:
                            seen_locations.add(k)
                            flag = "📍"
                            try:
                                flag = detect_country_group(s['name']).split(' ')[0]
                            except:
                                pass
                            globe_data_list.append({'lat': lat, 'lon': lon, 'name': flag})

                json_data = json.dumps(globe_data_list, ensure_ascii=False)

                ui.html(GLOBE_STRUCTURE, sanitize=False).classes('w-full h-[650px] overflow-hidden')
                ui.run_javascript(f'window.DASHBOARD_DATA = {json_data};')
                ui.run_javascript(GLOBE_JS_LOGIC)
