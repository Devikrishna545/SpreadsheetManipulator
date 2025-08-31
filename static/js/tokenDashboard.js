// Token Usage Dashboard Module
let chartInstances = {};

const chartDefaults = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
        legend: {
            labels: {
                color: '#e0e0e0',
                font: {
                    family: "'Inter', -apple-system, BlinkMacSystemFont, sans-serif",
                    size: 12
                }
            }
        },
        tooltip: {
            backgroundColor: 'rgba(0, 0, 0, 0.8)',
            titleColor: '#00bfff',
            bodyColor: '#e0e0e0',
            borderColor: 'rgba(0, 191, 255, 0.3)',
            borderWidth: 1
        }
    },
    scales: {
        x: {
            ticks: {
                color: '#a0a0a0'
            },
            grid: {
                color: 'rgba(255, 255, 255, 0.1)'
            }
        },
        y: {
            ticks: {
                color: '#a0a0a0'
            },
            grid: {
                color: 'rgba(255, 255, 255, 0.1)'
            }
        }
    }
};

export async function initializeTokenDashboard() {
    console.log('🚀 Initializing Token Dashboard...');
    
    const modalElement = document.getElementById('mappingManagementModal');
    if (!modalElement) {
        console.warn('⚠️ Mapping management modal not found - dashboard may not be visible');
    }
    
    const dashboardContainer = document.getElementById('tokenUsageDashboard');
    if (!dashboardContainer) {
        console.error('❌ Token usage dashboard container not found!');
        return;
    }
    
    console.log('✅ Dashboard container found, proceeding with setup...');
    setupEventListeners();
    await loadTokenUsageData();
    console.log('🎉 Token Dashboard initialization completed!');
}

function setupEventListeners() {
    console.log('🔧 Setting up Token Dashboard event listeners...');
    const refreshBtn = document.getElementById('refreshTokenStatsBtn');
    if (refreshBtn) {
        console.log('✅ Refresh button found, attaching listener');
        
        refreshBtn.removeEventListener('click', refreshTokenUsageData);
        
        refreshBtn.addEventListener('click', async () => {
            await refreshTokenUsageData();
        });
    } else {
        console.warn('⚠️ Refresh button not found in DOM');
    }
}

async function loadTokenUsageData() {
    try {
        console.log('📡 Loading token usage data from backend...');
        showLoadingState();
        
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 10000);
        
        const response = await fetch('/token_usage_stats', {
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        if (!response.ok) {
            throw new Error(`Failed to fetch token usage data: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log('🔍 Token usage data received:', data);
        console.log('🔍 Recent activity from API:', data.recentActivity);
        console.log('🔍 Recent activity count:', data.recentActivity?.length);
        
        if (!data || typeof data !== 'object') {
            throw new Error('Invalid data structure received');
        }
        
        updateDashboard(data);
        
    } catch (error) {
        console.error('❌ Error loading token usage data:', error);
        
        const noDataState = {
            summary: {
                totalTokens: 0,
                totalCost: 0,
                totalBatchCommands: 0,
                avgTokensPerCommand: 0,
                tokensTrend: 0,
                costTrend: 0,
                batchTrend: 0,
                avgTrend: 0
            },
            tokenDistribution: {
                inputTokens: 0,
                outputTokens: 0
            },
            modelUsage: {
                models: []
            },
            costBreakdown: {
                categories: []
            },
            usageTimeline: {
                timeline: []
            },
            recentActivity: []
        };
        
        console.log('🔄 Showing "No Data" state due to error');
        updateDashboard(noDataState);
    }
}

async function refreshTokenUsageData() {
    const refreshBtn = document.getElementById('refreshTokenStatsBtn');
    if (!refreshBtn) {
        console.warn('⚠️ Refresh button not found during refresh operation');
        return;
    }
    
    const originalContent = refreshBtn.innerHTML;
    
    refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Refreshing...';
    refreshBtn.disabled = true;
    
    try {
        console.log('🔄 Starting refresh operation...');
        await loadTokenUsageData();
        console.log('✅ Refresh operation completed successfully');
    } catch (error) {
        console.error('❌ Error during refresh operation:', error);
    } finally {
        console.log('🔧 Restoring button state...');
        if (refreshBtn) {
            refreshBtn.innerHTML = originalContent;
            refreshBtn.disabled = false;
        }
    }
}

function updateDashboard(data) {
    console.log('📊 Updating dashboard with data:', data);
    
    const hasRealData = data.summary?.totalTokens > 0 || 
                       data.summary?.totalBatchCommands > 0 ||
                       (data.recentActivity && data.recentActivity.length > 0);
    
    const sampleDataBadge = document.getElementById('sampleDataBadge');
    if (sampleDataBadge) {
        const hasSampleData = data.summary?.totalTokens === 12000 && data.summary?.totalCost === 0.012;
        if (hasSampleData) {
            sampleDataBadge.style.display = 'inline-block';
            console.log('📋 Displaying sample data badge');
        } else {
            sampleDataBadge.style.display = 'none';
        }
    }
    
    console.log('🔍 Recent activity data before processing:', data.recentActivity);
    console.log('🔍 Has real data:', hasRealData);
    
    updateSummaryCards(data.summary);
    updateCharts(data, hasRealData);
    updateRecentActivity(data.recentActivity);
}

function updateSummaryCards(summary) {
    animateNumber('totalTokensUsed', summary.totalTokens || 0);
    animateNumber('totalCostEstimate', summary.totalCost || 0, true);
    animateNumber('totalBatchCommands', summary.totalBatchCommands || 0);
    animateNumber('avgTokensPerCommand', summary.avgTokensPerCommand || 0);
    
    updateTrend('tokensTrend', summary.tokensTrend || 0, 'tokens');
    updateTrend('costTrend', summary.costTrend || 0, 'cost');
    updateTrend('batchTrend', summary.batchTrend || 0, 'batch');
    updateTrend('avgTrend', summary.avgTrend || 0, 'avg');
}

function animateNumber(elementId, targetValue, isCurrency = false) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const startValue = 0;
    const duration = 1000;
    const startTime = Date.now();
    
    function updateNumber() {
        const currentTime = Date.now();
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        const easeProgress = 1 - Math.pow(1 - progress, 4);
        const currentValue = startValue + (targetValue - startValue) * easeProgress;
        
        if (isCurrency) {
            element.textContent = `$${currentValue.toFixed(6)}`;
        } else {
            element.textContent = Math.floor(currentValue).toLocaleString();
        }
        
        if (progress < 1) {
            requestAnimationFrame(updateNumber);
        } else {
            if (isCurrency) {
                element.textContent = `$${targetValue.toFixed(6)}`;
            } else {
                element.textContent = targetValue.toLocaleString();
            }
        }
    }
    
    updateNumber();
}

function updateTrend(elementId, trendValue, metricType = 'default') {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    const icon = element.querySelector('i');
    const span = element.querySelector('span');
    
    let isGoodTrend = false;
    
    switch (metricType) {
        case 'tokens':
            isGoodTrend = trendValue < 0;
            break;
        case 'cost':
            isGoodTrend = trendValue < 0;
            break;
        case 'batch':
            isGoodTrend = trendValue > 0;
            break;
        case 'avg':
            isGoodTrend = trendValue < 0;
            break;
        default:
            isGoodTrend = trendValue > 0;
            break;
    }
    
    if (trendValue > 0) {
        if (isGoodTrend) {
            icon.className = 'fas fa-arrow-up text-success';
        } else {
            icon.className = 'fas fa-arrow-down text-danger';
        }
        span.textContent = `+${trendValue}%`;
    } else if (trendValue < 0) {
        if (isGoodTrend) {
            icon.className = 'fas fa-arrow-up text-success';
        } else {
            icon.className = 'fas fa-arrow-down text-danger';
        }
        span.textContent = `${trendValue}%`;
    } else {
        icon.className = 'fas fa-minus text-warning';
        span.textContent = '0%';
    }
}

function updateCharts(data, hasRealData = true) {
    console.log('📊 Updating all charts with data...', 'Has real data:', hasRealData);
    
    hideLoadingState();
    
    try {
        updateTokenDistributionChart(data.tokenDistribution, hasRealData);
        updateModelUsageChart(data.modelUsage, hasRealData);
        updateCostBreakdownChart(data.costBreakdown, hasRealData);
        updateUsageTimelineChart(data.usageTimeline, hasRealData);
        
        console.log('✅ All charts updated successfully');
    } catch (error) {
        console.error('❌ Error updating charts:', error);
        hideLoadingState();
    }
}

function showNoDataMessage(canvasId, message = "No data available") {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const container = canvas.parentElement;
    if (!container) return;
    
    canvas.style.display = 'none';
    
    let noDataDiv = container.querySelector('.no-data-message');
    if (!noDataDiv) {
        noDataDiv = document.createElement('div');
        noDataDiv.className = 'no-data-message text-center text-muted py-4';
        container.appendChild(noDataDiv);
    }
    
    noDataDiv.innerHTML = `
        <i class="fas fa-chart-bar fa-2x mb-3 opacity-50"></i>
        <h6 class="mb-2">${message}</h6>
        <p class="mb-0 small">Execute commands to see data here</p>
    `;
    noDataDiv.style.display = 'block';
}

function hideNoDataMessage(canvasId) {
    const canvas = document.getElementById(canvasId);
    if (!canvas) return;
    
    const container = canvas.parentElement;
    if (!container) return;
    
    canvas.style.display = 'block';
    
    const noDataDiv = container.querySelector('.no-data-message');
    if (noDataDiv) {
        noDataDiv.style.display = 'none';
    }
}

function updateTokenDistributionChart(data, hasRealData = true) {
    try {
        const ctx = document.getElementById('tokenDistributionChart');
        if (!ctx) {
            console.warn('⚠️ Token distribution chart canvas not found');
            return;
        }
        
        if (chartInstances.tokenDistribution) {
            chartInstances.tokenDistribution.destroy();
        }
        
        const inputTokens = data?.inputTokens || 0;
        const outputTokens = data?.outputTokens || 0;
        
        if (!hasRealData || (inputTokens === 0 && outputTokens === 0)) {
            showNoDataMessage('tokenDistributionChart', 'No Token Distribution Data');
            return;
        }
        
        hideNoDataMessage('tokenDistributionChart');
        
        chartInstances.tokenDistribution = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: ['Input Tokens', 'Output Tokens'],
                datasets: [{
                    data: [inputTokens, outputTokens],
                    backgroundColor: [
                        'rgba(0, 191, 255, 0.8)',
                        'rgba(139, 69, 190, 0.8)'
                    ],
                    borderColor: [
                        'rgba(0, 191, 255, 1)',
                        'rgba(139, 69, 190, 1)'
                    ],
                    borderWidth: 2,
                    hoverOffset: 4
                }]
            },
            options: {
                ...chartDefaults,
                plugins: {
                    ...chartDefaults.plugins,
                    legend: {
                        ...chartDefaults.plugins.legend,
                        position: 'bottom'
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        });
        
        console.log('✅ Token distribution chart created successfully');
    } catch (error) {
        console.error('❌ Error creating token distribution chart:', error);
    }
}

function updateModelUsageChart(data, hasRealData = true) {
    try {
        const ctx = document.getElementById('modelUsageChart');
        if (!ctx) {
            console.warn('⚠️ Model usage chart canvas not found');
            return;
        }
        
        if (chartInstances.modelUsage) {
            chartInstances.modelUsage.destroy();
        }
        
        const models = data?.models || [];
        
        if (!hasRealData || models.length === 0) {
            showNoDataMessage('modelUsageChart', 'No Model Usage Data');
            return;
        }
        
        hideNoDataMessage('modelUsageChart');
        
        const colors = generateColors(models.length);

        let backgrounds = [...colors.background];
        let borders = [...colors.border];
        for (let i = 0; i < backgrounds.length; i++) {
            const label = models[i]?.name?.toLowerCase?.() || '';
            if (
                (label.includes('exp') || label.includes('purple') || label.includes('2.0')) ||
                (/hsl\(\s*([2][6-9][0-9]|3[0-1][0-9])/.test(backgrounds[i]))
            ) {
                backgrounds[i] = 'rgba(139, 69, 190, 0.8)';
                borders[i] = 'rgba(139, 69, 190, 1)';
            }
        }
        chartInstances.modelUsage = new Chart(ctx, {
            type: 'pie',
            data: {
                labels: models.map(m => m.name),
                datasets: [{
                    data: models.map(m => m.usage),
                    backgroundColor: backgrounds,
                    borderColor: borders,
                    borderWidth: 2,
                    hoverOffset: 4
                }]
            },
            options: {
                ...chartDefaults,
                plugins: {
                    ...chartDefaults.plugins,
                    legend: {
                        ...chartDefaults.plugins.legend,
                        position: 'bottom'
                    }
                },
                animation: {
                    animateRotate: true,
                    duration: 1000
                }
            }
        });
        
        console.log('✅ Model usage chart created successfully');
    } catch (error) {
        console.error('❌ Error creating model usage chart:', error);
    }
}

function updateCostBreakdownChart(data, hasRealData = true) {
    try {
        const ctx = document.getElementById('costBreakdownChart');
        if (!ctx) {
            console.warn('⚠️ Cost breakdown chart canvas not found');
            return;
        }
        
        if (chartInstances.costBreakdown) {
            chartInstances.costBreakdown.destroy();
        }
        
        const categories = data?.categories || [];
        
        if (!hasRealData || categories.length === 0 || categories.every(c => c.cost === 0)) {
            showNoDataMessage('costBreakdownChart', 'No Cost Breakdown Data');
            return;
        }
        
        hideNoDataMessage('costBreakdownChart');
        
        const colors = generateColors(categories.length);
        
        const inputData = categories.find(c => c.name === 'Input')?.cost || 0;
        const outputData = categories.find(c => c.name === 'Output')?.cost || 0;
        
        chartInstances.costBreakdown = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: ['Input', 'Output'],
                datasets: [
                    {
                        label: 'Input',
                        data: [inputData, 0],
                        backgroundColor: 'rgba(139, 69, 190, 0.8)',
                        borderColor: 'rgba(139, 69, 190, 1)',
                        borderWidth: 1,
                        borderRadius: 4,
                        borderSkipped: false,
                        barPercentage: 1.0,
                        categoryPercentage: 1.0,
                        grouped: false,
                        maxBarThickness: 90
                    },
                    {
                        label: 'Output',
                        data: [0, outputData],
                        backgroundColor: 'rgba(0, 191, 255, 0.8)',
                        borderColor: 'rgba(0, 191, 255, 1)',
                        borderWidth: 1,
                        borderRadius: 4,
                        borderSkipped: false,
                        barPercentage: 1.0,
                        categoryPercentage: 1.0,
                        grouped: false,
                        maxBarThickness: 90
                    }
                ]
            },
            options: {
                ...chartDefaults,
                indexAxis: 'x',
                plugins: {
                    ...chartDefaults.plugins,
                    legend: {
                        ...chartDefaults.plugins.legend,
                        position: 'bottom',
                        onClick: (e, legendItem, legend) => {
                            const chart = legend.chart;
                            const datasetIndex = legendItem.datasetIndex;
                            const meta = chart.getDatasetMeta(datasetIndex);
                            meta.hidden = meta.hidden === null ? !chart.data.datasets[datasetIndex].hidden : null;
                            chart.update();
                        }
                    }
                },
                scales: {
                    ...chartDefaults.scales,
                    x: {
                        ...chartDefaults.scales.x,
                        offset: true,
                    },
                    y: {
                        ...chartDefaults.scales.y,
                        beginAtZero: true,
                        ticks: {
                            ...chartDefaults.scales.y.ticks,
                            callback: function(value) {
                                return '$' + value.toFixed(6);
                            }
                        }
                    }
                },
                animation: {
                    duration: 1000,
                    easing: 'easeOutQuart'
                }
            }
        });
        
        console.log('✅ Cost breakdown chart created successfully');
    } catch (error) {
        console.error('❌ Error creating cost breakdown chart:', error);
    }
}

function updateUsageTimelineChart(data, hasRealData = true) {
    try {
        const ctx = document.getElementById('usageTimelineChart');
        if (!ctx) {
            console.warn('⚠️ Usage timeline chart canvas not found');
            return;
        }
        
        if (chartInstances.usageTimeline) {
            chartInstances.usageTimeline.destroy();
        }
        
        const timelineData = data?.timeline || [];
        
        if (!hasRealData || timelineData.length === 0 || timelineData.every(d => d.tokens === 0 && d.cost === 0)) {
            showNoDataMessage('usageTimelineChart', 'No Usage Timeline Data');
            return;
        }
        
        hideNoDataMessage('usageTimelineChart');
        
        chartInstances.usageTimeline = new Chart(ctx, {
            type: 'line',
            data: {
                labels: timelineData.map(d => d.date),
                datasets: [
                    {
                        label: 'Tokens Used',
                        data: timelineData.map(d => d.tokens),
                        borderColor: 'rgba(0, 191, 255, 1)',
                        backgroundColor: 'rgba(0, 191, 255, 0.1)',
                        borderWidth: 3,
                        fill: true,
                        tension: 0.4,
                        pointBackgroundColor: 'rgba(0, 191, 255, 1)',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 5,
                        pointHoverRadius: 8
                    },
                    {
                        label: 'Cost ($)',
                        data: timelineData.map(d => d.cost * 1000),
                        borderColor: 'rgba(139, 69, 190, 1)',
                        backgroundColor: 'rgba(255, 193, 7, 0.1)',
                        borderWidth: 2,
                        fill: false,
                        tension: 0.4,
                        pointBackgroundColor: 'rgba(139, 69, 190, 0.8)',
                        pointBorderColor: '#ffffff',
                        pointBorderWidth: 2,
                        pointRadius: 4,
                        pointHoverRadius: 7,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                ...chartDefaults,
                plugins: {
                    ...chartDefaults.plugins,
                    legend: {
                        ...chartDefaults.plugins.legend,
                        position: 'bottom'
                    }
                },
                layout: {
                    padding: {
                        bottom: 50
                    }
                },
                scales: {
                    ...chartDefaults.scales,
                    x: {
                        ...chartDefaults.scales.x,
                        ticks: {
                            ...chartDefaults.scales.x.ticks,
                            maxRotation: 0,
                            padding: 10
                        }
                    },
                    y: {
                        ...chartDefaults.scales.y,
                        type: 'linear',
                        display: true,
                        position: 'left',
                        beginAtZero: true
                    },
                    y1: {
                        ...chartDefaults.scales.y,
                        type: 'linear',
                        display: true,
                        position: 'right',
                        beginAtZero: true,
                        grid: {
                            drawOnChartArea: false,
                        },
                        ticks: {
                            ...chartDefaults.scales.y.ticks,
                            callback: function(value) {
                                return '$' + (value / 1000).toFixed(6);
                            }
                        }
                    }
                },
                animation: {
                    duration: 1500,
                    easing: 'easeOutQuart'
                }
            }
        });
        
        console.log('✅ Usage timeline chart created successfully');
    } catch (error) {
        console.error('❌ Error creating usage timeline chart:', error);
    }
}

function updateRecentActivity(activities) {
    console.log('🔄 Updating recent activity with data:', activities);
    console.log('🔍 Activity data type:', typeof activities);
    console.log('🔍 Activity array check:', Array.isArray(activities));
    
    const container = document.getElementById('recentActivityList');
    if (!container) {
        console.error('❌ Recent activity container not found!');
        return;
    }
    
    container.innerHTML = '';
    
    if (!activities || activities.length === 0) {
        console.log('✅ No batch activities found - showing empty state message');
        container.innerHTML = `
            <div class="text-center text-muted py-4">
                <i class="fas fa-history fa-2x mb-3 opacity-50"></i>
                <h6 class="mb-2">No Recent Batch Activity</h6>
                <p class="mb-0 small">Execute batch commands to see activity here</p>
            </div>
        `;
        return;
    }
    
    console.log(`✅ Processing ${activities.length} real batch activities`);
    
    activities.forEach((activity, index) => {
        console.log(`📝 Creating activity item ${index + 1}:`, {
            batchName: activity.batchName,
            commandCount: activity.commandCount,
            tokens: activity.tokens,
            timestamp: activity.timestamp
        });
        
        const activityElement = createActivityItem(activity, index);
        if (activityElement) {
            container.appendChild(activityElement);
            console.log(`✅ Activity item ${index + 1} added to container`);
        } else {
            console.error(`❌ Failed to create activity item ${index + 1}`);
        }
    });
    
    console.log(`🎉 Recent activity update completed - ${container.children.length} items in container`);
}

function createActivityItem(activity, index) {
    const div = document.createElement('div');
    div.className = 'activity-item';
    div.style.animationDelay = `${index * 0.1}s`;
    
    div.innerHTML = `
        <div class="activity-icon">
            <i class="fas fa-layer-group"></i>
        </div>
        <div class="activity-content">
            <div class="activity-details">
                <div class="fw-bold">${activity.batchName || 'Batch Command'}</div>
                <div class="activity-meta">
                    ${formatDate(activity.timestamp)} • ${activity.commandCount} commands
                </div>
            </div>
            <div class="activity-stats">
                <div class="activity-stat">
                    <div class="activity-stat-value">${activity.tokens.toLocaleString()}</div>
                    <div class="activity-stat-label">Tokens</div>
                </div>
                <div class="activity-stat">
                    <div class="activity-stat-value">$${activity.cost.toFixed(6)}</div>
                    <div class="activity-stat-label">Cost</div>
                </div>
                <div class="activity-stat">
                    <div class="activity-stat-value">${activity.model}</div>
                    <div class="activity-stat-label">Model</div>
                </div>
            </div>
        </div>
    `;
    
    return div;
}

function showLoadingState() {
    console.log('🔄 Showing loading state for charts...');
    const chartContainers = [
        'tokenDistributionChart',
        'modelUsageChart',
        'costBreakdownChart',
        'usageTimelineChart'
    ];
    
    chartContainers.forEach(id => {
        const canvas = document.getElementById(id);
        if (canvas && canvas.parentElement) {
            const wrapper = canvas.parentElement;
            
            const existingOverlay = wrapper.querySelector('.chart-loading-overlay');
            if (existingOverlay) {
                existingOverlay.remove();
            }
            
            const loadingOverlay = document.createElement('div');
            loadingOverlay.className = 'chart-loading-overlay';
            loadingOverlay.innerHTML = `
                <div class="chart-loading">
                    <div class="chart-loading-spinner"></div>
                    <div class="chart-loading-text">Loading chart data...</div>
                </div>
            `;
            
            wrapper.style.position = 'relative';
            wrapper.appendChild(loadingOverlay);
            console.log(`✅ Added loading overlay to ${id}`);
        } else {
            console.warn(`⚠️ Chart container not found: ${id}`);
        }
    });
}

function hideLoadingState() {
    console.log('✨ Hiding loading state for charts...');
    const chartContainers = [
        'tokenDistributionChart',
        'modelUsageChart',
        'costBreakdownChart',
        'usageTimelineChart'
    ];
    
    chartContainers.forEach(id => {
        const canvas = document.getElementById(id);
        if (canvas && canvas.parentElement) {
            const wrapper = canvas.parentElement;
            const loadingOverlay = wrapper.querySelector('.chart-loading-overlay');
            if (loadingOverlay) {
                loadingOverlay.remove();
                console.log(`✅ Removed loading overlay from ${id}`);
            }
        }
    });
}

function showErrorState() {
    const summaryCards = ['totalTokensUsed', 'totalCostEstimate', 'totalBatchCommands', 'avgTokensPerCommand'];
    summaryCards.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.textContent = 'Error';
        }
    });
    
    const recentActivityList = document.getElementById('recentActivityList');
    if (recentActivityList) {
        recentActivityList.innerHTML = `
            <div class="text-center text-danger py-3">
                <i class="fas fa-exclamation-triangle"></i>
                <p class="mb-0 mt-2">Failed to load token usage data</p>
            </div>
        `;
    }
}

function generateColors(count) {
    const baseHue = 195;
    const colors = {
        background: [],
        border: []
    };
    
    for (let i = 0; i < count; i++) {
        const hue = (baseHue + (i * 60)) % 360;
        const saturation = 70 + (i * 10) % 30;
        const lightness = 50 + (i * 15) % 30;
        
        colors.background.push(`hsla(${hue}, ${saturation}%, ${lightness}%, 0.6)`);
        colors.border.push(`hsla(${hue}, ${saturation}%, ${lightness}%, 1)`);
    }
    
    return colors;
}

function formatDate(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diffInMinutes = Math.floor((now - date) / (1000 * 60));
    
    if (diffInMinutes < 1) {
        return 'Just now';
    } else if (diffInMinutes < 60) {
        return `${diffInMinutes} minutes ago`;
    } else if (diffInMinutes < 1440) {
        const hours = Math.floor(diffInMinutes / 60);
        return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    } else {
        return date.toLocaleDateString();
    }
}

export function cleanupTokenDashboard() {
    Object.values(chartInstances).forEach(chart => {
        if (chart) {
            chart.destroy();
        }
    });
    chartInstances = {};
}

export function getCurrentTokenSummary() {
    return {
        totalTokens: parseInt(document.getElementById('totalTokensUsed')?.textContent?.replace(/,/g, '') || '0'),
        totalCost: parseFloat(document.getElementById('totalCostEstimate')?.textContent?.replace('$', '') || '0'),
        batchCommands: parseInt(document.getElementById('totalBatchCommands')?.textContent?.replace(/,/g, '') || '0'),
        avgTokens: parseInt(document.getElementById('avgTokensPerCommand')?.textContent?.replace(/,/g, '') || '0')
    };
}
