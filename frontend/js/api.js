/**
 * 后端API调用模块
 */

const API = (function() {
    const BASE_URL = 'api';

    /**
     * 通用请求方法
     */
    async function request(endpoint, options = {}) {
        const url = BASE_URL + endpoint;
        const defaultOptions = {
            headers: {}
        };

        const mergedOptions = {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...options.headers
            }
        };

        try {
            const response = await fetch(url, mergedOptions);

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `请求失败: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API请求错误:', error);
            throw error;
        }
    }

    /**
     * 获取配置状态
     */
    async function getConfigStatus() {
        return request('/config/status');
    }

    /**
     * 获取完整配置
     */
    async function getConfig() {
        return request('/config');
    }

    /**
     * 保存配置
     */
    async function saveConfig(configData) {
        return request('/config', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(configData)
        });
    }

    /**
     * 测试API连通性
     * @param {Object} params - { model_type, api_key, endpoint, model_name }
     */
    async function testConnection(params) {
        return request('/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
    }

    /**
     * 智能筛选
     * @param {string} jdContent - JD内容
     * @param {File[]} files - 简历文件列表
     * @param {Object|null} dimensions - 自定义匹配维度（可选）
     *
     * 生产模式下会从 GlobalState.getUserConfig() 读取当前模型的 API Key 等字段，
     * 附加到 FormData 一起上传给后端。本地模式下这些字段后端会忽略。
     */
    async function screening(jdContent, files, dimensions) {
        const formData = new FormData();
        formData.append('jd_content', jdContent);

        files.forEach(file => {
            formData.append('files', file);
        });

        if (dimensions) {
            formData.append('dimensions', JSON.stringify(dimensions));
        }

        const userConfig = (window.GlobalState && GlobalState.getUserConfig()) || null;
        if (userConfig) {
            const currentModel = userConfig.current_model;
            const modelConfig = (userConfig.models || {})[currentModel] || {};
            if (modelConfig.api_key) formData.append('api_key', modelConfig.api_key);
            if (currentModel) formData.append('model_type', currentModel);
            if (modelConfig.endpoint) formData.append('model_endpoint', modelConfig.endpoint);
            if (modelConfig.model_version) formData.append('model_name', modelConfig.model_version);
            if (modelConfig.api_secret) formData.append('api_secret', modelConfig.api_secret);
        }

        return request('/screening', {
            method: 'POST',
            body: formData
        });
    }

    /**
     * 解析简历（预览）
     */
    async function parseResume(file) {
        const formData = new FormData();
        formData.append('file', file);

        return request('/parse-resume', {
            method: 'POST',
            body: formData
        });
    }

    /**
     * 导出筛选结果为Excel
     * @param {Array} results - 筛选结果数组
     * @returns {Blob} Excel文件流
     */
    async function exportExcel(results) {
        const response = await fetch(BASE_URL + '/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ results })
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.detail || `导出失败: ${response.status}`);
        }

        // 获取文件名
        const disposition = response.headers.get('Content-Disposition') || '';
        let filename = '简历筛选结果.xlsx';
        const match = disposition.match(/filename\*?=(?:UTF-8'')?([^;]+)/i);
        if (match) {
            try { filename = decodeURIComponent(match[1]); } catch (_) {}
        }

        const blob = await response.blob();
        return { blob, filename };
    }

    /**
     * 健康检查
     */
    async function healthCheck() {
        return request('/health');
    }

    // 导出接口
    return {
        getConfigStatus,
        getConfig,
        saveConfig,
        testConnection,
        screening,
        parseResume,
        exportExcel,
        healthCheck
    };
})();

// 导出到全局
window.API = API;
