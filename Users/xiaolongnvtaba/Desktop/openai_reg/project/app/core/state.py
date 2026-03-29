import asyncio
import time


SERVERS_CACHE = []
SUBS_CACHE = []
NODES_DATA = {}
ADMIN_CONFIG = {}
GLOBAL_UI_VERSION = time.time()
PROCESS_POOL = None

IP_GEO_CACHE = {}

DASHBOARD_REFS = {
    'servers': None, 'nodes': None, 'traffic': None, 'subs': None,
    'bar_chart': None, 'pie_chart': None, 'stat_up': None, 'stat_down': None, 'stat_avg': None,
    'map': None, 'map_info': None,
}

DNS_CACHE = {}
DNS_WAITING_LABELS = {}

PROBE_DATA_CACHE = {}
PING_TREND_CACHE = {}

SYNC_SEMAPHORE = asyncio.Semaphore(50)
LAST_AUTO_SYNC_TIME = 0

EXPANDED_GROUPS = set()
SERVER_UI_MAP = {}

PING_CACHE = {}
CURRENT_PROBE_TAB = 'ALL'

REFRESH_LOCKS = set()
LAST_SYNC_MAP = {}

REFRESH_CURRENT_NODES = lambda: None

UI_ROW_REFS = {}
CURRENT_VIEW_STATE = {'scope': 'DASHBOARD', 'data': None}

SIDEBAR_UI_REFS = {
    'groups': {},
    'rows': {},
}

_current_dragged_group = None

ALERT_CACHE = {}
FAILURE_COUNTS = {}
