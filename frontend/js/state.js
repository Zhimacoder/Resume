/**
 * 全局状态管理模块
 * 负责APIkey配置状态的校验和同步
 */

const GlobalState = (function() {
    let state = {
        is_config_valid: false,
        current_model: "doubao",
        models: {}
    };

    let listeners = [];

    /**
     * 初始化状态
     */
    async function init() {
        await checkConfigStatus();
        return state;
    }

    /**
     * 校验APIkey配置状态
     */
    async function checkConfigStatus() {
        try {
            const response = await fetch('/api/config/status');
            if (response.ok) {
                const data = await response.json();
                state.is_config_valid = data.is_config_valid;
                state.current_model = data.current_model;
                state.models = data.models;

                // 通知所有监听器
                notifyListeners();
                return data;
            }
        } catch (error) {
            console.error('获取配置状态失败:', error);
        }
        return state;
    }

    /**
     * 获取当前状态
     */
    function getState() {
        return { ...state };
    }

    /**
     * 获取当前模型配置
     */
    function getCurrentModelConfig() {
        const model = state.models[state.current_model];
        return model || null;
    }

    /**
     * 验证配置是否有效
     */
    function isValid() {
        if (!state.is_config_valid) return false;

        const model = state.models[state.current_model];
        if (!model) return false;

        return model.is_valid &&
               model.api_key &&
               model.endpoint;
    }

    /**
     * 添加状态监听器
     */
    function addListener(callback) {
        if (typeof callback === 'function') {
            listeners.push(callback);
        }
    }

    /**
     * 移除状态监听器
     */
    function removeListener(callback) {
        const index = listeners.indexOf(callback);
        if (index > -1) {
            listeners.splice(index, 1);
        }
    }

    /**
     * 通知所有监听器
     */
    function notifyListeners() {
        listeners.forEach(callback => {
            try {
                callback(state);
            } catch (error) {
                console.error('状态监听器执行错误:', error);
            }
        });
    }

    /**
     * 更新配置
     */
    async function saveConfig(config) {
        try {
            const response = await fetch('/api/config', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(config)
            });

            const data = await response.json();

            if (data.success) {
                // 更新本地状态
                await checkConfigStatus();
                return true;
            }
            return false;
        } catch (error) {
            console.error('保存配置失败:', error);
            return false;
        }
    }

    // 导出接口
    return {
        init,
        checkConfigStatus,
        getState,
        getCurrentModelConfig,
        isValid,
        addListener,
        removeListener,
        saveConfig
    };
})();

// 导出到全局
window.GlobalState = GlobalState;