// URL base da API - Configurada para funcionar tanto em desenvolvimento quanto em produção
const API_BASE_URL = window.location.origin + '/api/v1';

// Configurações da API
const CONFIG = {
    MIN_QUERY_LENGTH: 2,
    MAX_QUERY_LENGTH: 100,
    DEFAULT_LIMIT: 100,
    DEFAULT_SKIP: 0
};

// Headers padrão para requisições
const DEFAULT_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
};

// Elementos da página
const searchForm = document.getElementById('search-form');
const searchInput = document.getElementById('search-input');
const searchBtn = document.getElementById('search-btn');
const resultsTable = document.getElementById('results-table');
const resultsBody = document.getElementById('results-body');
const loadingElement = document.getElementById('loading');
const errorMessage = document.getElementById('error-message');
const noResults = document.getElementById('no-results');
const totalResults = document.getElementById('total-results');

// Variável para controlar se há uma pesquisa em andamento
let isSearchInProgress = false;

/**
 * Formata um valor numérico para o formato de moeda brasileira (R$)
 * @param {number} valor - O valor a ser formatado
 * @returns {string} - Valor formatado como moeda
 */
function formatarMoeda(valor) {
    return valor.toLocaleString('pt-BR', { 
        style: 'currency', 
        currency: 'BRL',
        minimumFractionDigits: 2,
        maximumFractionDigits: 2
    });
}

/**
 * Destaca o termo de pesquisa dentro do texto
 * @param {string} texto - O texto completo
 * @param {string} termo - O termo a ser destacado
 * @returns {string} - Texto com o termo destacado usando HTML
 */
function destacarTexto(texto, termo) {
    if (!texto || !termo || termo.length < 3) return texto || '';
    
    try {
        const regex = new RegExp(termo.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi');
        return texto.replace(regex, match => `<span class="highlight">${match}</span>`);
    } catch (e) {
        console.warn('Erro ao destacar texto:', e);
        return texto;
    }
}

/**
 * Exibe uma mensagem de erro na interface
 * @param {string} mensagem - Mensagem de erro a ser exibida
 */
function mostrarErro(mensagem) {
    errorMessage.textContent = mensagem || 'Ocorreu um erro na pesquisa. Por favor, tente novamente.';
    errorMessage.style.display = 'block';
    loadingElement.style.display = 'none';
    resultsTable.style.display = 'none';
    noResults.style.display = 'none';
    totalResults.style.display = 'none';
    
    // Mostrar o container de resultados quando há erro
    const resultsContainer = document.querySelector('.results-container');
    if (resultsContainer) {
        resultsContainer.classList.add('active');
    }
}

/**
 * Limpa os resultados anteriores e reseta a interface
 */
function limparResultados() {
    resultsBody.innerHTML = '';
    errorMessage.style.display = 'none';
    noResults.style.display = 'none';
    resultsTable.style.display = 'none';
    loadingElement.style.display = 'none';
    totalResults.style.display = 'none';
    
    // Limpar também os cards
    const cardsContainer = document.getElementById('results-cards');
    if (cardsContainer) {
        cardsContainer.innerHTML = '';
        cardsContainer.style.display = 'none';
    }
    
    // Ocultar o container de resultados quando não há busca
    const resultsContainer = document.querySelector('.results-container');
    if (resultsContainer) {
        resultsContainer.classList.remove('active');
    }
}

/**
 * Formata o texto de gravidade com cores e estilos adequados
 * @param {string} gravidade - O texto da gravidade da infração
 * @returns {string} - HTML formatado para exibição da gravidade
 */
function formatarGravidade(gravidade) {
    // Converte o texto para minúsculo para facilitar a comparação
    const textoGravidade = String(gravidade).toLowerCase();
    
    // Lógica mais robusta de detecção
    if (textoGravidade.includes('gravissima') || textoGravidade.includes('gravíssima')) {
        return '<span class="gravidade-gravissima">Gravíssima</span>';
    } else if (textoGravidade.includes('grave')) {
        return '<span class="gravidade-grave">Grave</span>';
    } else if (textoGravidade.includes('media') || textoGravidade.includes('média')) {
        return '<span class="gravidade-media">Média</span>';
    } else if (textoGravidade.includes('leve')) {
        return '<span class="gravidade-leve">Leve</span>';
    }
    
    // Verificação de padrão numérico (como gravissima10x)
    if (textoGravidade.match(/gravissima\d+x/)) {
        return '<span class="gravidade-gravissima">Gravíssima</span>';
    } else if (textoGravidade.match(/grave\d+x/)) {
        return '<span class="gravidade-grave">Grave</span>';
    } else if (textoGravidade.match(/media\d+x/) || textoGravidade.match(/média\d+x/)) {
        return '<span class="gravidade-media">Média</span>';
    } else if (textoGravidade.match(/leve\d+x/)) {
        return '<span class="gravidade-leve">Leve</span>';
    }
    
    // Se não conseguiu identificar, devolve o texto original
    console.log("Gravidade não reconhecida:", gravidade);
    return gravidade;
}

/**
 * Função para expandir/recolher card
 * @param {Element} cardElement - O elemento do card a ser expandido/recolhido
 */
function toggleCard(cardElement) {
    const isExpanded = cardElement.classList.contains('expanded');
    const detailsSection = cardElement.querySelector('.card-details');
    const expandButton = cardElement.querySelector('.expand-button');
    
    if (isExpanded) {
        // Recolher
        cardElement.classList.remove('expanded');
        detailsSection.classList.remove('expanded');
        expandButton.classList.remove('expanded');
        expandButton.innerHTML = '<i class="fas fa-chevron-down expand-icon"></i> Ver mais detalhes';
    } else {
        // Expandir
        cardElement.classList.add('expanded');
        detailsSection.classList.add('expanded');
        expandButton.classList.add('expanded');
        expandButton.innerHTML = '<i class="fas fa-chevron-up expand-icon"></i> Ocultar detalhes';
    }
}

/**
 * Função para aplicar classe de estilo baseada na gravidade (para cards)
 * @param {string} gravidade - O texto da gravidade da infração
 * @returns {string} - Classe CSS para aplicar no card
 */
function getGravidadeCardClass(gravidade) {
    const gravidadeLower = gravidade.toLowerCase();
    if (gravidadeLower.includes('leve')) {
        return 'gravidade-leve';
    } else if (gravidadeLower.includes('méd') || gravidadeLower.includes('med')) {
        return 'gravidade-media';
    } else if (gravidadeLower.includes('grav') && !gravidadeLower.includes('gravíss')) {
        return 'gravidade-grave';
    } else if (gravidadeLower.includes('gravíss')) {
        return 'gravidade-gravissima';
    }
    return '';
}

/**
 * Função para exibir os resultados como cards
 * @param {Array} resultados - Array de infrações a serem exibidas
 * @param {string} query - Termo de pesquisa para destacar
 */
function exibirResultadosCards(resultados, query) {
    // Verificar se o container de cards existe, senão criar
    let cardsContainer = document.getElementById('results-cards');
    if (!cardsContainer) {
        cardsContainer = document.createElement('div');
        cardsContainer.id = 'results-cards';
        cardsContainer.className = 'infractions-container';
        
        // Inserir o container após o totalResults
        totalResults.insertAdjacentElement('afterend', cardsContainer);
    }
    
    if (resultados.length === 0) {
        cardsContainer.innerHTML = `
            <div class="no-results-card">
                <i class="fas fa-search"></i>
                <h4>Nenhuma infração encontrada</h4>
                <p>Tente ajustar os filtros ou usar termos diferentes na busca.</p>
            </div>
        `;
        return;
    }
    
    let html = '';
    
    resultados.forEach((infracao, index) => {
        const gravidadeCardClass = getGravidadeCardClass(infracao.gravidade);
        
        html += `
            <div class="infraction-card" data-codigo="${infracao.codigo}">
                <div class="info-indicator">${index + 1}</div>
                
                <!-- Seção Principal (sempre visível) -->
                <div class="card-main">
                    <div class="card-codigo">${destacarTexto(infracao.codigo, query)}</div>
                    
                    <div class="card-descricao" title="${infracao.descricao}">
                        ${destacarTexto(infracao.descricao, query)}
                    </div>
                    
                    <div class="card-pontos">
                        <div class="pontos-badge">${infracao.pontos} pts</div>
                    </div>
                    
                    <div class="card-valor">
                        <div class="valor-badge">${formatarMoeda(infracao.valor_multa)}</div>
                    </div>
                    
                    <div class="card-gravidade">
                        <div class="gravidade-badge ${gravidadeCardClass}">${infracao.gravidade}</div>
                    </div>
                    
                    <div class="expand-button" onclick="toggleCard(this.closest('.infraction-card'))">
                        <i class="fas fa-chevron-down expand-icon"></i>
                        Ver mais detalhes
                    </div>
                </div>
                
                <!-- Seção Expandida (detalhes adicionais) -->
                <div class="card-details">
                    <div class="details-grid">
                        <div class="detail-item">
                            <div class="detail-label">Responsável</div>
                            <div class="detail-value">${infracao.responsavel || '-'}</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Órgão Autuador</div>
                            <div class="detail-value">${infracao.orgao_autuador || '-'}</div>
                        </div>
                        
                        <div class="detail-item">
                            <div class="detail-label">Artigos do CTB</div>
                            <div class="detail-value">${infracao.artigos_ctb || 'Não informado'}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    });
    
    cardsContainer.innerHTML = html;
    cardsContainer.style.display = 'block';
}

/**
 * Função principal que busca infrações na API e exibe os resultados
 * @param {string} query - Termo de pesquisa
 */
async function buscarInfracoes(query) {
    // Verificar se já há uma busca em andamento
    if (isSearchInProgress) {
        console.log("Busca já em andamento, ignorando nova solicitação");
        return;
    }
    
    // Marcar que há uma busca em andamento
    isSearchInProgress = true;
    
    // Limpar resultados anteriores e mostrar indicador de carregamento
    limparResultados();
    loadingElement.style.display = 'block';
    
    // Mostrar o container de resultados quando há busca
    const resultsContainer = document.querySelector('.results-container');
    if (resultsContainer) {
        resultsContainer.classList.add('active');
    }
    
    try {
        // Preparar parâmetros da requisição
        const params = new URLSearchParams({
            q: query,
            skip: CONFIG.DEFAULT_SKIP.toString(),
            limit: CONFIG.DEFAULT_LIMIT.toString()
        });
        
        // Fazer a requisição à API
        const response = await fetch(`${API_BASE_URL}/infracoes/pesquisa?${params}`, {
            method: 'GET',
            headers: DEFAULT_HEADERS
        });
        
        // Verificar se a resposta foi bem-sucedida
        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.detail || `Erro ${response.status}: ${response.statusText}`);
        }
        
        // Processar os dados retornados
        const data = await response.json();
        loadingElement.style.display = 'none';
        
        // Verificar se há resultados
        if (data.total === 0 || !data.resultados || data.resultados.length === 0) {
            if (data.sugestao) {
                const sugestaoHtml = `Nenhuma infração encontrada. Você quis dizer: <a href="#" onclick="buscarInfracoes('${data.sugestao}'); return false;">${data.sugestao}</a>?`;
                noResults.innerHTML = sugestaoHtml;
            } else {
                noResults.textContent = data.mensagem || 'Nenhuma infração encontrada. Tente outro termo de pesquisa.';
            }
            noResults.style.display = 'block';
            
            // Manter o container ativo mesmo sem resultados
            const resultsContainer = document.querySelector('.results-container');
            if (resultsContainer) {
                resultsContainer.classList.add('active');
            }
            return;
        }
        
        // Exibir o total de resultados encontrados
        totalResults.textContent = `Encontrados ${data.total} resultados para "${query}"`;
        totalResults.style.display = 'block';
        
        // Exibir resultados em cards ao invés de tabela
        exibirResultadosCards(data.resultados, query);
        
        // Ocultar a tabela tradicional
        resultsTable.style.display = 'none';
        
    } catch (error) {
        // Tratar erros que ocorrerem durante a busca
        console.error('Erro ao buscar infrações:', error);
        mostrarErro(error.message);
    } finally {
        // Independentemente do resultado, marcar que a busca terminou
        isSearchInProgress = false;
    }
}

/**
 * Anima o botão de pesquisa ao clicar
 */
function animarBotaoPesquisa() {
    searchBtn.classList.add('clicked');
    
    setTimeout(() => {
        searchBtn.classList.remove('clicked');
    }, 300);
}

// Tornar a função toggleCard global para ser acessível pelo onclick
window.toggleCard = toggleCard;

/**
 * Valida se o termo de pesquisa é adequado (palavra única ou código)
 * @param {string} query - Termo de pesquisa
 * @returns {Object} - {valido: boolean, mensagem: string}
 */
function validarTermoPesquisa(query) {
    // Verificar se é um código (números com possíveis traços/pontos)
    const isCodigoNumerico = /^[\d\-\.\s]+$/.test(query);
    if (isCodigoNumerico) {
        return { valido: true, mensagem: '' };
    }
    
    // Combinações permitidas (2 palavras específicas)
    const combinacoesPermitidas = [
        'cinto segurança', 'cinto seguranç', 'pneu desgastado', 'pneu ruim',
        'telefone celular', 'telefone movel', 'bebida alcoólica', 'bebida alcoolica',
        'velocidade máxima', 'velocidade maxima', 'faixa pedestre', 'faixa pedestres',
        'luz vermelha', 'sinal vermelho', 'carteira motorista', 'carteira habilitação',
        'carteira habilitaçao', 'documento veiculo', 'documento obrigatório',
        'documento obrigatorio', 'via preferencial', 'mão direção', 'mao direcao',
        'capacete proteção', 'capacete protecao', 'viseira capacete', 'placa identificação',
        'placa identificacao', 'dispositivo segurança', 'dispositivo seguranca'
    ];
    
    const queryLower = query.toLowerCase();
    if (combinacoesPermitidas.some(combo => queryLower.includes(combo))) {
        return { valido: true, mensagem: '' };
    }
    
    // Contar palavras (separadas por espaços)
    const palavras = query.trim().split(/\s+/).filter(palavra => palavra.length >= 2);
    
    if (palavras.length > 2) {
        return {
            valido: false,
            mensagem: `Use apenas 1 palavra ou código para pesquisar. Exemplos: <strong>cinto</strong>, <strong>bafômetro</strong>, <strong>velocidade</strong>, <strong>60501</strong>`
        };
    }
    
    return { valido: true, mensagem: '' };
}

// Adicionar evento de envio do formulário (único evento de busca)
searchForm.addEventListener('submit', function(event) {
    event.preventDefault();
    const query = searchInput.value.trim();
    
    // Validar o termo de pesquisa
    if (query.length < CONFIG.MIN_QUERY_LENGTH) {
        mostrarErro(`O termo de pesquisa deve ter pelo menos ${CONFIG.MIN_QUERY_LENGTH} caracteres.`);
        return;
    }
    
    if (query.length > CONFIG.MAX_QUERY_LENGTH) {
        mostrarErro(`O termo de pesquisa não pode ter mais que ${CONFIG.MAX_QUERY_LENGTH} caracteres.`);
        return;
    }
    
    // Validar se é palavra única ou código
    const validacao = validarTermoPesquisa(query);
    if (!validacao.valido) {
        mostrarErro(validacao.mensagem);
        return;
    }
    
    // Animar o botão e iniciar a pesquisa
    animarBotaoPesquisa();
    buscarInfracoes(query);
});

// Evento de input apenas para limpar mensagens de erro (sem pesquisa automática)
searchInput.addEventListener('input', function() {
    errorMessage.style.display = 'none';
});

// Funcionalidades adicionais para a página
document.addEventListener('DOMContentLoaded', function() {
    // Configurar botões de ação
    document.querySelectorAll('.action-button').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            // Scroll suave até o formulário de pesquisa
            const searchContainer = document.querySelector('.search-container');
            searchContainer.scrollIntoView({ behavior: 'smooth' });
            searchInput.focus();
        });
    });
    
    // Adicionar evento de clique ao botão de pesquisa para animação
    searchBtn.addEventListener('click', function() {
        animarBotaoPesquisa();
    });
    
    // Inicializar o foco no campo de pesquisa ao carregar a página
    searchInput.focus();
});