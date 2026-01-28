// Analysis functions for MarketScope

async function analyzeProduct(type) {
    const prompt = document.getElementById('productPrompt').value.trim();
    
    if (!prompt) {
        alert('Please describe your product concept first!');
        return;
    }

    // Show loading state
    const button = event.target.closest('button');
    const originalText = button.innerHTML;
    button.innerHTML = '<svg class="w-5 h-5 animate-spin inline mr-2" viewBox="0 0 24 24" fill="none"><circle cx="12" cy="12" r="10" stroke="currentColor" stroke-width="2" stroke-dasharray="60" stroke-dashoffset="40"/></svg>Analyzing...';
    button.disabled = true;

    try {
        const response = await fetch('/analyze', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt: prompt,
                type: type
            })
        });

        const data = await response.json();
        
        if (data.success) {
            displayResults(data.analysis, type);
        } else {
            alert('Analysis failed: ' + (data.error || 'Please try again.'));
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

function displayResults(analysis, type) {
    const container = document.getElementById('resultsContainer');
    container.style.display = 'block';
    container.classList.remove('hidden');
    container.scrollIntoView({ behavior: 'smooth', block: 'nearest' });

    if (type === 'full') {
        displayFullReport(analysis);
    } else if (type === 'market') {
        displayMarketOverview(analysis);
    } else if (type === 'competitive') {
        displayCompetitiveAnalysis(analysis);
    }
}

// Utility function to escape HTML and prevent XSS
function escapeHtml(text) {
    if (typeof text !== 'string') return text;
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function displayFullReport(analysis) {
    // Confidence Score
    const confidenceScore = document.getElementById('confidenceScore');
    if (confidenceScore) {
        const score = analysis.confidence_score || 0.85;
        confidenceScore.textContent = Math.round(score * 100) + '%';
    }

    // Market Gaps
    const marketGaps = document.getElementById('marketGaps');
    if (marketGaps && analysis.market_gaps) {
        marketGaps.innerHTML = analysis.market_gaps.map(gap => 
            `<li class="flex items-start gap-2 pb-3 border-b border-white/5 text-white/80 last:border-0">
                <span class="text-[#a78bfa] mt-1">→</span>
                <span>${escapeHtml(gap)}</span>
            </li>`
        ).join('');
    }

    // Pain Points
    const painPoints = document.getElementById('painPoints');
    if (painPoints && analysis.pain_points) {
        painPoints.innerHTML = analysis.pain_points.map(point => 
            `<li class="flex items-start gap-2 pb-3 border-b border-white/5 text-white/80 last:border-0">
                <span class="text-[#a78bfa] mt-1">→</span>
                <span>${escapeHtml(point)}</span>
            </li>`
        ).join('');
    }

    // Competitors
    const competitors = document.getElementById('competitors');
    if (competitors && analysis.competitors) {
        competitors.innerHTML = analysis.competitors.map(comp => `
            <div class="grid grid-cols-4 gap-4 p-4 bg-[#0f1420]/50 rounded-lg border-l-4 border-[#a78bfa]/40 mb-3">
                <div class="font-semibold">${escapeHtml(comp.name)}</div>
                <div class="text-sm text-white/70"><span class="block text-[#a78bfa] text-xs uppercase mb-1">Price</span>${escapeHtml(comp.price)}</div>
                <div class="text-sm text-white/70"><span class="block text-[#a78bfa] text-xs uppercase mb-1">Rating</span>${escapeHtml(comp.rating)}</div>
                <div class="text-sm text-white/70"><span class="block text-[#a78bfa] text-xs uppercase mb-1">Features</span>${comp.features}</div>
            </div>
        `).join('');
    }

    // Opportunities
    const opportunities = document.getElementById('opportunities');
    if (opportunities && analysis.opportunities) {
        opportunities.innerHTML = analysis.opportunities.map(opp => 
            `<li class="flex items-start gap-2 pb-3 border-b border-white/5 text-white/80 last:border-0">
                <span class="text-[#a78bfa] mt-1">★</span>
                <span>${escapeHtml(opp)}</span>
            </li>`
        ).join('');
    }

    // Viability
    const viability = document.getElementById('viabilityIndicator');
    if (viability && analysis.market_viability) {
        viability.textContent = analysis.market_viability + ' Potential';
        viability.className = 'text-4xl font-bold text-[#a78bfa]';
    }
}

function displayMarketOverview(analysis) {
    // Pricing Data
    const pricingData = document.getElementById('pricingData');
    if (pricingData && analysis.competitors) {
        const prices = analysis.competitors.map(comp => {
            const price = parseFloat(comp.price.replace(/[^0-9.]/g, ''));
            return isNaN(price) ? 0 : price;
        }).filter(p => p > 0);
        
        const avgPrice = prices.length > 0 ? prices.reduce((sum, p) => sum + p, 0) / prices.length : 0;
        const minPrice = prices.length > 0 ? Math.min(...prices) : 0;
        const maxPrice = prices.length > 0 ? Math.max(...prices) : 0;
        
        pricingData.innerHTML = `
            <div class="space-y-3">
                <div class="p-4 bg-[#0f1420]/50 rounded-lg border-l-4 border-[#a78bfa]/40">
                    <span class="font-semibold">Average Market Price:</span> $${avgPrice.toFixed(2)}
                </div>
                <div class="p-4 bg-[#0f1420]/50 rounded-lg border-l-4 border-[#a78bfa]/40">
                    <span class="font-semibold">Price Range:</span> $${minPrice.toFixed(2)} - $${maxPrice.toFixed(2)}
                </div>
                <div class="p-4 bg-[#0f1420]/50 rounded-lg border-l-4 border-[#a78bfa]/40">
                    <span class="font-semibold">Recommended Pricing:</span> $${(avgPrice * 0.9).toFixed(2)} - $${(avgPrice * 1.1).toFixed(2)}
                </div>
            </div>
        `;
    }

    // Features
    const features = document.getElementById('features');
    if (features && analysis.market_gaps) {
        features.innerHTML = analysis.market_gaps.map(gap => 
            `<li class="flex items-start gap-2 pb-3 border-b border-white/5 text-white/80 last:border-0">
                <span class="text-[#a78bfa] mt-1">→</span>
                <span>${escapeHtml(gap)}</span>
            </li>`
        ).join('');
    }

    // Positioning
    const positioning = document.getElementById('positioning');
    if (positioning && analysis.opportunities) {
        positioning.innerHTML = analysis.opportunities.map(opp => 
            `<li class="flex items-start gap-2 pb-3 border-b border-white/5 text-white/80 last:border-0">
                <span class="text-[#a78bfa] mt-1">→</span>
                <span>${escapeHtml(opp)}</span>
            </li>`
        ).join('');
    }
}

function displayCompetitiveAnalysis(analysis) {
    // Competitor Comparison
    const comparison = document.getElementById('competitorComparison');
    if (comparison && analysis.competitors) {
        comparison.innerHTML = analysis.competitors.map(comp => `
            <div class="p-4 bg-[#0f1420]/50 rounded-lg border-l-4 border-[#a78bfa]/40 mb-3">
                <div class="font-semibold mb-2">${escapeHtml(comp.name)}</div>
                <div class="text-sm text-white/70">Price: ${escapeHtml(comp.price)} | Rating: ${escapeHtml(comp.rating)} | Features: ${comp.features}</div>
            </div>
        `).join('');
    }

    // Differentiators
    const differentiators = document.getElementById('differentiators');
    if (differentiators && analysis.opportunities) {
        differentiators.innerHTML = analysis.opportunities.map(opp => 
            `<li class="flex items-start gap-2 pb-3 border-b border-white/5 text-white/80 last:border-0">
                <span class="text-[#a78bfa] mt-1">★</span>
                <span>${escapeHtml(opp)}</span>
            </li>`
        ).join('');
    }

    // Advantages
    const advantages = document.getElementById('advantages');
    if (advantages && analysis.market_gaps) {
        advantages.innerHTML = analysis.market_gaps.map(gap => 
            `<li class="flex items-start gap-2 pb-3 border-b border-white/5 text-white/80 last:border-0">
                <span class="text-[#a78bfa] mt-1">→</span>
                <span>Address: ${escapeHtml(gap)}</span>
            </li>`
        ).join('');
    }
}

// Add spinning animation for loading
const style = document.createElement('style');
style.textContent = `
    @keyframes spin {
        from { transform: rotate(0deg); }
        to { transform: rotate(360deg); }
    }
    .animate-spin {
        animation: spin 1s linear infinite;
    }
`;
document.head.appendChild(style);
