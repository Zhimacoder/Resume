/**
 * 配置页（config.html）业务逻辑
 */

let configData = null;

const modelFields = {
    doubao:   { endpoint: 'doubao-endpoint',   key: 'doubao-key',   version: 'doubao-version'   },
    wenxin:   { endpoint: 'wenxin-endpoint',   key: 'wenxin-key',   secret: 'wenxin-secret', version: 'wenxin-version'   },
    qianwen:  { endpoint: 'qianwen-endpoint',  key: 'qianwen-key',  version: 'qianwen-version'  },
    zhipu:    { endpoint: 'zhipu-endpoint',    key: 'zhipu-key',    version: 'zhipu-version'    },
    minmax:   { endpoint: 'minmax-endpoint',   key: 'minmax-key',   version: 'minmax-version'   },
    deepseek: { endpoint: 'deepseek-endpoint', key: 'deepseek-key', version: 'deepseek-version' },
    custom: {
        name:     'custom-name',
        endpoint: 'custom-endpoint',
        key:      'custom-key',
        version:  'custom-version'
    }
};

const modelVersionCache = {};

document.addEventListener('DOMContentLoaded', async function() {
    await GlobalState.init();
    await loadConfig();
    bindEvents();
    updateBackButton();
});

function updateBackButton() {
    const params = new URLSearchParams(window.location.search);
    const from = params.get('from');
    const btn = document.getElementById('btn-home');
    if (from === 'result') {
        btn.textContent = '← 返回结果';
    } else {
        btn.textContent = '← 返回主页';
    }
}

async function loadConfig() {
    try {
        const userConfig = GlobalState.getUserConfig();
        if (userConfig) {
            configData = userConfig;
        } else {
            configData = {
                current_model: 'deepseek',
                models: {}
            };
        }
        fillFormData();
        updateStatus();
    } catch (error) {
        console.error('加载配置失败:', error);
        Toast.error('加载配置失败');
    }
}

function bindEvents() {
    document.getElementById('btn-home').addEventListener('click', goHome);
    document.getElementById('btn-save').addEventListener('click', saveConfig);
    document.getElementById('btn-clear-key').addEventListener('click', clearUserApiKey);

    // Tab 切换
    document.querySelectorAll('.model-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            switchModel(tab.dataset.model);
        });
    });
}

function switchModel(modelKey) {
    // 更新 Tab 高亮
    document.querySelectorAll('.model-tab').forEach(t => {
        t.classList.toggle('active', t.dataset.model === modelKey);
    });
    // 切换面板
    document.querySelectorAll('.model-panel').forEach(p => {
        p.classList.toggle('active', p.dataset.panel === modelKey);
    });
    // 同步隐藏的 select（config.js 内部读取用）
    document.getElementById('current-model-select').value = modelKey;
}

function fillFormData() {
    if (!configData) return;
    const currentModel = configData.current_model || 'deepseek';
    document.getElementById('current-model-select').value = currentModel;
    switchModel(currentModel);

    const models = configData.models || {};

    Object.keys(modelFields).forEach(modelKey => {
        const model = models[modelKey];
        if (!model) return;
        const fields = modelFields[modelKey];

        if (fields.name) {
            const el = document.getElementById(fields.name);
            if (el) el.value = model.model_name || '';
        }
        if (fields.endpoint) {
            const el = document.getElementById(fields.endpoint);
            if (el && el.type !== 'hidden') el.value = model.endpoint || '';
        }
        if (fields.key) {
            const el = document.getElementById(fields.key);
            if (el) {
                el.value = model.api_key || '';
                el.dataset.masked = model.api_key && model.api_key.indexOf('****') >= 0 ? '1' : '0';
            }
        }
        if (fields.secret) {
            const el = document.getElementById(fields.secret);
            if (el) {
                el.value = model.api_secret || '';
                el.dataset.masked = model.api_secret && model.api_secret.indexOf('****') >= 0 ? '1' : '0';
            }
        }
        if (fields.version && model.model_version) {
            const savedVersion = model.model_version;
            const versionEl = document.getElementById(fields.version);
            if (!versionEl) return;

            if (versionEl.tagName === 'SELECT') {
                versionEl.innerHTML = `<option value="${savedVersion}">${savedVersion}（已保存，点击「测试连通」可重新加载列表）</option>`;
                versionEl.value = savedVersion;
                versionEl.disabled = false;

                const hint = document.getElementById(modelKey + '-version-hint');
                if (hint) hint.textContent = '已加载已保存的模型版本，点击「测试连通」可刷新完整列表';
            } else {
                versionEl.value = savedVersion;
            }
        }
    });
}

function updateStatus() {
    const statusEl = document.getElementById('config-status');
    if (!statusEl) return;
    if (!configData) { statusEl.textContent = '加载失败'; return; }

    const currentModel = configData.current_model;
    const model = (configData.models || {})[currentModel];

    if (model && model.api_key && model.endpoint) {
        statusEl.innerHTML =
            '<span style="color:#10b981;">✓ 已配置</span> — ' +
            (model.model_name || currentModel) +
            (model.model_version ? `（${model.model_version}）` : '') +
            ' <span style="font-size:12px;color:var(--text-muted);">Key 已存在浏览器</span>';
    } else {
        statusEl.innerHTML = '<span style="color:#ef4444;">✕ 未配置</span> <span style="font-size:12px;color:var(--text-muted);">请填写并保存 API Key</span>';
    }
}

function populateVersionSelect(modelKey, models, savedVal) {
    const sel = document.getElementById(modelFields[modelKey].version);
    const hint = document.getElementById(modelKey + '-version-hint');
    if (!sel) return;

    sel.innerHTML = '<option value="">（不指定，使用平台默认）</option>';

    models.forEach(m => {
        const opt = document.createElement('option');
        opt.value = m;
        opt.textContent = m;
        sel.appendChild(opt);
    });

    if (savedVal && models.includes(savedVal)) {
        sel.value = savedVal;
    } else if (savedVal) {
        const opt = document.createElement('option');
        opt.value = savedVal;
        opt.textContent = savedVal + '（已保存）';
        sel.appendChild(opt);
        sel.value = savedVal;
    }

    sel.disabled = false;
    sel.classList.remove('loading');

    if (hint) hint.textContent = `已加载 ${models.length} 个可选模型版本`;
}

async function testModel(modelKey) {
    const fields = modelFields[modelKey];
    const resultEl = document.getElementById(modelKey + '-test-result');
    const versionEl = document.getElementById(fields.version);
    const hint = document.getElementById(modelKey + '-version-hint');

    const apiKey   = document.getElementById(fields.key).value.trim();
    const endpoint = document.getElementById(fields.endpoint).value.trim();
    const apiSecret = fields.secret ? document.getElementById(fields.secret).value.trim() : '';

    if (!apiKey) {
        resultEl.className = 'test-result err';
        resultEl.textContent = '请先填写 API Key';
        return;
    }
    if (!endpoint) {
        resultEl.className = 'test-result err';
        resultEl.textContent = '请先填写 Endpoint';
        return;
    }
    if (modelKey === 'wenxin' && !apiSecret) {
        resultEl.className = 'test-result err';
        resultEl.textContent = '请先填写 API Secret (SK)';
        return;
    }

    resultEl.className = 'test-result';
    resultEl.textContent = '测试中...';

    if (versionEl && versionEl.tagName === 'SELECT') {
        versionEl.disabled = true;
        versionEl.classList.add('loading');
        versionEl.innerHTML = '<option value="">正在加载模型列表...</option>';
        if (hint) hint.textContent = '正在拉取可用模型版本...';
    }

    const btn = document.querySelector(`button[onclick="testModel('${modelKey}')"]`);
    if (btn) btn.disabled = true;

    try {
        const res = await API.testConnection({
            model_type: modelKey,
            api_key: apiKey,
            endpoint: endpoint,
            model_name: '',
            api_secret: apiSecret
        });

        resultEl.className = 'test-result ' + (res.success ? 'ok' : 'err');
        resultEl.textContent = (res.success ? '✓ ' : '✕ ') + res.message;

        if (res.success && versionEl && versionEl.tagName === 'SELECT') {
            const models = Array.isArray(res.models) ? res.models : [];
            modelVersionCache[modelKey] = models;

            const savedVersion = (configData?.models?.[modelKey]?.model_version) || '';
            populateVersionSelect(modelKey, models, savedVersion);
        } else if (!res.success && versionEl && versionEl.tagName === 'SELECT') {
            versionEl.innerHTML = '<option value="">— 请先点击「测试连通」—</option>';
            versionEl.disabled = true;
            versionEl.classList.remove('loading');
            if (hint) hint.textContent = '填写 API Key 后点击「测试连通」，将自动加载可选模型版本';
        }

    } catch (err) {
        resultEl.className = 'test-result err';
        resultEl.textContent = '✕ 请求失败: ' + err.message;

        if (versionEl && versionEl.tagName === 'SELECT') {
            versionEl.innerHTML = '<option value="">— 请先点击「测试连通」—</option>';
            versionEl.disabled = true;
            versionEl.classList.remove('loading');
            if (hint) hint.textContent = '填写 API Key 后点击「测试连通」，将自动加载可选模型版本';
        }
    } finally {
        if (btn) btn.disabled = false;
    }
}

async function saveConfig() {
    const currentModel = document.getElementById('current-model-select').value;
    const fields = modelFields[currentModel];

    let apiKey = '', apiSecret = '', endpoint = '', modelName = '', modelVersion = '';

    if (currentModel === 'custom') {
        modelName    = document.getElementById('custom-name').value.trim();
        endpoint     = document.getElementById('custom-endpoint').value.trim();
        apiKey       = document.getElementById('custom-key').value.trim();
        modelVersion = document.getElementById('custom-version').value.trim();
    } else {
        endpoint     = document.getElementById(fields.endpoint).value.trim();
        apiKey       = document.getElementById(fields.key).value.trim();
        apiSecret    = fields.secret ? document.getElementById(fields.secret).value.trim() : '';
        modelName    = getModelDisplayName(currentModel);
        modelVersion = fields.version
            ? document.getElementById(fields.version).value.trim()
            : '';
    }

    if (!apiKey)    { Toast.warning('请输入 API Key'); return; }
    if (!endpoint)  { Toast.warning('请输入 API Endpoint'); return; }
    if (currentModel === 'wenxin' && !apiSecret) { Toast.warning('请输入 API Secret (SK)'); return; }
    if (currentModel === 'custom' && !modelName) { Toast.warning('请输入自定义模型名称'); return; }

    showLoading('正在保存...');
    try {
        const existingModels = (configData && configData.models) ? configData.models : {};
        const models = { ...existingModels };
        models[currentModel] = {
            model_name:    modelName,
            api_key:       apiKey,
            endpoint:      endpoint,
            model_version: modelVersion,
            is_valid:      true
        };
        if (apiSecret) {
            models[currentModel].api_secret = apiSecret;
        }

        const newConfig = { current_model: currentModel, models };
        const ok = GlobalState.saveUserConfig(newConfig);

        if (ok) {
            configData = GlobalState.getUserConfig() || newConfig;
            updateStatus();
            Toast.success('API Key 已保存到你的浏览器');
        } else {
            Toast.error('保存失败：浏览器 localStorage 写入异常');
        }
    } catch (error) {
        Toast.error('保存失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

function clearUserApiKey() {
    if (!confirm('确定要清除本浏览器中保存的 API Key 吗？此操作仅影响当前浏览器，不会影响其他设备。')) return;
    GlobalState.clearUserConfig();
    configData = { current_model: 'deepseek', models: {} };
    // 清空所有输入框
    document.querySelectorAll('.model-panel input:not([type="hidden"]), .model-panel select').forEach(el => {
        if (el.tagName === 'SELECT') {
            el.innerHTML = '<option value="">— 请先点击「测试连通」—</option>';
            el.disabled = true;
        } else {
            el.value = '';
        }
    });
    switchModel('deepseek');
    updateStatus();
    Toast.info('已清除本浏览器的 API Key 配置');
}

function getModelDisplayName(key) {
    return { doubao:'字节豆包', wenxin:'百度文心', qianwen:'阿里千问',
             zhipu:'智谱GLM', minmax:'MinMax', deepseek:'DeepSeek' }[key] || key;
}

function goHome() {
    const params = new URLSearchParams(window.location.search);
    const from = params.get('from');
    if (from === 'result') {
        window.location.href = 'result';
    } else {
        window.location.href = './';
    }
}

function showLoading(text) {
    document.getElementById('loading-text').textContent = text || '正在保存...';
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}

window.testModel = testModel;
