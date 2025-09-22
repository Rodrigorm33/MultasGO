// URL base da API - Configurada para funcionar tanto em desenvolvimento quanto em produção
const API_BASE_URL = window.location.origin + '/api/v1';

// Configurações da API
const CONFIG = {
    MIN_QUERY_LENGTH: 2,
    MAX_QUERY_LENGTH: 15,  // CORRIGIDO: 15 caracteres máximo
    DEFAULT_LIMIT: 100,
    DEFAULT_SKIP: 0
};

// Headers padrão para requisições
const DEFAULT_HEADERS = {
    'Accept': 'application/json',
    'Content-Type': 'application/json'
};

// Elementos da página
let searchForm = null;
let searchInput = null;
let searchBtn = null;
let resultsTable = null;
let resultsBody = null;
let loadingElement = null;
let errorMessage = null;
let noResults = null;
let totalResults = null;

// Função para inicializar elementos
function inicializarElementos() {
    searchForm = document.getElementById('search-form');
    searchInput = document.getElementById('search-input');
    searchBtn = document.getElementById('search-btn');
    resultsTable = document.getElementById('results-table');
    resultsBody = document.getElementById('results-body');
    loadingElement = document.getElementById('loading');
    errorMessage = document.getElementById('error-message');
    noResults = document.getElementById('no-results');
    totalResults = document.getElementById('total-results');
    
    // Verificar se elementos existem
    console.log('🔍 Verificando elementos HTML:');
    console.log('searchForm:', !!searchForm);
    console.log('searchInput:', !!searchInput);
    console.log('searchBtn:', !!searchBtn);
    console.log('errorMessage:', !!errorMessage);
    
    return searchForm && searchInput && searchBtn && errorMessage;
}

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
    errorMessage.innerHTML = mensagem || 'Ocorreu um erro na pesquisa. Por favor, tente novamente.';
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
                // Destacar a palavra sugerida com a função existente
                const sugestaoDestacada = destacarTexto(data.sugestao, data.sugestao);
                const sugestaoHtml = `Você quis dizer: <a href="#" class="suggestion-link" onclick="buscarInfracoes('${data.sugestao}'); return false;">${sugestaoDestacada}</a>?`;
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
    // VALIDAÇÃO 1: Tamanho mínimo
    if (query.length < CONFIG.MIN_QUERY_LENGTH) {
        return {
            valido: false,
            mensagem: `Digite pelo menos ${CONFIG.MIN_QUERY_LENGTH} caracteres para pesquisar.`
        };
    }
    
    // VALIDAÇÃO 2: Tamanho máximo RESTRITO - 15 caracteres
    if (query.length > CONFIG.MAX_QUERY_LENGTH) {
        return {
            valido: false,
            mensagem: `Use apenas 1 palavra ou código para pesquisar. Exemplos: <strong>cinto</strong>, <strong>bafômetro</strong>, <strong>velocidade</strong>, <strong>60501</strong>`
        };
    }
    
    // VALIDAÇÃO 3: Caracteres especiais não permitidos
    const caracteresEspeciais = /[^a-zA-Z0-9áàãâäéêëíîïóôõöúûüçñ\s\-]/;
    if (caracteresEspeciais.test(query)) {
        return {
            valido: false,
            mensagem: `Use apenas 1 palavra ou código para pesquisar. Exemplos: <strong>cinto</strong>, <strong>bafômetro</strong>, <strong>velocidade</strong>, <strong>60501</strong>`
        };
    }
    
    // VALIDAÇÃO 4: Verificar se é código numérico (permitir sempre)
    const isCodigoNumerico = /^[\d\-\.\s]+$/.test(query);
    if (isCodigoNumerico) {
        return { valido: true, mensagem: '' };
    }
    
    // VALIDAÇÃO 5: Múltiplas palavras - REJEITAR SEMPRE
    const palavras = query.trim().split(/\s+/).filter(palavra => palavra.length >= 2);
    if (palavras.length > 1) {
        return {
            valido: false,
            mensagem: `Use apenas 1 palavra ou código para pesquisar. Exemplos: <strong>cinto</strong>, <strong>bafômetro</strong>, <strong>velocidade</strong>, <strong>60501</strong>`
        };
    }
    
    // VALIDAÇÃO 6: Espaços no meio da palavra (detectar tentativas de múltiplas palavras)
    if (query.includes(' ') && !isCodigoNumerico) {
        return {
            valido: false,
            mensagem: `Use apenas 1 palavra ou código para pesquisar. Exemplos: <strong>cinto</strong>, <strong>bafômetro</strong>, <strong>velocidade</strong>, <strong>60501</strong>`
        };
    }
    
    return { valido: true, mensagem: '' };
}

/**
 * Mostra popup quando usuário digita espaço
 */
function mostrarPopupEspaco() {
    // Remover popup existente se houver
    const popupExistente = document.getElementById('popup-espaco');
    if (popupExistente) {
        popupExistente.remove();
    }
    
    // Criar popup
    const popup = document.createElement('div');
    popup.id = 'popup-espaco';
    popup.innerHTML = `
        <div class="popup-content">
            <span class="popup-close" onclick="fecharPopupEspaco()">&times;</span>
            <h3>⚠️ Atenção!</h3>
            <p>Digite apenas <strong>uma palavra</strong> ou <strong>código</strong> para pesquisar.</p>
            <p><strong>Exemplos:</strong> cinto, bafômetro, velocidade, 60501</p>
            <button class="popup-go-btn" onclick="fecharPopupEspaco()">GO!</button>
        </div>
    `;
    popup.style.cssText = `
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background-color: rgba(0,0,0,0.5);
        display: flex;
        justify-content: center;
        align-items: center;
        z-index: 10000;
    `;
    
    const popupContent = popup.querySelector('.popup-content');
    popupContent.style.cssText = `
        background: white;
        padding: 20px;
        border-radius: 10px;
        max-width: 400px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        animation: fadeIn 0.3s ease-out;
        position: relative;
    `;
    
    const closeBtn = popup.querySelector('.popup-close');
    closeBtn.style.cssText = `
        position: absolute;
        top: 10px;
        right: 15px;
        font-size: 24px;
        cursor: pointer;
        color: #999;
    `;
    
    // Estilo do botão GO!
    const goBtn = popup.querySelector('.popup-go-btn');
    goBtn.style.cssText = `
        margin-top: 20px;
        padding: 12px 32px;
        background: #27ae60;
        color: white;
        border: none;
        border-radius: 25px;
        font-size: 18px;
        font-weight: bold;
        cursor: pointer;
        box-shadow: 0 2px 8px rgba(39,174,96,0.15);
        transition: background 0.2s;
    `;
    goBtn.onmouseover = function() { goBtn.style.background = '#219150'; };
    goBtn.onmouseout = function() { goBtn.style.background = '#27ae60'; };
    
    // Adicionar CSS de animação
    const style = document.createElement('style');
    style.textContent = `
        @keyframes fadeIn {
            from { opacity: 0; transform: scale(0.8); }
            to { opacity: 1; transform: scale(1); }
        }
    `;
    document.head.appendChild(style);
    
    document.body.appendChild(popup);
    // Removido o setTimeout para não fechar automaticamente
}

/**
 * Fecha o popup de espaço
 */
function fecharPopupEspaco() {
    const popup = document.getElementById('popup-espaco');
    if (popup) {
        popup.remove();
    }
}

// Tornar função global
window.fecharPopupEspaco = fecharPopupEspaco;

// Funcionalidades adicionais para a página
document.addEventListener('DOMContentLoaded', function() {
    console.log('🚀 DOM carregado, inicializando sistema...');
    
    // Inicializar elementos
    if (!inicializarElementos()) {
        console.error('❌ ERRO: Elementos HTML não encontrados!');
        return;
    }
    
    console.log('✅ Elementos HTML encontrados, anexando eventos...');
    
    // Anexar eventos apenas se elementos existem
    if (searchForm && searchInput && searchBtn && errorMessage) {
        
        // Evento de envio do formulário
        searchForm.addEventListener('submit', function(event) {
            console.log('📝 Submit do formulário acionado');
            event.preventDefault();
            const query = searchInput.value.trim();
            
            console.log(`🔍 Query submetida: "${query}"`);
            
            // Validar o termo de pesquisa
            if (query.length < CONFIG.MIN_QUERY_LENGTH) {
                console.log('❌ Query muito curta');
                mostrarErro(`O termo de pesquisa deve ter pelo menos ${CONFIG.MIN_QUERY_LENGTH} caracteres.`);
                return;
            }
            
            if (query.length > CONFIG.MAX_QUERY_LENGTH) {
                console.log('❌ Query muito longa');
                mostrarErro(`O termo de pesquisa não pode ter mais que ${CONFIG.MAX_QUERY_LENGTH} caracteres.`);
                return;
            }
            
            // Validar se é palavra única ou código
            const validacao = validarTermoPesquisa(query);
            if (!validacao.valido) {
                console.log('❌ Validação falhou:', validacao.mensagem);
                mostrarErro(validacao.mensagem);
                return;
            }
            
            console.log('✅ Validação passou, iniciando busca...');
            
            // Animar o botão e iniciar a pesquisa
            animarBotaoPesquisa();
            buscarInfracoes(query);
        });

        // Evento de input para validação em tempo real
        searchInput.addEventListener('input', function(e) {
            const valor = e.target.value;
            console.log(`⌨️  Input: "${valor}" (${valor.length} chars)`);
            
            // VALIDAÇÃO 1: Limitar a 15 caracteres automaticamente
            if (valor.length > CONFIG.MAX_QUERY_LENGTH) {
                console.log('🚫 Limitando caracteres');
                e.target.value = valor.substring(0, CONFIG.MAX_QUERY_LENGTH);
                mostrarErro('Use apenas 1 palavra ou código para pesquisar. Exemplos: <strong>cinto</strong>, <strong>bafômetro</strong>, <strong>velocidade</strong>, <strong>60501</strong>');
                return;
            }
            
            // VALIDAÇÃO 2: Detectar espaços e mostrar popup
            if (valor.includes(' ')) {
                console.log('🚫 Espaços detectados, removendo...');
                // Remover espaços automaticamente
                e.target.value = valor.replace(/\s/g, '');
                mostrarPopupEspaco();
                return;
            }
            
            // VALIDAÇÃO 3: Impedir caracteres especiais
            const caracteresEspeciais = /[^a-zA-Z0-9áàãâäéêëíîïóôõöúûüçñ\-]/;
            if (caracteresEspeciais.test(valor)) {
                console.log('🚫 Caracteres especiais detectados, removendo...');
                e.target.value = valor.replace(/[^a-zA-Z0-9áàãâäéêëíîïóôõöúûüçñ\-]/g, '');
                mostrarErro('Use apenas 1 palavra ou código para pesquisar. Exemplos: <strong>cinto</strong>, <strong>bafômetro</strong>, <strong>velocidade</strong>, <strong>60501</strong>');
                return;
            }
            
            // Se chegou aqui, limpar mensagens de erro
            errorMessage.style.display = 'none';
        });

        // Adicionar evento para impedir espaços com keydown também
        searchInput.addEventListener('keydown', function(e) {
            // Impedir espaço (código 32)
            if (e.keyCode === 32) {
                console.log('🚫 Espaço bloqueado no keydown');
                e.preventDefault();
                mostrarPopupEspaco();
                return false;
            }
        });

        // Adicionar evento para impedir colar texto com espaços
        searchInput.addEventListener('paste', function(e) {
            console.log('📋 Paste detectado');
            // Aguardar o paste processar
            setTimeout(() => {
                const valor = e.target.value;
                console.log(`📋 Valor após paste: "${valor}"`);
                
                // Limitar caracteres
                if (valor.length > CONFIG.MAX_QUERY_LENGTH) {
                    console.log('🚫 Limitando paste');
                    e.target.value = valor.substring(0, CONFIG.MAX_QUERY_LENGTH);
                }
                
                // Remover espaços
                if (valor.includes(' ')) {
                    console.log('🚫 Removendo espaços do paste');
                    e.target.value = valor.replace(/\s/g, '');
                    mostrarPopupEspaco();
                }
                
                // Remover caracteres especiais
                const caracteresEspeciais = /[^a-zA-Z0-9áàãâäéêëíîïóôõöúûüçñ\-]/;
                if (caracteresEspeciais.test(valor)) {
                    console.log('🚫 Removendo caracteres especiais do paste');
                    e.target.value = valor.replace(/[^a-zA-Z0-9áàãâäéêëíîïóôõöúûüçñ\-]/g, '');
                }
            }, 10);
        });
        
        console.log('✅ Todos os eventos anexados com sucesso!');
    } else {
        console.error('❌ ERRO: Não foi possível anexar eventos aos elementos');
    }
    
    // Configurar botões de ação
    document.querySelectorAll('.action-button').forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            // Scroll suave até o formulário de pesquisa
            const searchContainer = document.querySelector('.search-container');
            if (searchContainer) {
                searchContainer.scrollIntoView({ behavior: 'smooth' });
            }
            if (searchInput) {
                searchInput.focus();
            }
        });
    });
    
    // Adicionar evento de clique ao botão de pesquisa para animação
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            animarBotaoPesquisa();
        });
    }
    
    // Inicializar o foco no campo de pesquisa ao carregar a página
    if (searchInput) {
        searchInput.focus();
        console.log('✅ Foco no campo de pesquisa');
    }
    
    console.log('🎉 Sistema inicializado com sucesso!');
});