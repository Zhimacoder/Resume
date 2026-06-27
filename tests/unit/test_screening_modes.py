"""
双模式（REQUIRE_USER_API_KEY true/false）行为单元测试

测试 main.py 在生产模式和本地模式下：
- /api/config/status 返回结构是否符合预期
- /api/config POST 在生产模式是否返回 403
- /api/screening 在生产模式缺 Key 时是否返回 400
"""

import sys
import os
import importlib

sys.path.insert(0, os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    'server'
))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client_factory(monkeypatch):
    """根据环境变量重新加载 main 模块并返回 TestClient"""
    def _make(require_user_api_key: bool):
        if require_user_api_key:
            monkeypatch.setenv('REQUIRE_USER_API_KEY', 'true')
        else:
            monkeypatch.setenv('REQUIRE_USER_API_KEY', 'false')

        if 'main' in sys.modules:
            del sys.modules['main']
        import main
        importlib.reload(main)
        return TestClient(main.app)
    return _make


class TestConfigStatusProductionMode:
    def test_returns_require_user_api_key_true(self, client_factory):
        client = client_factory(True)
        resp = client.get('/api/config/status')
        assert resp.status_code == 200
        data = resp.json()
        assert data['require_user_api_key'] is True
        assert data['is_config_valid'] is False
        assert 'current_model' in data

    def test_models_empty_in_production(self, client_factory):
        client = client_factory(True)
        data = client.get('/api/config/status').json()
        assert data['models'] == {}


class TestConfigStatusLocalMode:
    def test_returns_require_user_api_key_false(self, client_factory):
        client = client_factory(False)
        resp = client.get('/api/config/status')
        assert resp.status_code == 200
        data = resp.json()
        assert data['require_user_api_key'] is False


class TestConfigPostProductionMode:
    def test_post_returns_403(self, client_factory):
        client = client_factory(True)
        resp = client.post('/api/config', json={'current_model': 'deepseek', 'models': {}})
        assert resp.status_code == 403


class TestScreeningProductionMode:
    def test_missing_api_key_returns_400(self, client_factory, tmp_path):
        client = client_factory(True)
        fake_file = tmp_path / 'resume.txt'
        fake_file.write_text('hello')

        with open(fake_file, 'rb') as f:
            resp = client.post(
                '/api/screening',
                data={
                    'jd_content': 'JD 示例',
                },
                files={'files': ('resume.txt', f, 'text/plain')}
            )
        assert resp.status_code == 400

    def test_with_api_key_proceeds(self, client_factory, tmp_path):
        """提供 api_key 和 model_endpoint 后应通过参数校验（后续 LLM 调用会失败但不会 400）"""
        client = client_factory(True)
        fake_file = tmp_path / 'resume.txt'
        fake_file.write_text('hello world this is a resume')

        with open(fake_file, 'rb') as f:
            resp = client.post(
                '/api/screening',
                data={
                    'jd_content': 'JD 示例',
                    'api_key': 'fake-key',
                    'model_type': 'deepseek',
                    'model_endpoint': 'https://api.deepseek.com/chat/completions',
                    'model_name': 'deepseek-chat',
                },
                files={'files': ('resume.txt', f, 'text/plain')}
            )
        assert resp.status_code == 200
        data = resp.json()
        assert data['success'] is True
        assert data['model_used'] == 'deepseek'
        # 真实 LLM 调用会失败，errors 里应该有内容
        assert isinstance(data.get('errors', []), list)


class TestScreeningLocalMode:
    def test_missing_server_config_returns_400(self, client_factory, tmp_path, monkeypatch):
        """本地模式下，若服务器端配置无效，应返回 400"""
        client = client_factory(False)

        from config import DEFAULT_CONFIG
        # 强制 load_config 返回无效配置
        import config as config_module
        monkeypatch.setattr(config_module, 'load_config', lambda: DEFAULT_CONFIG.copy())

        # 重新 reload main 让它用新的 load_config
        if 'main' in sys.modules:
            del sys.modules['main']
        import main
        importlib.reload(main)
        monkeypatch.setattr(config_module, 'load_config', lambda: DEFAULT_CONFIG.copy())

        fake_file = tmp_path / 'resume.txt'
        fake_file.write_text('hello')
        with open(fake_file, 'rb') as f:
            resp = client.post(
                '/api/screening',
                data={'jd_content': 'JD'},
                files={'files': ('resume.txt', f, 'text/plain')}
            )
        assert resp.status_code == 400
