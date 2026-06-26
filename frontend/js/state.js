/**
 * 全局状态管理模块
 * 负责APIkey配置状态的校验和同步
 *
 * 支持两种模式（由后端 /api/config/status 的 require_user_api_key 字段决定）：
 * - 生产模式（require_user_api_key=true）：API Key 存浏览器 localStorage，
 *   调用 /api/screening 时随请求上传，后端不持久化
 * - 本地模式（require_user_api_key=false）：沿用服务器端配置（load_config）
 */

const STORAGE_KEY = 'resume_screening_user_api_key';

const UserConfigStore = {
    load() {
        try {
            const raw = localStorage.getItem(STORAGE_KEY);
            return raw ? JSON.parse(raw) : null;
        } catch (e) {
            console.error('读取用户 API Key 配置失败:', e);
            return null;
        }
    },
    save(config) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
            return true;
        } catch (e) {
            console.error('保存用户 API Key 配置失败:', e);
            return false;
        }
    },
    clear() {
        localStorage.removeItem(STORAGE_KEY);
    }
};


function _isUserConfigValid(config) {
    if (!config) return false;
    const currentModel = config.current_model;
    if (!currentModel) return false;
    const model = (config.models || {})[currentModel];
    if (!model) return false;
    if (!model.api_key || !model.endpoint) return false;
    return true;
}


const GlobalState = (function() {
    let state = {
        is_config_valid: false,
        current_model: "deepseek",
        models: {},
        require_user_api_key: false
    };

    let listeners = [];

    async function init() {
        await checkConfigStatus();
        return state;
    }

    async function checkConfigStatus() {
        try {
            const response = await fetch('api/config/status');
            if (response.ok) {
                const data = await response.json();
                state.require_user_api_key = !!data.require_user_api_key;

                if (state.require_user_api_key) {
                    const userConfig = UserConfigStore.load();
                    state.current_model = (userConfig && userConfig.current_model) || 'deepseek';
                    state.models = (userConfig && userConfig.models) || {};
                    state.is_config_valid = _isUserConfigValid(userConfig);
                } else {
                    state.is_config_valid = data.is_config_valid;
                    state.current_model = data.current_model;
                    state.models = data.models;
                }

                notifyListeners();
                return data;
            }
        } catch (error) {
            console.error('获取配置状态失败:', error);
        }
        return state;
    }

    function getState() {
        return { ...state };
    }

    function getCurrentModelConfig() {
        const model = state.models[state.current_model];
        return model || null;
    }

    function isValid() {
        if (state.require_user_api_key) {
            const userConfig = UserConfigStore.load();
            return _isUserConfigValid(userConfig);
        }

        if (!state.is_config_valid) return false;

        const model = state.models[state.current_model];
        if (!model) return false;

        return model.is_valid &&
               model.has_api_key &&
               model.endpoint;
    }

    function getUserConfig() {
        return UserConfigStore.load();
    }

    function saveUserConfig(config) {
        const ok = UserConfigStore.save(config);
        if (ok) {
            const userConfig = UserConfigStore.load();
            state.current_model = (userConfig && userConfig.current_model) || 'deepseek';
            state.models = (userConfig && userConfig.models) || {};
            state.is_config_valid = _isUserConfigValid(userConfig);
            notifyListeners();
        }
        return ok;
    }

    function clearUserConfig() {
        UserConfigStore.clear();
        state.models = {};
        state.is_config_valid = false;
        notifyListeners();
    }

    function addListener(callback) {
        if (typeof callback === 'function') {
            listeners.push(callback);
        }
    }

    function removeListener(callback) {
        const index = listeners.indexOf(callback);
        if (index > -1) {
            listeners.splice(index, 1);
        }
    }

    function notifyListeners() {
        listeners.forEach(callback => {
            try {
                callback(state);
            } catch (error) {
                console.error('状态监听器执行错误:', error);
            }
        });
    }

    async function saveConfig(config) {
        try {
            const response = await fetch('api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            const data = await response.json();

            if (data.success) {
                await checkConfigStatus();
                return true;
            }
            return false;
        } catch (error) {
            console.error('保存配置失败:', error);
            return false;
        }
    }

    return {
        init,
        checkConfigStatus,
        getState,
        getCurrentModelConfig,
        isValid,
        addListener,
        removeListener,
        saveConfig,
        getUserConfig,
        saveUserConfig,
        clearUserConfig
    };
})();

window.GlobalState = GlobalState;
window.UserConfigStore = UserConfigStore;
