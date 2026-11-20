import sys
from uuid import uuid4
import pytest


@pytest.mark.skipif(sys.platform != 'darwin', reason='requires real macOS Keychain')
def test_keychain_roundtrip_and_update():
    from app.ai import macos_keychain
    account = 'test-' + uuid4().hex
    service = 'CodeTopLocal.Tests'
    try:
        assert macos_keychain.read(service, account) is None
        macos_keychain.write(service, account, '测试-secret')
        assert macos_keychain.read(service, account) == '测试-secret'
        macos_keychain.write(service, account, 'updated')
        assert macos_keychain.read(service, account) == 'updated'
    finally:
        macos_keychain.delete(service, account)
