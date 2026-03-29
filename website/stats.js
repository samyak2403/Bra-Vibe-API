// stats.js - Logic for the statistics dashboard
const ALL_DEALS_API = '../data/all_bras.json';
const PREMIUM_DEALS_API = '../data/premium_bras.json';

document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
});

async function initDashboard() {
    try {
        const [allRes, premiumRes] = await Promise.all([
            fetch(ALL_DEALS_API).catch(() => null),
            fetch(PREMIUM_DEALS_API).catch(() => null)
        ]);

        let allDeals = [];
        let premiumDeals = [];
        let lastUpdated = null;
        
        if (allRes && allRes.ok) {
            const data = await allRes.json();
            allDeals = data.deals || [];
            lastUpdated = data.metadata ? data.metadata.timestamp : null;
        }

        if (premiumRes && premiumRes.ok) {
            const data = await premiumRes.json();
            premiumDeals = data.deals || [];
        }

        const combinedDeals = [...allDeals];
        
        updateMetrics(combinedDeals, premiumDeals, lastUpdated);
        renderCharts(combinedDeals);

    } catch (err) {
        console.error("Failed to initialize dashboard:", err);
    }
}

function updateMetrics(allDeals, premiumDeals, lastUpdated) {
    const totalCount = document.getElementById('total-count');
    const sourceCount = document.getElementById('source-count');
    const premiumPerc = document.getElementById('premium-perc');
    const lastUpdate = document.getElementById('last-update');

    const total = allDeals.length;
    const sources = [...new Set(allDeals.map(d => d.website_source))].length;
    const premiumRatio = total > 0 ? Math.round((premiumDeals.length / total) * 100) : 0;

    animateValue(totalCount, 0, total, 1000);
    animateValue(sourceCount, 0, sources, 1000);
    animateValue(premiumPerc, 0, premiumRatio, 1000, '%');

    if (lastUpdated) {
        const date = new Date(lastUpdated);
        lastUpdate.innerText = "Every 5m";
        lastUpdate.style.fontSize = "1.5rem";
        lastUpdate.title = "Last Sync: " + date.toLocaleString();
    } else {
        lastUpdate.innerText = "5m Scan";
    }
}

function animateValue(obj, start, end, duration, suffix = '') {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        obj.innerText = Math.floor(progress * (end - start) + start) + suffix;
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function renderCharts(deals) {
    // 1. Store Distribution
    const storeStats = {};
    deals.forEach(d => {
        const s = d.website_source || 'Unknown';
        storeStats[s] = (storeStats[s] || 0) + 1;
    });

    const storeCtx = document.getElementById('storeChart').getContext('2d');
    new Chart(storeCtx, {
        type: 'doughnut',
        data: {
            labels: Object.keys(storeStats),
            datasets: [{
                data: Object.values(storeStats),
                backgroundColor: ['#ec4899', '#8b5cf6', '#3b82f6', '#10b981', '#f59e0b', '#ef4444'],
                borderWidth: 0,
                hoverOffset: 15
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'Inter', size: 10 }, usePointStyle: true, padding: 20 }
                }
            }
        }
    });

    // 2. Category Breakdown
    const catStats = {};
    deals.forEach(d => {
        const c = d.category || 'Bras';
        catStats[c] = (catStats[c] || 0) + 1;
    });

    // Sort categories and pick top 15 for better coverage
    const sortedCats = Object.entries(catStats).sort((a,b) => b[1] - a[1]).slice(0, 15);
    
    const catCtx = document.getElementById('categoryChart').getContext('2d');
    new Chart(catCtx, {
        type: 'polarArea',
        data: {
            labels: sortedCats.map(c => c[0]),
            datasets: [{
                data: sortedCats.map(c => c[1]),
                backgroundColor: sortedCats.map((_, i) => `rgba(139, 92, 246, ${0.8 - (i * 0.08)})`),
                borderColor: 'rgba(255, 255, 255, 0.1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: { r: { grid: { color: 'rgba(255,255,255,0.05)' }, ticks: { display: false } } },
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#94a3b8', font: { family: 'Inter', size: 10 }, usePointStyle: true, padding: 15 }
                }
            }
        }
    });

    // 3. Discount Intensity (Bar Chart)
    const storeDiscounts = {};
    const storeCounts = {};
    deals.forEach(d => {
        const s = d.website_source || 'Unknown';
        storeDiscounts[s] = (storeDiscounts[s] || 0) + (d.discount_percentage || 0);
        storeCounts[s] = (storeCounts[s] || 0) + 1;
    });

    const avgDiscounts = {};
    Object.keys(storeDiscounts).forEach(s => {
        avgDiscounts[s] = Math.round(storeDiscounts[s] / storeCounts[s]);
    });

    const discCtx = document.getElementById('discountChart').getContext('2d');
    new Chart(discCtx, {
        type: 'bar',
        data: {
            labels: Object.keys(avgDiscounts),
            datasets: [{
                label: 'Avg Discount %',
                data: Object.values(avgDiscounts),
                backgroundColor: 'rgba(236, 72, 153, 0.4)',
                borderColor: '#ec4899',
                borderWidth: 2,
                borderRadius: 10,
                barThickness: 40
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: { 
                    beginAtZero: true, 
                    grid: { color: 'rgba(255,255,255,0.05)' },
                    ticks: { color: '#64748b' }
                },
                x: {
                    grid: { display: false },
                    ticks: { color: '#64748b' }
                }
            },
            plugins: {
                legend: { display: false }
            }
        }
    });
}
