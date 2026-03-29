// Bra Vibe API - Application Logic

const DEALS_JSON_PATH = '../data/bras_deals.json';

document.addEventListener('DOMContentLoaded', () => {
    fetchDeals();
    initializeTabs();
    updateHomeMetrics();
});

async function updateHomeMetrics() {
    const totalCountEl = document.getElementById('total-count');
    const storeCountEl = document.getElementById('store-count');
    
    if (!totalCountEl || !storeCountEl) return;

    try {
        const response = await fetch('../data/all_bras.json');
        const data = await response.json();
        const deals = data.deals || [];
        
        const total = deals.length;
        const stores = [...new Set(deals.map(d => d.website_source))].length;

        totalCountEl.innerText = total;
        storeCountEl.innerText = stores;
    } catch (err) {
        console.error("Failed to load metrics:", err);
    }
}

async function fetchDeals() {
    const dealsContainer = document.getElementById('deals-container');
    try {
        const response = await fetch(DEALS_JSON_PATH);
        const data = await response.json();
        const deals = data.deals || [];

        dealsContainer.innerHTML = ''; // Clear loading text

        if (deals.length === 0) {
            dealsContainer.innerHTML = '<div style="text-align: center; color: var(--text-muted); width: 100%; grid-column: 1/-1;">No deals available at the moment. Check back soon!</div>';
            return;
        }

        deals.forEach(deal => {
            const card = createProductCard(deal);
            dealsContainer.appendChild(card);
        });

    } catch (error) {
        console.error('Error fetching deals:', error);
        dealsContainer.innerHTML = '<div style="text-align: center; color: var(--accent-pink); width: 100%; grid-column: 1/-1;">Error loading deals. Please ensure the JSON file is available.</div>';
    }
}

function createProductCard(deal) {
    const card = document.createElement('div');
    card.className = 'product-card';

    const p_orig = deal.price_original || 0;
    const p_disc = deal.price_discounted || 0;
    const disc_perc = deal.discount_percentage || 0;

    const discountTagHTML = disc_perc > 0 ? `<div class="discount-tag">${disc_perc}% OFF</div>` : '';
    const priceOldHTML = disc_perc > 0 ? `<span class="price-old">₹${p_orig}</span>` : '';

    const image_urls = (deal.image_urls || [deal.image_url]).filter(u => u);
    let dotsHTML = '';
    if (image_urls.length > 1) {
        dotsHTML = `<div class="image-dots-container">`;
        // Limit dots to 5 for UI clarity
        image_urls.slice(0, 7).forEach((url, index) => {
            dotsHTML += `<span class="image-dot ${index === 0 ? 'active' : ''}" data-url="${url}"></span>`;
        });
        dotsHTML += `</div>`;
    }

    card.innerHTML = `
        ${discountTagHTML}
        ${dotsHTML}
        <img src="${deal.image_url}" alt="${deal.name}" class="card-img" onerror="this.src='https://via.placeholder.com/300x400?text=Premium+Lingerie'">
        <div class="card-content">
            <span class="brand-badge">${deal.brand || deal.website_source}</span>
            <div class="product-name" title="${deal.name}">${deal.name}</div>
            <div class="price-row">
                <span class="price-now">₹${p_disc}</span>
                ${priceOldHTML}
            </div>
            <a href="${deal.product_url}" target="_blank" class="btn btn-primary" style="padding: 0.6rem 1rem; width: 100%; justify-content: center; margin-top: 1.5rem; border-radius: 12px; font-size: 0.85rem;">View Deal</a>
        </div>
    `;

    // Add image switching logic
    if (image_urls.length > 1) {
        const dots = card.querySelectorAll('.image-dot');
        const img = card.querySelector('.card-img');
        dots.forEach(dot => {
            const updateImage = () => {
                const url = dot.getAttribute('data-url');
                img.src = url;
                dots.forEach(d => d.classList.remove('active'));
                dot.classList.add('active');
            };
            dot.addEventListener('mouseenter', updateImage);
            dot.addEventListener('click', updateImage);
        });
    }

    return card;
}

function initializeTabs() {
    const tabs = document.querySelectorAll('#snippet-tabs .tab');
    const snippets = document.querySelectorAll('#snippet-container pre');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const lang = tab.getAttribute('data-lang');

            // Update tabs
            tabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Update snippets
            snippets.forEach(s => {
                s.style.display = s.id === `snippet-${lang}` ? 'block' : 'none';
            });
        });
    });
}

function copyToClipboard(text, btn) {
    navigator.clipboard.writeText(text).then(() => {
        const originalText = btn.innerText;
        btn.innerText = 'Copied!';
        btn.style.borderColor = 'var(--accent-pink)';
        setTimeout(() => {
            btn.innerText = originalText;
            btn.style.borderColor = 'var(--glass-border)';
        }, 2000);
    });
}

function showSnippet(lang) {
    const snippets = document.querySelectorAll('#snippet-container pre');
    const tabs = document.querySelectorAll('#snippet-tabs .tab');

    tabs.forEach(t => t.classList.remove('active'));
    document.querySelector(`[data-lang="${lang}"]`).classList.add('active');

    snippets.forEach(s => {
        s.style.display = s.id === `snippet-${lang}` ? 'block' : 'none';
    });
}
