import os
import pytest


def test_macos_credentials_are_scoped_and_not_written_to_files(tmp_path, monkeypatch):
    from app import platforms
    from app.ai import secrets, macos_keychain
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    saved = {}
    monkeypatch.setattr(macos_keychain, 'read', lambda s, a: saved.get((s, a)))
    monkeypatch.setattr(macos_keychain, 'write', lambda s, a, v: saved.__setitem__((s, a), v))
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    first, second = secrets.KeyStore(tmp_path / '甲'), secrets.KeyStore(tmp_path / '乙')
    first.write('sk-unit-test')
    assert first.read() == 'sk-unit-test'
    assert second.read() == ''
    assert not list(tmp_path.rglob('*'))
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'environment-key')
    assert second.read() == 'environment-key'
    assert first.read() == 'sk-unit-test'


def test_denied_keychain_never_falls_back_or_echoes_key(tmp_path, monkeypatch):
    from app import platforms
    from app.ai import secrets, macos_keychain
    monkeypatch.setattr(platforms, 'system_name', lambda: 'macos')
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'environment-key')
    def denied(*args):
        raise ValueError('钥匙串访问被拒绝')
    monkeypatch.setattr(macos_keychain, 'read', denied)
    monkeypatch.setattr(macos_keychain, 'write', denied)
    store = secrets.KeyStore(tmp_path)
    with pytest.raises(ValueError, match='钥匙串'):
        store.read()
    with pytest.raises(ValueError, match='钥匙串') as exc:
        store.write('sk-never-echo-this')
    assert 'sk-never-echo-this' not in str(exc.value)
    assert not list(tmp_path.rglob('*'))


@pytest.mark.skipif(os.name == 'nt', reason='POSIX credential file backend')
def test_posix_credentials_use_user_only_file(tmp_path, monkeypatch):
    from app import platforms
    from app.ai import secrets
    monkeypatch.setattr(platforms, 'system_name', lambda: 'unsupported')
    monkeypatch.delenv('DEEPSEEK_API_KEY', raising=False)
    store = secrets.KeyStore(tmp_path)
    assert store.read() == ''
    store.write('sk-unit-test')
    assert store.read() == 'sk-unit-test'
    path = tmp_path/'ai-key.local'
    assert (path.stat().st_mode & 0o777) == 0o600
    assert not (tmp_path/'ai-key.dpapi').exists()
    monkeypatch.setenv('DEEPSEEK_API_KEY', 'environment-key')
    assert store.read() == 'sk-unit-test'
    assert secrets.KeyStore(tmp_path/'fresh').read() == 'environment-key'
