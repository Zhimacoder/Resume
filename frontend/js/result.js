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
    resultsData = CacheManager.getResults();

    if (!resultsData || !resultsData.results || resultsData.results.length === 0) {
        Toast.warning('无筛选结果，请重新筛选');
        setTimeout(() => {
            window.location.href = '.';
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
        const ageTag = buildAgeTag(item.age_info);
        
        const matchCount = (item.matching_points || []).length;
        const shortCount = (item.shortcomings || []).length;
        let summaryText = item.summary || '暂无概述';
        if (summaryText.length > 60) {
            summaryText = summaryText.substring(0, 60) + '...';
        }
        
        return `
        <div class="result-item ${index === currentIndex ? 'active' : ''}" data-index="${index}">
            <div class="item-main">
                <div class="name-row">
                    <span class="name" title="${item.resume_name}">📄 ${item.resume_name}</span>
                    ${ageTag}
                </div>
                <div class="item-desc" title="${item.summary || '暂无概述'}">${summaryText}</div>
                <div class="item-tags">
                    <span class="mini-tag tag-match">✓ 匹配 ${matchCount}</span>
                    <span class="mini-tag tag-gap">! 不足 ${shortCount}</span>
                </div>
            </div>
            <div class="item-score-wrap">
                <div class="score ${scoreClass}">${score}分</div>
            </div>
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
    const scoreTone = score >= 75 ? 'high' : score >= 50 ? 'mid' : 'low';
    const scoreBarColor = score >= 75
        ? 'linear-gradient(135deg,#10b981,#059669)'
        : score >= 50
            ? 'linear-gradient(135deg,#f59e0b,#d97706)'
            : 'linear-gradient(135deg,#ef4444,#dc2626)';
    const ageTag = buildAgeTag(item.age_info);

    container.innerHTML = `
        <div class="detail-top">
            <div class="detail-title-block">
                <div class="detail-resume-name">
                    <span class="file-mark">📄</span>
                    <span>${item.resume_name}</span>
                    ${ageTag}
                </div>
                <div class="detail-summary-inline">${item.summary || '暂无概述'}</div>
            </div>
            <div class="score-card score-card-${scoreTone}">
                <div class="score-value" style="background:${scoreBarColor};-webkit-background-clip:text;background-clip:text;">${score}</div>
                <div class="score-label">${score >= 75 ? '高度匹配' : score >= 50 ? '基本匹配' : '匹配度较低'}</div>
                <div class="score-bar-wrap compact">
                    <div class="score-bar" style="width:${scoreBarWidth}%;background:${scoreBarColor};"></div>
                </div>
            </div>
        </div>

        <div class="detail-grid">
            <section class="detail-section section-match">
                <div class="title">
                    <span class="title-icon title-icon-match">✓</span>
                    匹配点
                    <span class="section-count">${matchingPoints.length}</span>
                </div>
                <div class="content">
                    ${matchingPoints.length > 0 ? `
                        <ul class="list-match compact-list">
                            ${matchingPoints.map(p => `<li data-icon="✓">${p}</li>`).join('')}
                        </ul>
                    ` : '<span style="color:var(--text-muted)">暂无</span>'}
                </div>
            </section>

            <section class="detail-section section-gap">
                <div class="title">
                    <span class="title-icon title-icon-gap">!</span>
                    不足点
                    <span class="section-count">${shortcomings.length}</span>
                </div>
                <div class="content">
                    ${shortcomings.length > 0 ? `
                        <ul class="list-gap compact-list">
                            ${shortcomings.map(s => `<li data-icon="!">${s}</li>`).join('')}
                        </ul>
                    ` : '<span style="color:var(--text-muted)">暂无</span>'}
                </div>
            </section>
        </div>

        <section class="detail-section section-questions">
            <div class="title">
                <span class="title-icon title-icon-question">?</span>
                建议面试问题
                <span class="section-count">${interviewQuestions.length}</span>
            </div>
            <div class="content">
                ${interviewQuestions.length > 0 ? `
                    <ul class="list-question question-grid">
                        ${interviewQuestions.map(q => {
                            let qText, qFocus;
                            if (typeof q === 'object' && q !== null) {
                                qText = q.question || '';
                                qFocus = q.focus || '';
                            } else {
                                qText = String(q);
                                qFocus = '';
                            }
                            return `
                                <li>
                                    <div class="question-item">
                                        <div class="question-text">${qText}</div>
                                        ${qFocus ? `<div class="question-focus">考察：${qFocus}</div>` : ''}
                                    </div>
                                </li>
                            `;
                        }).join('')}
                    </ul>
                ` : '<span style="color:var(--text-muted)">暂无</span>'}
            </div>
        </section>
    `;
}

function goHome() {
    window.location.href = '.';
}

function goConfig() {
    window.location.href = 'config?from=result';
}

function buildAgeTag(ageInfo) {
    if (!ageInfo) return '';
    const age = ageInfo.age;
    const inRange = ageInfo.in_range;

    if (age === null || age === undefined) {
        return '<span class="age-tag age-unknown" title="简历中未提供出生日期或身份证号，无法确定年龄">❓ 年龄未知</span>';
    }

    if (inRange === true) {
        return `<span class="age-tag age-match" title="年龄${age}岁，符合要求">✅ ${age}岁</span>`;
    } else if (inRange === false) {
        return `<span class="age-tag age-mismatch" title="年龄${age}岁，不符合年龄段要求">❌ ${age}岁</span>`;
    } else {
        return `<span class="age-tag age-neutral" title="未设置年龄段要求，年龄${age}岁">${age}岁</span>`;
    }
}
