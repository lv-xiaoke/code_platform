import pytest
from starlette.websockets import WebSocketDisconnect

from app.runtime import BrowserTabs


SOCKET = 'ws://127.0.0.1:8000/api/v1/browser-tab'
SAME_ORIGIN = {'Origin': 'http://127.0.0.1:8000'}

def test_manual_server_does_not_enable_browser_shutdown(env):
    client, _, _ = env
    with client.websocket_connect(SOCKET, headers=SAME_ORIGIN) as socket:
        assert socket.receive() == {'type': 'websocket.close', 'code': 1000, 'reason': ''}


def test_last_browser_tab_controls_idle_shutdown(env):
    client, app, _ = env
    clock = [0.0]
    tabs = BrowserTabs(clock=lambda: clock[0])
    app.state.browser_tabs = tabs

    assert not tabs.should_stop()
    with client.websocket_connect(SOCKET, headers=SAME_ORIGIN):
        with client.websocket_connect(SOCKET, headers=SAME_ORIGIN):
            clock[0] += 90
        clock[0] += 10
        assert not tabs.should_stop()

    assert not tabs.should_stop()
    clock[0] += 2
    with client.websocket_connect(SOCKET, headers=SAME_ORIGIN):
        clock[0] += 10
        assert not tabs.should_stop()

    clock[0] += 6
    assert tabs.should_stop()


def test_cross_origin_socket_cannot_keep_service_running(env):
    client, app, _ = env
    app.state.browser_tabs = BrowserTabs()
    with pytest.raises(WebSocketDisconnect) as refused:
        with client.websocket_connect(SOCKET, headers={'Origin': 'http://localhost:8123'}):
            pytest.fail('cross-origin tab connected')
    assert refused.value.code == 1008


def test_service_stops_if_initial_page_never_connects():
    clock = [0.0]
    tabs = BrowserTabs(clock=lambda: clock[0])
    assert not tabs.should_stop()
    clock[0] += 75
    assert tabs.should_stop()
