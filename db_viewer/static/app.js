let currentPage = 1;
let currentQuery = "";

const searchInput = document.getElementById('searchInput');
const papersFeed = document.getElementById('papersFeed');
const resultsCount = document.getElementById('resultsCount');
const paginationControls = document.getElementById('paginationControls');

// Debounce function for search
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

const handleSearch = debounce((e) => {
    currentQuery = e.target.value;
    currentPage = 1;
    fetchPapers();
}, 300);

searchInput.addEventListener('input', handleSearch);

// Fetch data from API
async function fetchPapers() {
    papersFeed.innerHTML = '<div class="loading"><i class="ph ph-spinner ph-spin"></i> Loading papers...</div>';

    try {
        const response = await fetch(`/api/papers?page=${currentPage}&query=${encodeURIComponent(currentQuery)}`);
        const data = await response.json();

        renderPapers(data.papers);
        renderPagination(data.page, data.total_pages);
        resultsCount.textContent = `Showing ${data.papers.length} of ${data.total} papers`;
    } catch (error) {
        console.error("Error fetching papers:", error);
        papersFeed.innerHTML = '<div class="error">Failed to load papers. Ensure the database exists.</div>';
    }
}

// Map Source APIs to icons
function getSourceIcon(source) {
    const s = source.toLowerCase();
    if (s.includes('arxiv')) return 'ph-file-archive';
    if (s.includes('pubmed')) return 'ph-pill';
    if (s.includes('openalex')) return 'ph-books';
    if (s.includes('semantic')) return 'ph-brain';
    return 'ph-globe';
}

function formatDate(dateString) {
    if (!dateString) return 'Unknown Date';
    const options = { year: 'numeric', month: 'short', day: 'numeric' };
    return new Date(dateString).toLocaleDateString(undefined, options);
}

function renderPapers(papers) {
    if (papers.length === 0) {
        papersFeed.innerHTML = '<div class="empty-state"><i class="ph ph-files"></i><p>No papers found matching your criteria.</p></div>';
        return;
    }

    papersFeed.innerHTML = papers.map(paper => `
        <article class="paper-card">
            <div class="paper-meta">
                <span class="source-badge">
                    <i class="ph ${getSourceIcon(paper.source_api)}"></i>
                    ${paper.source_api}
                </span>
                <div class="meta-right">
                    <span class="citation-count">
                        <i class="ph ph-quotes"></i> ${paper.citation_count ?? 0} citations
                    </span>
                    <span class="pub-date">${formatDate(paper.published_date)}</span>
                </div>
            </div>
            
            <h2 class="paper-title">${paper.title}</h2>
            
            <div class="paper-authors">
                <i class="ph-fill ph-users"></i>
                <span>${paper.authors || 'Unknown Authors'}</span>
            </div>
            
            <div class="paper-abstract">
                ${paper.abstract_snippet ? paper.abstract_snippet : '<em>No abstract available.</em>'}
            </div>
            
            <div class="paper-actions">
                ${paper.source_url ?
            `<a href="${paper.source_url}" target="_blank" rel="noopener noreferrer" class="btn btn-primary">
                        Read Paper <i class="ph ph-arrow-up-right"></i>
                    </a>` : ''
        }
            </div>
        </article>
    `).join('');
}
function renderPagination(page, totalPages) {
    if (totalPages <= 1) {
        paginationControls.innerHTML = '';
        return;
    }

    let buttons = '';

    // Prev
    buttons += `<button class="page-btn" ${page === 1 ? 'disabled' : ''} onclick="goToPage(${page - 1})">Previous</button>`;

    // Pages (simplified)
    for (let i = Math.max(1, page - 2); i <= Math.min(totalPages, page + 2); i++) {
        buttons += `<button class="page-btn ${i === page ? 'active' : ''}" onclick="goToPage(${i})">${i}</button>`;
    }

    // Next
    buttons += `<button class="page-btn" ${page === totalPages ? 'disabled' : ''} onclick="goToPage(${page + 1})">Next</button>`;

    paginationControls.innerHTML = buttons;
}

window.goToPage = function (page) {
    currentPage = page;
    fetchPapers();
    window.scrollTo({ top: 0, behavior: 'smooth' });
}

// Initial fetch
fetchPapers();
