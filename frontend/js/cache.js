/**
 * 页面数据保活模块
 * 使用sessionStorage实现页面跳转时的数据缓存与回填
 */

const CacheManager = (function() {
    const CACHE_KEY = 'resume_screening_cache';
    const JD_KEY = 'jd_content';
    const RESUME_LIST_KEY = 'resume_list';
    const RESULTS_KEY = 'screening_results';
    const DIMENSIONS_KEY = 'screening_dimensions';
    const DISMISS_KEY = 'result_banner_dismissed';
    const MAX_CACHE_SIZE = 1 * 1024 * 1024; // 单文件缓存上限 1MB

    /**
     * 保存JD内容
     */
    function saveJD(jdContent) {
        const cache = getCache();
        cache.jd_content = jdContent;
        cache.cache_time = new Date().toISOString();
        saveCache(cache);
    }

    /**
     * 获取JD内容
     */
    function getJD() {
        const cache = getCache();
        return cache.jd_content || '';
    }

    /**
     * 保存简历文件列表（包含文件基本信息）
     */
    function saveResumeList(files) {
        const cache = getCache();
        cache.resume_list = files.map(file => ({
            file_name: file.file_name,
            file_size: file.file_size,
            file_type: file.file_type,
            file_data: file.file_data // base64编码的文件内容
        }));
        cache.cache_time = new Date().toISOString();
        saveCache(cache);
    }

    /**
     * 获取简历文件列表
     */
    function getResumeList() {
        const cache = getCache();
        return cache.resume_list || [];
    }

    /**
     * 清空JD和简历缓存
     */
    function clearCache() {
        sessionStorage.removeItem(CACHE_KEY);
    }

    /**
     * 清空所有会话数据（JD + 简历 + 结果 + 维度 + 横幅关闭状态）
     */
    function clearAll() {
        clearCache();
        clearResults();
        clearDimensions();
        sessionStorage.removeItem(DISMISS_KEY);
    }

    /**
     * 保存筛选结果
     */
    function saveResults(results) {
        try {
            sessionStorage.setItem(RESULTS_KEY, JSON.stringify(results));
            sessionStorage.removeItem(DISMISS_KEY);
        } catch (e) {
            console.error('保存结果失败:', e);
        }
    }

    /**
     * 获取筛选结果
     */
    function getResults() {
        try {
            const data = sessionStorage.getItem(RESULTS_KEY);
            return data ? JSON.parse(data) : null;
        } catch (e) {
            console.error('读取结果失败:', e);
            return null;
        }
    }

    /**
     * 是否存在有效筛选结果
     */
    function hasResults() {
        const r = getResults();
        return !!(r && r.results && r.results.length > 0);
    }

    /**
     * 清除筛选结果
     */
    function clearResults() {
        sessionStorage.removeItem(RESULTS_KEY);
    }

    /**
     * 保存筛选维度
     */
    function saveDimensions(dimensions) {
        try {
            sessionStorage.setItem(DIMENSIONS_KEY, JSON.stringify(dimensions || {}));
        } catch (e) {
            console.error('保存维度失败:', e);
        }
    }

    /**
     * 获取筛选维度
     */
    function getDimensions() {
        try {
            const data = sessionStorage.getItem(DIMENSIONS_KEY);
            return data ? JSON.parse(data) : {};
        } catch (e) {
            return {};
        }
    }

    /**
     * 清除筛选维度
     */
    function clearDimensions() {
        sessionStorage.removeItem(DIMENSIONS_KEY);
    }

    /**
     * 标记结果横幅为已关闭（本次会话内不再显示）
     */
    function dismissResultBanner() {
        sessionStorage.setItem(DISMISS_KEY, '1');
    }

    /**
     * 结果横幅是否被用户关闭
     */
    function isResultBannerDismissed() {
        return sessionStorage.getItem(DISMISS_KEY) === '1';
    }

    /**
     * 获取缓存对象
     */
    function getCache() {
        try {
            const data = sessionStorage.getItem(CACHE_KEY);
            return data ? JSON.parse(data) : {};
        } catch (e) {
            console.error('读取缓存失败:', e);
            return {};
        }
    }

    /**
     * 保存缓存对象
     */
    function saveCache(cache) {
        try {
            sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache));
        } catch (e) {
            console.error('保存缓存失败:', e);
        }
    }

    /**
     * 检查是否有缓存数据
     */
    function hasCache() {
        const cache = getCache();
        return !!(cache.jd_content || (cache.resume_list && cache.resume_list.length > 0));
    }

    /**
     * 获取缓存信息
     */
    function getCacheInfo() {
        const cache = getCache();
        return {
            has_jd: !!cache.jd_content,
            has_resumes: !!(cache.resume_list && cache.resume_list.length > 0),
            resume_count: cache.resume_list ? cache.resume_list.length : 0,
            cache_time: cache.cache_time
        };
    }

    /**
     * 将File对象转换为可缓存的对象
     * 超过 1MB 的文件仅缓存元信息，不存储 base64 内容
     */
    async function fileToCacheable(file) {
        return new Promise((resolve, reject) => {
            // 大文件仅缓存元信息
            if (file.size > MAX_CACHE_SIZE) {
                resolve({
                    file_name: file.name,
                    file_size: file.size,
                    file_type: file.type,
                    file_data: null,  // 大文件不存储 base64
                    _large_file: true
                });
                return;
            }

            const reader = new FileReader();
            reader.onload = function(e) {
                resolve({
                    file_name: file.name,
                    file_size: file.size,
                    file_type: file.type,
                    file_data: e.target.result // base64编码
                });
            };
            reader.onerror = function(e) {
                reject(e);
            };
            reader.readAsDataURL(file);
        });
    }

    /**
     * 从缓存数据还原File对象
     */
    function cacheToFiles(cacheList) {
        return cacheList.map(item => {
            // 将base64转换回blob
            const response = fetch(item.file_data);
            return response.then(res => res.blob()).then(blob => {
                const file = new File([blob], item.file_name, {
                    type: item.file_type
                });
                return file;
            });
        });
    }

    // 导出接口
    return {
        saveJD,
        getJD,
        saveResumeList,
        getResumeList,
        clearCache,
        clearAll,
        hasCache,
        getCacheInfo,
        fileToCacheable,
        cacheToFiles,
        saveResults,
        getResults,
        hasResults,
        clearResults,
        saveDimensions,
        getDimensions,
        clearDimensions,
        dismissResultBanner,
        isResultBannerDismissed
    };
})();

// 导出到全局
window.CacheManager = CacheManager;