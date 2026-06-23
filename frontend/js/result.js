/**
 * 结果页（result.html）业务逻辑
 */

let resultsData = null;
let currentIndex = 0;

document.addEventListener('DOMContentLoaded', async function() {
    await GlobalState.init();
    initPage();
    bindEvents();
});

function initPage() {
    try {
        const data = sessionStorage.getItem('screening_results');
        resultsData = JSON.parse(data);
    } catch (e) {
        resultsData = null;
    }

    if (!resultsData || !resultsData.results || resultsData.results.length === 0) {
        Toast.warning('无筛选结果，请重新筛选');
        setTimeout(() => {
            window.location.href = '/app';
        }, 1500);
        return;
    }

    renderResultList();
    selectResult(0);
}

function bindEvents() {
    document.getElementById('btn-home').addEventListener('click', goHome);
    document.getElementById('btn-config').addEventListener('click', goConfig);
    document.getElementById('btn-export').addEventListener('click', exportExcel);
}

async function exportExcel() {
    if (!resultsData || !resultsData.results || resultsData.results.length === 0) {
        Toast.warning('没有可导出的数据');
        return;
    }

    const btn = document.getElementById('btn-export');
    btn.disabled = true;
    btn.textContent = '导出中...';

    try {
        const { blob, filename } = await API.exportExcel(resultsData.results);
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        Toast.success('导出成功');
    } catch (error) {
        Toast.error('导出失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '📊 导出 Excel';
    }
}

function renderResultList() {
    const container = document.getElementById('result-list');
    const results = resultsData.results;

    container.innerHTML = results.map((item, index) => {
        const score = item.score || 0;
        const scoreClass = score >= 75 ? 'score-high' : score >= 50 ? 'score-mid' : 'score-low';
        return `
        <div class="result-item ${index === currentIndex ? 'active' : ''}" data-index="${index}">
            <div class="name">📄 ${item.resume_name}</div>
            <div class="score ${scoreClass}">${score}分</div>
        </div>`;
    }).join('');

    container.querySelectorAll('.result-item').forEach(item => {
        item.addEventListener('click', function() {
            const index = parseInt(this.dataset.index);
            selectResult(index);
        });
    });
}

function selectResult(index) {
    currentIndex = index;
    const results = resultsData.results;
    const item = results[index];

    document.querySelectorAll('.result-item').forEach((el, i) => {
        el.classList.toggle('active', i === index);
    });

    renderDetail(item);
}

function renderDetail(item) {
    const container = document.getElementById('result-detail');

    const matchingPoints = item.matching_points || [];
    const shortcomings = item.shortcomings || [];
    const interviewQuestions = item.interview_questions || [];
    const score = item.score || 0;
    const scoreBarWidth = Math.min(score, 100);
    const scoreClass = score >= 75 ? 'score-high' : score >= 50 ? 'score-mid' : 'score-low';
    const scoreBarColor = score >= 75
        ? 'linear-gradient(135deg,#10b981,#059669)'
        : score >= 50
            ? 'linear-gradient(135deg,#f59e0b,#d97706)'
            : 'linear-gradient(135deg,#ef4444,#dc2626)';

    container.innerHTML = `
        <div class="detail-resume-name">
            📄 <span>${item.resume_name}</span>
        </div>

        <div class="detail-section">
            <div class="title">
                <span class="title-icon" style="background:#ede9fe;">📝</span>
                简历概述
            </div>
            <div class="summary-box">${item.summary || '暂无概述'}</div>
        </div>

        <div class="detail-section">
            <div class="title">
                <span class="title-icon" style="background:#d1fae5;">✅</span>
                与岗位的匹配点
            </div>
            <div class="content">
                ${matchingPoints.length > 0 ? `
                    <ul class="list-match">
                        ${matchingPoints.map(p => `<li data-icon="✓">${p}</li>`).join('')}
                    </ul>
                ` : '<span style="color:var(--text-muted)">暂无</span>'}
            </div>
        </div>

        <div class="detail-section">
            <div class="title">
                <span class="title-icon" style="background:#fee2e2;">⚠️</span>
                与岗位的不足点
            </div>
            <div class="content">
                ${shortcomings.length > 0 ? `
                    <ul class="list-gap">
                        ${shortcomings.map(s => `<li data-icon="✗">${s}</li>`).join('')}
                    </ul>
                ` : '<span style="color:var(--text-muted)">暂无</span>'}
            </div>
        </div>

        <div class="detail-section">
            <div class="title">
                <span class="title-icon" style="background:#eef0fe;">💬</span>
                建议面试问题
            </div>
            <div class="content">
                ${interviewQuestions.length > 0 ? `
                    <ul class="list-question">
                        ${interviewQuestions.map(q => `<li>${q}</li>`).join('')}
                    </ul>
                ` : '<span style="color:var(--text-muted)">暂无</span>'}
            </div>
        </div>

        <div class="detail-section">
            <div class="title">
                <span class="title-icon" style="background:#eef0fe;">🎯</span>
                匹配度评分
            </div>
            <div class="score-display">
                <span class="score-badge-large" style="background:${scoreBarColor};-webkit-background-clip:text;background-clip:text;">${score}</span>
                <div style="flex:1;">
                    <div class="score-bar-wrap">
                        <div class="score-bar" style="width:${scoreBarWidth}%;background:${scoreBarColor};"></div>
                    </div>
                    <div style="font-size:12px;color:var(--text-muted);margin-top:5px;">${score >= 75 ? '高度匹配' : score >= 50 ? '基本匹配' : '匹配度较低'}</div>
                </div>
            </div>
        </div>
    `;
}

function goHome() {
    sessionStorage.removeItem('screening_results');
    window.location.href = '/app';
}

function goConfig() {
    window.location.href = '/config';
}
