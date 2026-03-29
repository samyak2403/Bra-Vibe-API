// store.js - Logic for the full store catalog

const DEALS_API = '../data/all_bras.json';
const PREMIUM_API = '../data/premium_bras.json';

let allDeals = [];
let premiumDeals = [];

document.addEventListener('DOMContentLoaded', () => {
    initStore();
});

async function initStore() {
    const container = document.getElementById('store-container');
    const stats = document.getElementById('stats');

    try {
        // Fetch both datasets concurrently
        const [dealsRes, premiumRes] = await Promise.all([
            fetch(DEALS_API).catch(() => null),
            fetch(PREMIUM_API).catch(() => null)
        ]);

        if (dealsRes && dealsRes.ok) {
            const data = await dealsRes.json();
            allDeals = data.deals || [];
        }

        if (premiumRes && premiumRes.ok) {
            const data = await premiumRes.json();
            premiumDeals = data.deals || [];
        }

        setupFilters();
        renderGrid('all');

    } catch (err) {
        console.error("Failed to load store data:", err);
        container.innerHTML = '<div style="text-align: center; color: var(--accent-pink); width: 100%; grid-column: 1/-1;">Error loading the catalog. Please check the API/JSON files.</div>';
    }
}

function setupFilters() {
    const buttons = document.querySelectorAll('.filter-btn');
    buttons.forEach(btn => {
        btn.addEventListener('click', (e) => {
            buttons.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            const filterType = e.target.getAttribute('data-filter');
            renderGrid(filterType);
        });
    });
}

function renderGrid(filterType) {
    const container = document.getElementById('store-container');
    const stats = document.getElementById('stats');
    container.innerHTML = '';

    let itemsToRender = [];
    if (filterType === 'premium') {
        itemsToRender = premiumDeals;
    } else {
        // Display all, perhaps combine them or just show regular
        // Because premium is separated, if user clicks 'All', show both sorted by discount
        itemsToRender = [...allDeals, ...premiumDeals].sort((a, b) => b.discount_percentage - a.discount_percentage);
    }

    stats.innerText = `Showing ${itemsToRender.length} product(s) from Indian e-commerce stores`;

    if (itemsToRender.length === 0) {
        container.innerHTML = '<div style="text-align: center; color: var(--text-muted); width: 100%; grid-column: 1/-1;">No products found in this category.</div>';
        return;
    }

    itemsToRender.forEach(deal => {
        const card = document.createElement('div');
        card.className = 'product-card';

        const p_orig = deal.price_original || 0;
        const p_disc = deal.price_discounted || 0;
        const disc_perc = deal.discount_percentage || 0;
        const isPremium = deal.premium ? '⭐ PREMIUM' : (deal.website_source || 'STORE');

        // Use a nice premium badge style if it's premium
        const badgeStyle = deal.premium ? 'background: rgba(236, 72, 153, 0.1); color: var(--accent-pink);' : '';

        const discountTagHTML = disc_perc > 0 ? `<div class="discount-tag">${disc_perc}% OFF</div>` : '';
        const priceOldHTML = disc_perc > 0 ? `<span class="price-old">₹${p_orig}</span>` : '';

        card.innerHTML = `
            ${discountTagHTML}
            <img src="${deal.image_url}" alt="${deal.name}" class="card-img" onerror="this.src='https://via.placeholder.com/300x400?text=Lingerie'">
            <div class="card-content">
                <span class="brand-badge" style="${badgeStyle}">${isPremium} | ${deal.brand || 'Unbranded'}</span>
                <div class="product-name" title="${deal.name}">${deal.name}</div>
                <div class="price-row">
                    <span class="price-now">₹${p_disc}</span>
                    ${priceOldHTML}
                </div>
                <a href="${deal.product_url}" target="_blank" class="btn btn-primary" style="padding: 0.6rem 1rem; width: 100%; justify-content: center; margin-top: 1.5rem; border-radius: 12px; font-size: 0.85rem;">View on Store</a>
            </div>
        `;
        container.appendChild(card);
    });
}
