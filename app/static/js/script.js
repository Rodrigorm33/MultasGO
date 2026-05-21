// URL base da API - Configurada para funcionar tanto em desenvolvimento quanto em produção
const API_BASE_URL = window.location.origin + '/api/v1';

// Configurações da API
const CONFIG = {
    MIN_QUERY_LENGTH: 2,
    MAX_QUERY_LENGTH: 200,  // Busca livre (estilo Google) com limite seguro
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
    // Segurança: evitar XSS. Mensagens devem ser texto puro.
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

      // Se o usuário clicou em um resultado do preview, abrir o card correspondente.
      try {
          const codigo = window._pendingOpenCodigo;
          if (codigo) {
              window._pendingOpenCodigo = null;
              const esc = (s) => {
                  // `codigo` é bem restrito (digits/hifen), mas mantém defensivo.
                  if (window.CSS && typeof window.CSS.escape === 'function') return window.CSS.escape(String(s));
                  return String(s).replace(/["\\]/g, '\\$&');
              };
              const selector = `.infraction-card[data-codigo="${esc(codigo)}"]`;
              const card = cardsContainer.querySelector(selector);
              if (card) {
                  toggleCard(card);
                  card.scrollIntoView({ behavior: 'smooth', block: 'center' });
              }
          }
      } catch (e) {
          console.warn('Falha ao abrir card do preview:', e);
      }
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
                // Segurança: não usar onclick inline nem innerHTML com dados dinâmicos.
                noResults.textContent = 'Você quis dizer: ';
                const link = document.createElement('a');
                link.href = '#';
                link.className = 'suggestion-link';
                link.textContent = data.sugestao;
                link.addEventListener('click', (e) => {
                    e.preventDefault();
                    buscarInfracoes(data.sugestao);
                });
                noResults.appendChild(link);
                noResults.appendChild(document.createTextNode('?'));
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
    
    // VALIDAÇÃO 2: Tamanho máximo
    if (query.length > CONFIG.MAX_QUERY_LENGTH) {
        return {
            valido: false,
            mensagem: `Sua busca é muito longa. Use até ${CONFIG.MAX_QUERY_LENGTH} caracteres.`
        };
    }
    
    // VALIDAÇÃO 3: caracteres de controle (raros, mas mantém defensivo)
    const controlChars = /[\x00-\x1F\x7F]/;
    if (controlChars.test(query)) {
        return { valido: false, mensagem: 'O termo de pesquisa contém caracteres inválidos.' };
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
                mostrarErro(`Sua busca é muito longa. Use até ${CONFIG.MAX_QUERY_LENGTH} caracteres.`);
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
            try { fecharOverlay(); } catch (e) { /* noop */ }
            buscarInfracoes(query);
        });

        // Evento de input para validação em tempo real
        searchInput.addEventListener('input', function(e) {
            const valor = e.target.value;
            console.log(`⌨️  Input: "${valor}" (${valor.length} chars)`);
            
            // Limitar tamanho automaticamente (sem bloquear espaços)
            if (valor.length > CONFIG.MAX_QUERY_LENGTH) {
                console.log('🚫 Limitando caracteres');
                e.target.value = valor.substring(0, CONFIG.MAX_QUERY_LENGTH);
                mostrarErro(`Sua busca é muito longa. Use até ${CONFIG.MAX_QUERY_LENGTH} caracteres.`);
                return;
            }
            
            // Se chegou aqui, limpar mensagens de erro
            errorMessage.style.display = 'none';
        });

        // Keydown: bloquear espaço + navegação autocomplete
        searchInput.addEventListener('keydown', function(e) {
            // Navegação do autocomplete (arrows, enter, escape)
            const dropdown = document.getElementById('autocomplete-dropdown');
            if (dropdown && dropdown.classList.contains('active')) {
                const items = dropdown.querySelectorAll('.autocomplete-item');
                if (items.length) {
                    if (e.key === 'ArrowDown') {
                        e.preventDefault();
                        window._acSelectedIndex = Math.min((window._acSelectedIndex || -1) + 1, items.length - 1);
                        items.forEach((item, i) => item.classList.toggle('selected', i === window._acSelectedIndex));
                        return;
                    } else if (e.key === 'ArrowUp') {
                        e.preventDefault();
                        window._acSelectedIndex = Math.max((window._acSelectedIndex || 0) - 1, -1);
                        items.forEach((item, i) => item.classList.toggle('selected', i === window._acSelectedIndex));
                        return;
                    } else if (e.key === 'Enter' && window._acSelectedIndex >= 0) {
                        e.preventDefault();
                        searchInput.value = items[window._acSelectedIndex].dataset.termo;
                        fecharAutocomplete();
                        buscarInfracoes(searchInput.value);
                        return;
                    } else if (e.key === 'Escape') {
                        fecharAutocomplete();
                        return;
                    }
                }
            }
            // Impedir espaco (codigo 32)
            // Espaço permitido (busca livre)
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
    
    // === SEARCH OVERLAY (Sugestões + Preview) ===
    let smartTimer = null;
    let smartController = null;
    window._ovSelectedIndex = -1;
    const SMART_DEBOUNCE_MS = 240;

    function criarOverlayBusca() {
        if (document.getElementById('search-overlay')) return;
        const overlay = document.createElement('div');
        overlay.className = 'autocomplete-dropdown search-overlay';
        overlay.id = 'search-overlay';
        const container = document.querySelector('.search-container');
        if (container) {
            container.appendChild(overlay);
        }
    }

    function fecharOverlay() {
        const overlay = document.getElementById('search-overlay');
        if (overlay) {
            overlay.classList.remove('active');
            overlay.replaceChildren();
        }
        window._ovSelectedIndex = -1;
    }

    function _addSectionTitle(overlay, title) {
        const el = document.createElement('div');
        el.className = 'overlay-section-title';
        el.textContent = title;
        overlay.appendChild(el);
    }

    function _addDidYouMean(overlay, sugestao) {
        const wrap = document.createElement('div');
        wrap.className = 'overlay-did-you-mean';
        const txt1 = document.createTextNode('Você quis dizer: ');
        const link = document.createElement('a');
        link.href = '#';
        link.textContent = sugestao;
        link.addEventListener('click', (e) => {
            e.preventDefault();
            if (!searchInput) return;
            searchInput.value = sugestao;
            fecharOverlay();
            buscarInfracoes(sugestao);
        });
        wrap.appendChild(txt1);
        wrap.appendChild(link);
        overlay.appendChild(wrap);
    }

    function _renderHighlightedText(target, text, needle) {
        // Render seguro (sem innerHTML): destaca a primeira ocorrência de `needle`.
        const full = String(text || '');
        const n = String(needle || '').trim();
        if (!n) {
            target.textContent = full;
            return;
        }
        const idx = full.toLowerCase().indexOf(n.toLowerCase());
        if (idx < 0) {
            target.textContent = full;
            return;
        }
        const before = full.slice(0, idx);
        const match = full.slice(idx, idx + n.length);
        const after = full.slice(idx + n.length);
        if (before) target.appendChild(document.createTextNode(before));
        const span = document.createElement('span');
        span.className = 'match';
        span.textContent = match;
        target.appendChild(span);
        if (after) target.appendChild(document.createTextNode(after));
    }

    function _makeOverlayItem({ label, action, query, codigo, prefix }) {
        const item = document.createElement('div');
        item.className = 'overlay-item';
        item.tabIndex = 0;
        item.dataset.action = action || 'search';
        if (query) item.dataset.query = query;
        if (codigo) item.dataset.codigo = codigo;

        const text = document.createElement('div');
        text.className = 'overlay-item-text';
        _renderHighlightedText(text, label, prefix);
        item.appendChild(text);

        item.addEventListener('click', () => _handleOverlayAction(item));
        return item;
    }

    function _makePreviewItem({ infracao, currentQuery }) {
        const item = document.createElement('div');
        item.className = 'overlay-item';
        item.tabIndex = 0;
        item.dataset.action = 'open_result';
        item.dataset.query = currentQuery;
        item.dataset.codigo = infracao.codigo;

        const main = document.createElement('div');
        main.className = 'overlay-result-main';

        const code = document.createElement('div');
        code.className = 'overlay-result-code';
        code.textContent = infracao.codigo || '';
        main.appendChild(code);

        const desc = document.createElement('div');
        desc.className = 'overlay-result-desc';
        desc.textContent = infracao.descricao || '';
        main.appendChild(desc);

        const meta = document.createElement('div');
        meta.className = 'overlay-result-meta';
        const pts = Number(infracao.pontos || 0);
        const grav = String(infracao.gravidade || '').trim();
        meta.textContent = `${pts} pts${grav ? ` · ${grav}` : ''}`;
        main.appendChild(meta);

        item.appendChild(main);
        item.addEventListener('click', () => _handleOverlayAction(item));
        return item;
    }

    function _handleOverlayAction(item) {
        const action = item.dataset.action;
        if (action === 'search') {
            const q = item.dataset.query || item.textContent || '';
            if (!searchInput) return;
            searchInput.value = q;
            fecharOverlay();
            buscarInfracoes(q);
            return;
        }
        if (action === 'open_result') {
            const q = item.dataset.query || (searchInput ? searchInput.value : '');
            const codigo = item.dataset.codigo;
            if (codigo) window._pendingOpenCodigo = codigo;
            fecharOverlay();
            buscarInfracoes(String(q || '').trim());
            return;
        }
    }

    async function buscarSmartOverlay(textoDigitado) {
        const q = String(textoDigitado || '');
        if (!q || q.trim().length < CONFIG.MIN_QUERY_LENGTH) {
            fecharOverlay();
            return;
        }

        // Cancelar request anterior (evita race conditions).
        try {
            if (smartController) smartController.abort();
        } catch (e) { /* noop */ }
        smartController = new AbortController();

        const url = `${API_BASE_URL}/infracoes/smart?q=${encodeURIComponent(q)}&limite_sugestoes=8&limite_preview=5`;
        try {
            const resp = await fetch(url, { headers: DEFAULT_HEADERS, signal: smartController.signal });
            if (!resp.ok) return;
            const data = await resp.json();
            renderizarOverlay(data, q);
        } catch (e) {
            if (e && e.name === 'AbortError') return;
            console.warn('Smart overlay error:', e);
        }
    }

    function renderizarOverlay(data, qOriginal) {
        const overlay = document.getElementById('search-overlay');
        if (!overlay) return;

        const sugestoes = Array.isArray(data && data.sugestoes) ? data.sugestoes : [];
        const preview = (data && data.preview) ? data.preview : null;
        const resultados = preview && Array.isArray(preview.resultados) ? preview.resultados : [];
        const total = preview && typeof preview.total === 'number' ? preview.total : 0;
        const sugestaoCorrecao = preview && preview.sugestao ? String(preview.sugestao) : '';

        overlay.replaceChildren();
        window._ovSelectedIndex = -1;

        if (sugestaoCorrecao) {
            _addDidYouMean(overlay, sugestaoCorrecao);
        }

        const prefix = String(qOriginal || '').trim().split(/\s+/).pop() || '';

        if (sugestoes.length) {
            _addSectionTitle(overlay, 'Sugestoes');
            sugestoes.slice(0, 8).forEach((s) => {
                const termo = (s && s.termo) ? String(s.termo) : '';
                if (!termo) return;
                overlay.appendChild(_makeOverlayItem({ label: termo, action: 'search', query: termo, prefix }));
            });
        }

        if (resultados.length) {
            _addSectionTitle(overlay, `Resultados (${total})`);
            resultados.slice(0, 5).forEach((r) => {
                overlay.appendChild(_makePreviewItem({ infracao: r, currentQuery: String(qOriginal || '').trim() }));
            });
        } else if (!sugestoes.length) {
            fecharOverlay();
            return;
        }

        overlay.classList.add('active');
    }

    // Conectar ao input (debounced)
    if (searchInput) {
        searchInput.addEventListener('input', function(e) {
            clearTimeout(smartTimer);
            // Não usar trim aqui, para preservar contexto (ex.: espaço no final).
            const val = String(e.target.value || '');
            smartTimer = setTimeout(() => buscarSmartOverlay(val), SMART_DEBOUNCE_MS);
        });
    }

    // Navegação por teclado no overlay
    if (searchInput) {
        searchInput.addEventListener('keydown', function(e) {
            const overlay = document.getElementById('search-overlay');
            if (!overlay || !overlay.classList.contains('active')) return;
            const items = overlay.querySelectorAll('.overlay-item');
            if (!items.length) return;

            if (e.key === 'ArrowDown') {
                e.preventDefault();
                window._ovSelectedIndex = Math.min((window._ovSelectedIndex || -1) + 1, items.length - 1);
                items.forEach((it, i) => it.classList.toggle('selected', i === window._ovSelectedIndex));
                return;
            }
            if (e.key === 'ArrowUp') {
                e.preventDefault();
                window._ovSelectedIndex = Math.max((window._ovSelectedIndex || 0) - 1, -1);
                items.forEach((it, i) => it.classList.toggle('selected', i === window._ovSelectedIndex));
                return;
            }
            if (e.key === 'Enter' && window._ovSelectedIndex >= 0) {
                e.preventDefault();
                _handleOverlayAction(items[window._ovSelectedIndex]);
                return;
            }
            if (e.key === 'Escape') {
                fecharOverlay();
                return;
            }
        });
    }

    // Fechar ao clicar fora
    document.addEventListener('click', function(e) {
        const overlay = document.getElementById('search-overlay');
        if (!overlay) return;
        if (searchInput && (searchInput.contains(e.target) || overlay.contains(e.target))) return;
        fecharOverlay();
    });

    criarOverlayBusca();

    // Inicializar o foco no campo de pesquisa ao carregar a página
    if (searchInput) {
        searchInput.focus();
    }

    console.log('Sistema inicializado com sucesso!');
});
