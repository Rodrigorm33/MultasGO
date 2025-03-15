/**
 * MultasGO - Script Principal
 * Responsável pela interação com a API e manipulação da interface
 */

// Configurações - URLs corrigidas
const BASE_URL = "http://localhost:8080"; // URL fixa para garantir que as requisições sejam enviadas para o servidor correto
const API_ENDPOINT = `${BASE_URL}/api/v1/infracoes`;
const SEARCH_ENDPOINT = `${API_ENDPOINT}/pesquisa`;
const DETAILS_ENDPOINT = API_ENDPOINT;

// Log para debug
console.log("API URL configurada:", API_ENDPOINT);

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
    console.log("MultasGO inicializado com sucesso!");
    console.log("Usando API em:", API_ENDPOINT);
    
    // Forçar limpeza inicial do DOM
    document.querySelectorAll('#error-message, #suggestion-container').forEach(el => {
        el.style.display = 'none';
        el.textContent = '';
        el.innerHTML = '';
    });
    
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
        console.log("Formulário de pesquisa configurado!");
    } else {
        console.error("Formulário de pesquisa não encontrado na página!");
    }

    // Adicionar regra CSS programaticamente para garantir compatibilidade
    function addConflictResolutionCSS() {
        const styleEl = document.createElement('style');
        styleEl.textContent = `
            /* Regra para garantir que erro e sugestão nunca apareçam juntos */
            #error-message:not([style*="display: none"]) ~ #suggestion-container,
            #suggestion-container:not([style*="display: none"]) ~ #error-message,
            #error-message[style*="display: block"] + #suggestion-container,
            #suggestion-container[style*="display: block"] + #error-message,
            #error-message:not(:empty) ~ #suggestion-container,
            #suggestion-container:not(:empty) ~ #error-message,
            /* Novas regras mais específicas */
            #suggestion-container:not(:empty) + #error-message,
            #error-message:not(:empty) + #suggestion-container,
            #suggestion-container[style*="display: block"] ~ #error-message,
            #error-message[style*="display: block"] ~ #suggestion-container,
            /* Regra mais forte para sugestões */
            body:has(#suggestion-container:not([style*="display: none"])) #error-message {
                display: none !important;
            }
        `;
        document.head.appendChild(styleEl);
    }

    // Adicionar regra CSS para garantir que as mensagens nunca apareçam juntas
    addConflictResolutionCSS();
});

// Manipulador de pesquisa
async function handleSearch(event) {
    event.preventDefault();
    
    if (isLoading) return;
    
    const query = searchInput.value.trim();
    
    if (!query) {
        errorMessage.textContent = 'Por favor, digite um termo de pesquisa.';
        errorMessage.style.display = 'block';
        suggestionContainer.style.display = 'none';
        return;
    }
    
    isLoading = true;
    showLoading(true);
    
    // Limpar mensagens antes da pesquisa
    errorMessage.style.display = 'none';
    errorMessage.textContent = '';
    suggestionContainer.style.display = 'none';
    suggestionContainer.innerHTML = '';
    
    console.log("Iniciando pesquisa para:", query);
    
    try {
        const url = `${SEARCH_ENDPOINT}?query=${encodeURIComponent(query)}`;
        console.log("Fazendo requisição para:", url);
        
        const response = await fetch(url, {
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            }
        });
        console.log("Status da resposta:", response.status);
        
        if (!response.ok) {
            const errorText = await response.text();
            console.error("Erro na resposta:", errorText);
            throw new Error(`Erro ${response.status}: ${response.statusText}. Detalhes: ${errorText}`);
        }
        
        const data = await response.json();
        console.log("Dados recebidos:", data);
        
        displayResults(data);
    } catch (error) {
        console.error('Erro na pesquisa:', error);
        errorMessage.textContent = `Erro na pesquisa: ${error.message}`;
        errorMessage.style.display = 'block';
        suggestionContainer.style.display = 'none';
        
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

// Exibir resultados da pesquisa
function displayResults(data) {
    console.log("Dados recebidos em displayResults:", data);
    
    // Forçar limpeza do DOM
    document.querySelectorAll('#error-message, #suggestion-container').forEach(el => {
        el.style.display = 'none';
        el.textContent = '';
        el.innerHTML = '';
    });
    
    // Garantir que data seja um objeto válido
    if (!data) {
        console.error("Dados inválidos recebidos:", data);
        errorMessage.style.display = 'block';
        errorMessage.textContent = "Dados de resposta inválidos";
        suggestionContainer.style.display = 'none';
        suggestionContainer.innerHTML = '';
        return;
    }
    
    // Extrair resultados com verificação para evitar erros
    const resultados = data.resultados || [];
    const total = data.total || 0;
    const mensagem = data.mensagem || '';
    const sugestao = data.sugestao || '';
    
    console.log(`Exibindo ${resultados.length} resultados de ${total} totais`);
    console.log("Resultados:", resultados);
    
    // NOVA ABORDAGEM: Controle direto da visibilidade
    // Primeiro, limpar ambas as mensagens
    errorMessage.style.display = 'none';
    errorMessage.textContent = '';
    suggestionContainer.style.display = 'none';
    suggestionContainer.innerHTML = '';
    
    // Depois, mostrar apenas a mensagem apropriada
    if (sugestao) {
        // Se houver sugestão, mostrar APENAS ela
        suggestionContainer.style.display = 'block';
        if (sugestao.startsWith('Você quis dizer')) {
            const termMatch = sugestao.match(/'([^']+)'/);
            if (termMatch && termMatch[1]) {
                const suggestedTerm = termMatch[1];
                suggestionContainer.innerHTML = `
                    <span>Você quis dizer: </span>
                    <a href="#" class="suggestion-link">${suggestedTerm}</a>?
                `;
                
                // Adicionar evento de clique na sugestão
                const suggestionLink = suggestionContainer.querySelector('.suggestion-link');
                if (suggestionLink) {
                    suggestionLink.addEventListener('click', (e) => {
                        e.preventDefault();
                        searchInput.value = suggestionLink.textContent.trim();
                        handleSearch(new Event('submit'));
                    });
                }
            }
        }
    } else if (mensagem && (!resultados || resultados.length === 0)) {
        // Se não houver sugestão mas houver mensagem de erro, mostrar APENAS o erro
        errorMessage.textContent = mensagem;
        errorMessage.style.display = 'block';
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
                    try {
                        console.log("Criando linha para infração:", infracao);
                        const row = createResultRow(infracao);
                        tbody.appendChild(row);
                    } catch (error) {
                        console.error("Erro ao criar linha para infração:", infracao, error);
                    }
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
    
    // Garantir que temos valores válidos (prevenção de erros)
    const codigo = infracao.codigo || '';
    const descricao = infracao.descricao || '';
    const gravidade = (infracao.gravidade === "nan" || !infracao.gravidade) ? "Não Aplicável" : infracao.gravidade;
    
    // Garantir que valor_multa é um número
    let valorMulta = 0;
    try {
        valorMulta = parseFloat(infracao.valor_multa || 0);
    } catch (error) {
        console.warn("Erro ao converter valor da multa:", infracao.valor_multa);
    }
    
    // Adicionar células
    row.innerHTML = `
        <td>${codigo}</td>
        <td>${descricao}</td>
        <td><span class="badge badge-${getBadgeClass(gravidade)}">${gravidade}</span></td>
        <td>R$ ${valorMulta.toFixed(2).replace('.', ',')}</td>
        <td>
            <button class="btn-details" data-codigo="${codigo}">Detalhes</button>
        </td>
    `;
    
    // Adicionar evento de clique no botão de detalhes
    const detailsButton = row.querySelector('.btn-details');
    if (detailsButton) {
        detailsButton.addEventListener('click', () => {
            getInfractionDetails(codigo);
        });
    }
    
    return row;
}

// Obter classe de badge com base na gravidade
function getBadgeClass(gravidade) {
    if (!gravidade) return 'media'; // Caso a gravidade seja undefined ou null
    
    const gravidadeLower = String(gravidade).toLowerCase();
    
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
    
    console.log("Buscando detalhes para código:", codigo);
    
    try {
        const url = `${DETAILS_ENDPOINT}/${encodeURIComponent(codigo)}`;
        console.log("Fazendo requisição para:", url);
        
        const response = await fetch(url);
        console.log("Status da resposta:", response.status);
        
        if (!response.ok) {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        console.log("Dados recebidos:", data);
        
        displayInfractionDetails(data);
    } catch (error) {
        console.error('Erro ao buscar detalhes:', error);
        errorMessage.textContent = `Erro ao buscar detalhes: ${error.message}`;
        errorMessage.style.display = 'block';
    } finally {
        isLoading = false;
        showLoading(false);
    }
}

// Exibir detalhes de uma infração
function displayInfractionDetails(infracao) {
    if (!detailsContainer) return;
    
    // Verificar se temos dados válidos
    if (!infracao) {
        console.error("Dados de infração inválidos:", infracao);
        errorMessage.style.display = 'block';
        errorMessage.textContent = "Não foi possível exibir os detalhes da infração";
        return;
    }
    
    // Garantir que temos valores válidos (prevenção de erros)
    const codigo = infracao.codigo || '';
    const descricao = infracao.descricao || '';
    const responsavel = infracao.responsavel || '';
    const orgaoAutuador = infracao.orgao_autuador || '';
    const artigosCTB = infracao.artigos_ctb || '';
    let pontos = 0;
    let valorMulta = 0;
    
    try {
        pontos = parseInt(infracao.pontos || 0);
    } catch (error) {
        console.warn("Erro ao converter pontos:", infracao.pontos);
    }
    
    try {
        valorMulta = parseFloat(infracao.valor_multa || 0);
    } catch (error) {
        console.warn("Erro ao converter valor da multa:", infracao.valor_multa);
    }
    
    // Formatar a gravidade para substituir "nan" por "Não Aplicável"
    const gravidade = (infracao.gravidade === "nan" || !infracao.gravidade) ? "Não Aplicável" : infracao.gravidade;
    
    // Preencher detalhes
    detailsContainer.innerHTML = `
        <div class="infracao-details animate-fade-in">
            <div class="infracao-header">
                <div>
                    <h2 class="infracao-title">${descricao}</h2>
                    <p class="infracao-codigo">Código: ${codigo}</p>
                </div>
                <div class="infracao-gravidade">
                    <span class="badge badge-${getBadgeClass(gravidade)}">${gravidade}</span>
                </div>
            </div>
            <div class="infracao-body">
                <div>
                    <div class="infracao-info">
                        <span class="infracao-label">Responsável</span>
                        <div class="infracao-value">${responsavel}</div>
                    </div>
                    <div class="infracao-info">
                        <span class="infracao-label">Valor da Multa</span>
                        <div class="infracao-value">R$ ${valorMulta.toFixed(2).replace('.', ',')}</div>
                    </div>
                    <div class="infracao-info">
                        <span class="infracao-label">Pontos</span>
                        <div class="infracao-value">${pontos}</div>
                    </div>
                </div>
                <div>
                    <div class="infracao-info">
                        <span class="infracao-label">Órgão Autuador</span>
                        <div class="infracao-value">${orgaoAutuador}</div>
                    </div>
                    <div class="infracao-info">
                        <span class="infracao-label">Artigos do CTB</span>
                        <div class="infracao-value">${artigosCTB}</div>
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
        console.log("Inicializando o explorador de infrações");
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
        console.log("Carregando lista de infrações do servidor...");
        const url = `${API_ENDPOINT}/?limit=100`;  // Reduzido para 100 para diminuir carga
        console.log("Fazendo requisição para:", url);
        
        const response = await fetch(url);
        console.log("Status da resposta:", response.status);
        
        if (response.status === 500) {
            console.warn("Erro 500 no servidor. Usando dados de fallback.");
            // Usar alguns dados de fallback para que o explorador funcione mesmo sem servidor
            allInfracoes = [
                { 
                    codigo: "54870", 
                    descricao: "Estacionar ao lado de outro veículo em fila dupla", 
                    responsavel: "Condutor",
                    valor_multa: 195.23,
                    pontos: 5,
                    gravidade: "grave"
                },
                { 
                    codigo: "55173", 
                    descricao: "Estacionar nos túneis", 
                    responsavel: "Condutor",
                    valor_multa: 195.23,
                    pontos: 5,
                    gravidade: "grave"
                },
                { 
                    codigo: "76252", 
                    descricao: "Estacionar o veículo nas vagas reservadas a idosos, sem credencial", 
                    responsavel: "Condutor",
                    valor_multa: 293.47,
                    pontos: 7,
                    gravidade: "gravíssima"
                },
                { 
                    codigo: "62540", 
                    descricao: "Transitar em velocidade inferior à metade da máxima da via", 
                    responsavel: "Condutor",
                    valor_multa: 130.16,
                    pontos: 4,
                    gravidade: "média"
                }
            ];
        } else if (response.ok) {
            const data = await response.json();
            console.log(`Recebidas ${data.length} infrações do servidor`);
            allInfracoes = data;
        } else {
            throw new Error(`Erro ${response.status}: ${response.statusText}`);
        }
        
        filteredInfracoes = [...allInfracoes];
        renderExplorerTable();
    } catch (error) {
        console.error('Erro ao carregar infrações:', error);
        
        // Mostrar mensagem de erro na interface
        if (explorerTable) {
            const tbody = explorerTable.querySelector('tbody');
            if (tbody) {
                tbody.innerHTML = `
                    <tr>
                        <td colspan="7" class="no-results">
                            Não foi possível carregar as infrações. Erro: ${error.message}
                            <br><br>
                            <button id="retry-load" class="btn-primary">Tentar Novamente</button>
                        </td>
                    </tr>
                `;
                
                // Adicionar botão para tentar novamente
                const retryButton = document.getElementById('retry-load');
                if (retryButton) {
                    retryButton.addEventListener('click', () => {
                        loadAllInfracoes();
                    });
                }
            }
        }
    }
}

// Aplicar filtros e ordenação
function applyFilters() {
    const gravidade = filterGravidade.value;
    const responsavel = filterResponsavel.value;
    const pontos = filterPontos.value;
    const sortBy = sortField.value;
    const direction = sortDirection.value;
    
    console.log("Aplicando filtros:", { gravidade, responsavel, pontos, sortBy, direction });
    
    // Filtrar infrações
    filteredInfracoes = allInfracoes.filter(infracao => {
        // Filtro de gravidade
        if (gravidade && String(infracao.gravidade || "").toLowerCase() !== gravidade.toLowerCase()) {
            return false;
        }
        
        // Filtro de responsável
        if (responsavel && String(infracao.responsavel || "").trim() !== responsavel.trim()) {
            return false;
        }
        
        // Filtro de pontos
        if (pontos) {
            let pontosNum = 0;
            try {
                pontosNum = parseInt(infracao.pontos || 0);
            } catch (error) {
                console.warn("Erro ao converter pontos para filtro:", infracao.pontos);
            }
            
            if (pontosNum !== parseInt(pontos)) {
                return false;
            }
        }
        
        return true;
    });
    
    console.log(`Filtro aplicado: ${filteredInfracoes.length} infrações encontradas`);
    
    // Ordenar infrações
    filteredInfracoes.sort((a, b) => {
        let valueA = a[sortBy];
        let valueB = b[sortBy];
        
        // Converter para número se for um campo numérico
        if (sortBy === 'valor_multa' || sortBy === 'pontos') {
            try {
                valueA = parseFloat(valueA || 0);
                valueB = parseFloat(valueB || 0);
            } catch (error) {
                console.warn("Erro ao converter valores para ordenação:", valueA, valueB);
                valueA = 0;
                valueB = 0;
            }
        } else {
            // Converter para string para comparação de texto
            valueA = String(valueA || "").toLowerCase();
            valueB = String(valueB || "").toLowerCase();
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
    
    console.log("Filtros resetados");
    
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
    
    console.log(`Renderizando página ${currentPage} de ${totalPages}, exibindo itens ${startIndex+1}-${endIndex} de ${filteredInfracoes.length}`);
    
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
            try {
                const row = createExplorerRow(infracao);
                tbody.appendChild(row);
            } catch (error) {
                console.error("Erro ao criar linha para o explorador:", infracao, error);
            }
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
    
    // Garantir que temos valores válidos (prevenção de erros)
    const codigo = infracao.codigo || '';
    const descricao = infracao.descricao || '';
    const responsavel = infracao.responsavel || '';
    const gravidade = (infracao.gravidade === "nan" || !infracao.gravidade) ? "Não Aplicável" : infracao.gravidade;
    
    // Garantir que pontos e valorMulta são números
    let pontos = 0;
    let valorMulta = 0;
    
    try {
        pontos = parseInt(infracao.pontos || 0);
    } catch (error) {
        console.warn("Erro ao converter pontos:", infracao.pontos);
    }
    
    try {
        valorMulta = parseFloat(infracao.valor_multa || 0);
    } catch (error) {
        console.warn("Erro ao converter valor da multa:", infracao.valor_multa);
    }
    
    // Adicionar células
    row.innerHTML = `
        <td>${codigo}</td>
        <td>${descricao}</td>
        <td><span class="badge badge-${getBadgeClass(gravidade)}">${gravidade}</span></td>
        <td>${responsavel}</td>
        <td>${pontos}</td>
        <td>R$ ${valorMulta.toFixed(2).replace('.', ',')}</td>
        <td>
            <button class="btn-details" data-codigo="${codigo}">Detalhes</button>
        </td>
    `;
    
    // Adicionar evento de clique no botão de detalhes
    const detailsButton = row.querySelector('.btn-details');
    if (detailsButton) {
        detailsButton.addEventListener('click', () => {
            getInfractionDetails(codigo);
            
            // Rolar para a seção de detalhes
            if (detailsContainer) {
                detailsContainer.scrollIntoView({ behavior: 'smooth' });
            }
        });
    }
    
    return row;
}