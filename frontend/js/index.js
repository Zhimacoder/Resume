/**
 * 主页（index.html）业务逻辑
 */

let uploadedFiles = [];

document.addEventListener('DOMContentLoaded', async function() {
    await GlobalState.init();
    initPage();
    bindEvents();
    GlobalState.addListener(handleStateChange);
});

function initPage() {
    initAgeSelects();
    updateAlertBanner();
    restoreFromCache();
    updateResultBanner();
}

const AGE_OPTIONS = [
    { value: '', label: '不限' },
    { value: '18', label: '18岁' },
    { value: '20', label: '20岁' },
    { value: '22', label: '22岁' },
    { value: '23', label: '23岁' },
    { value: '25', label: '25岁' },
    { value: '28', label: '28岁' },
    { value: '30', label: '30岁' },
    { value: '32', label: '32岁' },
    { value: '35', label: '35岁' },
    { value: '38', label: '38岁' },
    { value: '40', label: '40岁' },
    { value: '45', label: '45岁' },
    { value: '50', label: '50岁' },
    { value: '55', label: '55岁' },
    { value: '60', label: '60岁' }
];

function initAgeSelects() {
    const minSelect = document.getElementById('dim-age-min');
    const maxSelect = document.getElementById('dim-age-max');
    minSelect.innerHTML = '';
    maxSelect.innerHTML = '';
    AGE_OPTIONS.forEach(opt => {
        const o1 = document.createElement('option');
        o1.value = opt.value;
        o1.textContent = opt.value ? opt.label : '最小年龄（不限）';
        minSelect.appendChild(o1);
        const o2 = document.createElement('option');
        o2.value = opt.value;
        o2.textContent = opt.value ? opt.label : '最大年龄（不限）';
        maxSelect.appendChild(o2);
    });
}

function restoreFromCache() {
    const savedJD = CacheManager.getJD();
    if (savedJD) {
        document.getElementById('jd-input').value = savedJD;
    }

    const savedResumes = CacheManager.getResumeList();
    if (savedResumes && savedResumes.length > 0) {
        uploadedFiles = [];
        savedResumes.forEach(item => {
            const fileEntry = {
                name: item.file_name,
                size: item.file_size,
                type: item.file_type,
                fromCache: true,
                fileData: item.file_data || null
            };
            if (item._large_file) {
                fileEntry.isLargeFile = true;
            }
            uploadedFiles.push(fileEntry);
        });
        renderFileList();
    }

    const savedDimensions = CacheManager.getDimensions();
    if (savedDimensions) {
        if (savedDimensions.work_years) document.getElementById('dim-work-years').value = savedDimensions.work_years;
        if (savedDimensions.education) document.getElementById('dim-education').value = savedDimensions.education;
        if (savedDimensions.skill_weights) document.getElementById('dim-skill-weights').value = savedDimensions.skill_weights;
        if (savedDimensions.extra) document.getElementById('dim-extra').value = savedDimensions.extra;
        if (savedDimensions.age_min !== undefined && savedDimensions.age_min !== null) {
            document.getElementById('dim-age-min').value = String(savedDimensions.age_min);
        }
        if (savedDimensions.age_max !== undefined && savedDimensions.age_max !== null) {
            document.getElementById('dim-age-max').value = String(savedDimensions.age_max);
        }
    }
}

function bindEvents() {
    document.getElementById('btn-config').addEventListener('click', goToConfig);
    document.getElementById('btn-go-config').addEventListener('click', goToConfig);
    document.getElementById('btn-modal-config').addEventListener('click', goToConfig);

    document.getElementById('btn-cancel').addEventListener('click', closeModal);

    document.getElementById('btn-screening').addEventListener('click', handleScreening);

    document.getElementById('btn-clear').addEventListener('click', clearContent);

    document.getElementById('btn-view-result').addEventListener('click', function() {
        window.location.href = 'result';
    });

    document.getElementById('btn-dismiss-result').addEventListener('click', function() {
        CacheManager.dismissResultBanner();
        updateResultBanner();
    });

    initUploadArea();

    document.getElementById('btn-toggle-dimensions').addEventListener('click', function() {
        const panel = document.getElementById('dimensions-panel');
        const isHidden = panel.style.display === 'none';
        panel.style.display = isHidden ? 'block' : 'none';
        this.textContent = isHidden ? '收起设置' : '展开设置';
    });

    document.getElementById('jd-input').addEventListener('input', function() {
        CacheManager.saveJD(this.value);
    });

    ['dim-work-years', 'dim-education', 'dim-skill-weights', 'dim-extra'].forEach(function(id) {
        document.getElementById(id).addEventListener('input', saveDimensionsToCache);
    });

    document.getElementById('dim-age-min').addEventListener('change', function() {
        validateAgeRange();
        saveDimensionsToCache();
    });
    document.getElementById('dim-age-max').addEventListener('change', function() {
        validateAgeRange();
        saveDimensionsToCache();
    });
}

function validateAgeRange() {
    const minVal = document.getElementById('dim-age-min').value;
    const maxVal = document.getElementById('dim-age-max').value;
    if (minVal && maxVal && parseInt(minVal) > parseInt(maxVal)) {
        Toast.warning('最小年龄不能大于最大年龄');
        document.getElementById('dim-age-max').value = '';
    }
}

function initUploadArea() {
    const uploadArea = document.getElementById('upload-area');
    const fileInput = document.getElementById('file-input');

    uploadArea.addEventListener('click', function() {
        fileInput.click();
    });

    fileInput.addEventListener('change', function(e) {
        handleFiles(e.target.files);
        fileInput.value = '';
    });

    uploadArea.addEventListener('dragover', function(e) {
        e.preventDefault();
        uploadArea.classList.add('dragover');
    });

    uploadArea.addEventListener('dragleave', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
    });

    uploadArea.addEventListener('drop', function(e) {
        e.preventDefault();
        uploadArea.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
}

function handleFiles(files) {
    const validExtensions = ['.pdf', '.doc', '.docx', '.txt', '.rtf',
                             '.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp'];
    const maxFiles = 10;
    const maxSize = 10 * 1024 * 1024;

    for (let i = 0; i < files.length; i++) {
        const file = files[i];

        if (uploadedFiles.length >= maxFiles) {
            Toast.warning(`最多只能上传${maxFiles}份简历`);
            break;
        }

        const ext = '.' + file.name.split('.').pop().toLowerCase();
        if (!validExtensions.includes(ext)) {
            Toast.warning(`不支持的文件格式: ${file.name}`);
            continue;
        }

        if (file.size > maxSize) {
            Toast.warning(`文件过大: ${file.name} (最大10MB)`);
            continue;
        }

        const existing = uploadedFiles.find(f => f.name === file.name);
        if (existing) {
            if (existing.size === file.size) {
                Toast.warning(`文件可能重复: ${file.name}（文件名和大小均相同）`);
                continue;
            } else {
                const proceed = confirm(
                    `已存在同名文件 "${file.name}"，但文件大小不同（${(existing.size / 1024).toFixed(1)}KB vs ${(file.size / 1024).toFixed(1)}KB），是否继续添加？`
                );
                if (!proceed) continue;
            }
        }

        uploadedFiles.push(file);
    }

    renderFileList();
    saveToCache();
}

function renderFileList() {
    const container = document.getElementById('file-list');

    if (uploadedFiles.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = uploadedFiles.map((file, index) => `
        <div class="file-item">
            <span class="name">📄 ${file.name}</span>
            <span class="remove" data-index="${index}">✕</span>
        </div>
    `).join('');

    container.querySelectorAll('.remove').forEach(btn => {
        btn.addEventListener('click', function() {
            const index = parseInt(this.dataset.index);
            uploadedFiles.splice(index, 1);
            renderFileList();
            saveToCache();
        });
    });
}

async function saveToCache() {
    const jdContent = document.getElementById('jd-input').value;
    CacheManager.saveJD(jdContent);

    if (uploadedFiles.length > 0) {
        const cacheableFiles = [];
        for (const file of uploadedFiles) {
            if (file.fromCache && file.fileData) {
                cacheableFiles.push({
                    file_name: file.name,
                    file_size: file.size,
                    file_type: file.type,
                    file_data: file.fileData
                });
            } else {
                try {
                    const cacheable = await CacheManager.fileToCacheable(file);
                    cacheableFiles.push(cacheable);
                } catch (e) {
                    console.error('文件转换失败:', e);
                }
            }
        }
        CacheManager.saveResumeList(cacheableFiles);
    }
}

function clearContent() {
    if (!confirm('确定要清空所有内容吗？')) return;

    document.getElementById('jd-input').value = '';
    document.getElementById('dim-work-years').value = '';
    document.getElementById('dim-education').value = '';
    document.getElementById('dim-skill-weights').value = '';
    document.getElementById('dim-extra').value = '';
    document.getElementById('dim-age-min').value = '';
    document.getElementById('dim-age-max').value = '';
    uploadedFiles = [];
    renderFileList();
    CacheManager.clearAll();
    updateResultBanner();
    Toast.info('已清空所有内容');
}

function saveDimensionsToCache() {
    const ageMinVal = document.getElementById('dim-age-min').value;
    const ageMaxVal = document.getElementById('dim-age-max').value;
    const dimensions = {
        work_years: document.getElementById('dim-work-years').value.trim(),
        education: document.getElementById('dim-education').value.trim(),
        skill_weights: document.getElementById('dim-skill-weights').value.trim(),
        extra: document.getElementById('dim-extra').value.trim(),
        age_min: ageMinVal ? parseInt(ageMinVal) : null,
        age_max: ageMaxVal ? parseInt(ageMaxVal) : null
    };
    const hasAny = dimensions.work_years || dimensions.education || dimensions.skill_weights || dimensions.extra || dimensions.age_min || dimensions.age_max;
    CacheManager.saveDimensions(hasAny ? dimensions : null);
}

async function handleScreening() {
    const jdContent = document.getElementById('jd-input').value.trim();

    if (!jdContent) {
        Toast.warning('请输入岗位JD内容');
        return;
    }

    if (uploadedFiles.length === 0) {
        Toast.warning('请上传简历文件');
        return;
    }

    if (!GlobalState.isValid()) {
        showModal();
        return;
    }

    const workYears = document.getElementById('dim-work-years').value.trim();
    const education = document.getElementById('dim-education').value.trim();
    const skillWeights = document.getElementById('dim-skill-weights').value.trim();
    const extra = document.getElementById('dim-extra').value.trim();
    const ageMinVal = document.getElementById('dim-age-min').value;
    const ageMaxVal = document.getElementById('dim-age-max').value;
    const ageMin = ageMinVal ? parseInt(ageMinVal) : null;
    const ageMax = ageMaxVal ? parseInt(ageMaxVal) : null;
    const dimensions = (workYears || education || skillWeights || extra || ageMin || ageMax) ? {
        work_years: workYears,
        education: education,
        skill_weights: skillWeights,
        extra: extra,
        age_min: ageMin,
        age_max: ageMax
    } : null;

    const files = uploadedFiles.map(f => {
        if (f.fromCache && f.fileData) {
            return dataURLtoFile(f.fileData, f.name);
        }
        if (f.isLargeFile) {
            return null;
        }
        return f;
    }).filter(Boolean);

    const largeFiles = uploadedFiles.filter(f => f.isLargeFile);
    if (largeFiles.length > 0) {
        const names = largeFiles.map(f => f.name).join('、');
        Toast.warning(`以下文件因超过缓存大小限制（1MB），需要重新选择：${names}`);
        return;
    }

    showLoading(`正在分析 ${files.length} 份简历，请稍候...`);

    try {
        const response = await API.screening(jdContent, files, dimensions);

        if (response.success) {
            CacheManager.saveResults(response);
            CacheManager.saveDimensions(dimensions);
            window.location.href = 'result';
        } else {
            Toast.error('筛选失败: ' + (response.detail || '未知错误'));
        }
    } catch (error) {
        Toast.error('筛选失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

function dataURLtoFile(dataurl, filename) {
    const arr = dataurl.split(',');
    const mime = arr[0].match(/:(.*?);/)[1];
    const bstr = atob(arr[1]);
    let n = bstr.length;
    const u8arr = new Uint8Array(n);
    while (n--) {
        u8arr[n] = bstr.charCodeAt(n);
    }
    return new File([u8arr], filename, { type: mime });
}

function handleStateChange(state) {
    updateAlertBanner();
}

function updateAlertBanner() {
    const alertBanner = document.getElementById('alert-banner');
    const isValid = GlobalState.isValid();

    if (isValid) {
        alertBanner.classList.add('hidden');
    } else {
        alertBanner.classList.remove('hidden');
    }
}

function updateResultBanner() {
    const banner = document.getElementById('result-banner');
    const countEl = document.getElementById('result-count');

    if (CacheManager.hasResults() && !CacheManager.isResultBannerDismissed()) {
        const results = CacheManager.getResults();
        countEl.textContent = results.results.length;
        banner.classList.remove('hidden');
    } else {
        banner.classList.add('hidden');
    }
}

function goToConfig() {
    saveToCache();
    saveDimensionsToCache();
    window.location.href = 'config';
}

function showModal() {
    document.getElementById('modal-block').classList.add('active');
}

function closeModal() {
    document.getElementById('modal-block').classList.remove('active');
}

function showLoading(text) {
    document.getElementById('loading-text').textContent = text;
    document.getElementById('loading-overlay').classList.add('active');
}

function hideLoading() {
    document.getElementById('loading-overlay').classList.remove('active');
}
