/**
 * MultasGO - Script Principal
 * Responsável pela interação com a API e manipulação da interface
 */

// Configurações
const API_ENDPOINT = '/api/v1/infracoes';
const SEARCH_ENDPOINT = `${API_ENDPOINT}/pesquisa`;
const DETAILS_ENDPOINT = API_ENDPOINT;

// Elementos DOM
const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const errorMessage = document.getElementById('error-message');
const loadingIndicator = document.getElementById('loading-indicator');
const resultsSection = document.getElementById('results-section');
const resultsContainer = document.getElementById('results-container');
const resultsTable = document.getElementById('results-table');
const resultsCount = document.getElementById('results-count');
const detailsContainer = document.getElementById('details-container');
const suggestionContainer = document.getElementById('suggestion-container');

// Estado da aplicação
let isLoading = false;

// Inicialização
document.addEventListener('DOMContentLoaded', () => {
    // Ocultar seção de resultados inicialmente
    if (resultsSection) {
        resultsSection.style.display = 'none';
    }
    
    // Ocultar detalhes inicialmente
    if (detailsContainer) {
        detailsContainer.style.display = 'none';
    }
    
    // Adicionar evento de submit ao formulário
    if (searchForm) {
        searchForm.addEventListener('submit', handleSearch);
    }
});

// Manipulador de pesquisa
async function handleSearch(event) {
    event.preventDefault();
    
    if (isLoading) return;
    
    const query = searchInput.value.trim();
    
    if (!query) {
        showError(true, 'Por favor, digite um termo de pesquisa.');
        return;
    }
    
    isLoading = true;
    showLoading(true);
    showError(false);
    
    try {
        const response = await fetch(`${SEARCH_ENDPOINT}?query=${encodeURIComponent(query)}`);
        const data = await response.json();
        
        if (response.ok) {
            displayResults(data);
        } else {
            throw new Error(data.detail || 'Erro ao buscar infrações');
        }
    } catch (error) {
        console.error('Erro na pesquisa:', error);
        showError(true, error.message);
        
        // Ocultar seção de resultados em caso de erro
        if (resultsSection) {
            resultsSection.style.display = 'none';
        }
    } finally {
        isLoading = false;
        showLoading(false);
    }
}

// Mostrar/ocultar indicador de carregamento
function showLoading(show) {
    if (loadingIndicator) {
        loadingIndicator.style.display = show ? 'block' : 'none';
    }
    
    if (searchBtn) {
        searchBtn.disabled = show;
    }
}

// Mostrar/ocultar mensagem de erro
function showError(show, message = '') {
    if (errorMessage) {
        errorMessage.style.display = show ? 'block' : 'none';
        errorMessage.textContent = message;
    }
}

// Mostrar/ocultar sugestão de pesquisa
function showSuggestion(show, suggestion = '') {
    if (suggestionContainer) {
        suggestionContainer.style.display = show ? 'block' : 'none';
        
        if (show && suggestion) {
            suggestionContainer.innerHTML = `
                <span>Você quis dizer: </span>
                <a href="#" class="suggestion-link">${suggestion}</a>?
            `;
            
            // Adicionar evento de clique na sugestão
            const suggestionLink = suggestionContainer.querySelector('.suggestion-link');
            if (suggestionLink) {
                suggestionLink.addEventListener('click', (e) => {
                    e.preventDefault();
                    searchInput.value = suggestion;
                    handleSearch(new Event('submit'));
                });
            }
        } else {
            suggestionContainer.innerHTML = '';
        }
    }
}

// Exibir resultados da pesquisa
function displayResults(data) {
    const { resultados, total, mensagem, sugestao } = data;
    
    // Mostrar mensagem se houver e não houver resultados
    if (mensagem && (!resultados || resultados.length === 0)) {
        showError(true, mensagem);
    } else {
        showError(false);
    }
    
    // Mostrar sugestão se houver
    if (sugestao) {
        showSuggestion(true, sugestao);
    } else {
        showSuggestion(false);
    }
    
    // Atualizar contador de resultados
    if (resultsCount) {
        resultsCount.textContent = `${total} ${total === 1 ? 'resultado encontrado' : 'resultados encontrados'}`;
    }
    
    // Limpar tabela de resultados
    if (resultsTable) {
        const tbody = resultsTable.querySelector('tbody');
        if (tbody) {
            tbody.innerHTML = '';
            
            if (resultados && resultados.length > 0) {
                resultados.forEach(infracao => {
                    const row = createResultRow(infracao);
                    tbody.appendChild(row);
                });
                
                // Mostrar seção de resultados
                resultsSection.style.display = 'block';
            } else {
                // Ocultar seção de resultados se não houver resultados
                resultsSection.style.display = 'none';
            }
        }
    }
    
    // Ocultar detalhes se estiverem visíveis
    if (detailsContainer) {
        detailsContainer.style.display = 'none';
    }
}

// Criar linha de resultado
function createResultRow(infracao) {
    const row = document.createElement('tr');
    
    // Formatar a gravidade para substituir "nan" por "Não Aplicável"
    const gravidade = infracao.gravidade === "nan" ? "Não Aplicável" : infracao.gravidade;
    
    // Adicionar células
    row.innerHTML = `
        <td>${infracao.codigo}</td>
        <td>${infracao.descricao}</td>
        <td><span class="badge badge-${getBadgeClass(gravidade)}">${gravidade}</span></td>
        <td>R$ ${infracao.valor_multa.toFixed(2).replace('.', ',')}</td>
        <td>
            <button class="btn-details" data-codigo="${infracao.codigo}">Detalhes</button>
        </td>
    `;
    
    // Adicionar evento de clique no botão de detalhes
    const detailsButton = row.querySelector('.btn-details');
    if (detailsButton) {
        detailsButton.addEventListener('click', () => {
            getInfractionDetails(infracao.codigo);
        });
    }
    
    return row;
}

// Obter classe de badge com base na gravidade
function getBadgeClass(gravidade) {
    if (!gravidade) return 'media'; // Caso a gravidade seja undefined ou null
    
    const gravidadeLower = gravidade.toLowerCase();
    
    if (gravidadeLower.includes('leve')) return 'leve';
    if (gravidadeLower.includes('média') || gravidadeLower.includes('media')) return 'media';
    if (gravidadeLower.includes('grave')) return 'grave';
    if (gravidadeLower.includes('gravíssima') || gravidadeLower.includes('gravissima')) return 'gravissima';
    if (gravidadeLower.includes('não aplicável') || gravidadeLower === 'nan') return 'nan';
    
    return 'media'; // Padrão
}

// Obter detalhes de uma infração
async function getInfractionDetails(codigo) {
    if (isLoading) return;
    
    isLoading = true;
    showLoading(true);
    showError(false);
    
    try {
        const response = await fetch(`${DETAILS_ENDPOINT}/${encodeURIComponent(codigo)}`);
        const data = await response.json();
        
        if (response.ok) {
            displayInfractionDetails(data);
        } else {
            throw new Error(data.detail || 'Erro ao buscar detalhes da infração');
        }
    } catch (error) {
        console.error('Erro ao buscar detalhes:', error);
        showError(true, error.message);
    } finally {
        isLoading = false;
        showLoading(false);
    }
}

// Exibir detalhes de uma infração
function displayInfractionDetails(infracao) {
    if (!detailsContainer) return;
    
    // Formatar a gravidade para substituir "nan" por "Não Aplicável"
    const gravidade = infracao.gravidade === "nan" ? "Não Aplicável" : infracao.gravidade;
    
    // Preencher detalhes
    detailsContainer.innerHTML = `
        <div class="infracao-details animate-fade-in">
            <div class="infracao-header">
                <div>
                    <h2 class="infracao-title">${infracao.descricao}</h2>
                    <p class="infracao-codigo">Código: ${infracao.codigo}</p>
                </div>
                <div class="infracao-gravidade">
                    <span class="badge badge-${getBadgeClass(gravidade)}">${gravidade}</span>
                </div>
            </div>
            <div class="infracao-body">
                <div>
                    <div class="infracao-info">
                        <span class="infracao-label">Responsável</span>
                        <div class="infracao-value">${infracao.responsavel}</div>
                    </div>
                    <div class="infracao-info">
                        <span class="infracao-label">Valor da Multa</span>
                        <div class="infracao-value">R$ ${infracao.valor_multa.toFixed(2).replace('.', ',')}</div>
                    </div>
                    <div class="infracao-info">
                        <span class="infracao-label">Pontos</span>
                        <div class="infracao-value">${infracao.pontos}</div>
                    </div>
                </div>
                <div>
                    <div class="infracao-info">
                        <span class="infracao-label">Órgão Autuador</span>
                        <div class="infracao-value">${infracao.orgao_autuador}</div>
                    </div>
                    <div class="infracao-info">
                        <span class="infracao-label">Artigos do CTB</span>
                        <div class="infracao-value">${infracao.artigos_ctb}</div>
                    </div>
                </div>
            </div>
            <div class="infracao-actions mt-4">
                <button id="back-to-results" class="btn-back">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <line x1="19" y1="12" x2="5" y2="12"></line>
                        <polyline points="12 19 5 12 12 5"></polyline>
                    </svg>
                    Voltar para resultados
                </button>
            </div>
        </div>
    `;
    
    // Mostrar detalhes
    detailsContainer.style.display = 'block';
    
    // Adicionar evento de clique no botão de voltar
    const backButton = document.getElementById('back-to-results');
    if (backButton) {
        backButton.addEventListener('click', () => {
            detailsContainer.style.display = 'none';
            resultsSection.style.display = 'block';
            
            // Rolar para a seção de resultados
            resultsSection.scrollIntoView({ behavior: 'smooth' });
        });
    }
    
    // Rolar para a seção de detalhes
    detailsContainer.scrollIntoView({ behavior: 'smooth' });
}

/**
 * Explorador de Infrações
 * Implementa a funcionalidade de filtragem e ordenação de infrações
 */

// Elementos DOM do explorador
const explorerSection = document.getElementById('explorer-section');
const filterGravidade = document.getElementById('filter-gravidade');
const filterResponsavel = document.getElementById('filter-responsavel');
const filterPontos = document.getElementById('filter-pontos');
const sortField = document.getElementById('sort-field');
const sortDirection = document.getElementById('sort-direction');
const applyFiltersBtn = document.getElementById('apply-filters');
const resetFiltersBtn = document.getElementById('reset-filters');
const explorerTable = document.getElementById('explorer-table');
const explorerCount = document.getElementById('explorer-count');
const prevPageBtn = document.getElementById('prev-page');
const nextPageBtn = document.getElementById('next-page');
const pageInfo = document.getElementById('page-info');

// Estado do explorador
let allInfracoes = [];
let filteredInfracoes = [];
let currentPage = 1;
const itemsPerPage = 10;

// Inicialização do explorador
document.addEventListener('DOMContentLoaded', () => {
    if (explorerSection) {
        initExplorer();
    }
});

// Inicializar o explorador
async function initExplorer() {
    // Adicionar eventos aos botões
    if (applyFiltersBtn) {
        applyFiltersBtn.addEventListener('click', applyFilters);
    }
    
    if (resetFiltersBtn) {
        resetFiltersBtn.addEventListener('click', resetFilters);
    }
    
    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                renderExplorerTable();
            }
        });
    }
    
    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', () => {
            const totalPages = Math.ceil(filteredInfracoes.length / itemsPerPage);
            if (currentPage < totalPages) {
                currentPage++;
                renderExplorerTable();
            }
        });
    }
    
    // Carregar todas as infrações
    await loadAllInfracoes();
}

// Carregar todas as infrações do servidor
async function loadAllInfracoes() {
    try {
        const response = await fetch(`${API_ENDPOINT}/?limit=500`);
        const data = await response.json();
        
        if (response.ok) {
            allInfracoes = data;
            filteredInfracoes = [...allInfracoes];
            renderExplorerTable();
        } else {
            console.error('Erro ao carregar infrações:', data);
        }
    } catch (error) {
        console.error('Erro ao carregar infrações:', error);
    }
}

// Aplicar filtros e ordenação
function applyFilters() {
    const gravidade = filterGravidade.value;
    const responsavel = filterResponsavel.value;
    const pontos = filterPontos.value;
    const sortBy = sortField.value;
    const direction = sortDirection.value;
    
    // Filtrar infrações
    filteredInfracoes = allInfracoes.filter(infracao => {
        // Filtro de gravidade
        if (gravidade && infracao.gravidade !== gravidade) {
            return false;
        }
        
        // Filtro de responsável
        if (responsavel && infracao.responsavel !== responsavel) {
            return false;
        }
        
        // Filtro de pontos
        if (pontos && infracao.pontos !== parseInt(pontos)) {
            return false;
        }
        
        return true;
    });
    
    // Ordenar infrações
    filteredInfracoes.sort((a, b) => {
        let valueA = a[sortBy];
        let valueB = b[sortBy];
        
        // Converter para número se for um campo numérico
        if (sortBy === 'valor_multa' || sortBy === 'pontos') {
            valueA = parseFloat(valueA);
            valueB = parseFloat(valueB);
        } else {
            // Converter para string para comparação de texto
            valueA = String(valueA).toLowerCase();
            valueB = String(valueB).toLowerCase();
        }
        
        // Ordenar
        if (direction === 'asc') {
            return valueA > valueB ? 1 : -1;
        } else {
            return valueA < valueB ? 1 : -1;
        }
    });
    
    // Resetar para a primeira página
    currentPage = 1;
    
    // Renderizar tabela
    renderExplorerTable();
}

// Resetar filtros
function resetFilters() {
    // Resetar valores dos filtros
    filterGravidade.value = '';
    filterResponsavel.value = '';
    filterPontos.value = '';
    sortField.value = 'codigo';
    sortDirection.value = 'asc';
    
    // Resetar infrações filtradas
    filteredInfracoes = [...allInfracoes];
    
    // Resetar para a primeira página
    currentPage = 1;
    
    // Renderizar tabela
    renderExplorerTable();
}

// Renderizar tabela do explorador
function renderExplorerTable() {
    if (!explorerTable) return;
    
    const tbody = explorerTable.querySelector('tbody');
    if (!tbody) return;
    
    // Limpar tabela
    tbody.innerHTML = '';
    
    // Calcular paginação
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = startIndex + itemsPerPage;
    const paginatedInfracoes = filteredInfracoes.slice(startIndex, endIndex);
    const totalPages = Math.ceil(filteredInfracoes.length / itemsPerPage);
    
    // Atualizar contador
    if (explorerCount) {
        explorerCount.textContent = `${filteredInfracoes.length} infrações encontradas`;
    }
    
    // Atualizar informações de página
    if (pageInfo) {
        pageInfo.textContent = `Página ${currentPage} de ${totalPages || 1}`;
    }
    
    // Atualizar estado dos botões de paginação
    if (prevPageBtn) {
        prevPageBtn.disabled = currentPage <= 1;
    }
    
    if (nextPageBtn) {
        nextPageBtn.disabled = currentPage >= totalPages;
    }
    
    // Renderizar linhas
    if (paginatedInfracoes.length > 0) {
        paginatedInfracoes.forEach(infracao => {
            const row = createExplorerRow(infracao);
            tbody.appendChild(row);
        });
    } else {
        // Mostrar mensagem de nenhum resultado
        const row = document.createElement('tr');
        row.innerHTML = `
            <td colspan="7" class="no-results">Nenhuma infração encontrada com os filtros selecionados.</td>
        `;
        tbody.appendChild(row);
    }
}

// Criar linha da tabela do explorador
function createExplorerRow(infracao) {
    const row = document.createElement('tr');
    
    // Formatar a gravidade para substituir "nan" por "Não Aplicável"
    const gravidade = infracao.gravidade === "nan" ? "Não Aplicável" : infracao.gravidade;
    
    // Adicionar células
    row.innerHTML = `
        <td>${infracao.codigo}</td>
        <td>${infracao.descricao}</td>
        <td><span class="badge badge-${getBadgeClass(gravidade)}">${gravidade}</span></td>
        <td>${infracao.responsavel}</td>
        <td>${infracao.pontos}</td>
        <td>R$ ${infracao.valor_multa.toFixed(2).replace('.', ',')}</td>
        <td>
            <button class="btn-details" data-codigo="${infracao.codigo}">Detalhes</button>
        </td>
    `;
    
    // Adicionar evento de clique no botão de detalhes
    const detailsButton = row.querySelector('.btn-details');
    if (detailsButton) {
        detailsButton.addEventListener('click', () => {
            getInfractionDetails(infracao.codigo);
            
            // Rolar para a seção de detalhes
            if (detailsContainer) {
                detailsContainer.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    return row;
} 