// Função para rodar as frases engraçadas no container vazio
document.addEventListener('DOMContentLoaded', function() {
    // Array com as frases engraçadas e seus emojis
    const placeholderQuotes = [
        {emoji: '🚦', text: 'Parado no sinal vermelho? Digite algo para seguir viagem!'},
        {emoji: '🏍️', text: 'Sem capacete e sem destino... Digite algo para pegar a estrada!'},
        // {emoji: '🚗', text: 'O carro tá na garagem... Bora colocar ele na pista? Pesquise algo!'},
        {emoji: '🛑', text: 'Sem busca, sem multa... Mas será que você tá dirigindo certo?'},
        {emoji: '🚔', text: 'Até agora, sem infrações... Mas digite algo para ter certeza!'},
        {emoji: '⛽', text: 'Tanque cheio, motor ligado... Só falta você acelerar essa busca!'},
        {emoji: '🚧', text: 'Sem pesquisa, sem trânsito! Mas também sem informação... Digita aí!'},
        {emoji: '🚙', text: 'Seu motor tá em ponto morto... Engata uma busca e acelera!'},
        {emoji: '📋', text: 'Ainda sem movimento na pista... Insira um termo e bora rodar!'},
        {emoji: '🔍', text: 'Sem pesquisa até agora... Alguma infração escondida por aí?'}
    ];
    
    // Criação do elemento para exibir as frases
    const resultsContainer = document.querySelector('.results-container');
    
    // Verificar se já existe o elemento placeholder
    let placeholderElement = document.querySelector('.placeholder-quotes');
    
    if (!placeholderElement) {
        // Criar o elemento se ele não existir
        placeholderElement = document.createElement('div');
        placeholderElement.className = 'placeholder-quotes';
        resultsContainer.appendChild(placeholderElement);
    }
    
    // Função para atualizar o conteúdo com uma frase aleatória
    function updatePlaceholder() {
        // Verificar se devemos exibir o placeholder
        const resultsTable = document.getElementById('results-table');
        const noResults = document.getElementById('no-results');
        const loading = document.getElementById('loading');
        const errorMessage = document.getElementById('error-message');
        
        // Verificação melhorada que considera explicitamente o estado "table" para a tabela
        const hasResults = resultsTable.style.display === 'table';
        const hasNoResults = noResults.style.display === 'block';
        const isLoading = loading.style.display === 'block';
        const hasError = errorMessage.style.display === 'block';
        
        // Só mostrar placeholder se NENHUM dos outros elementos estiver visível
        if (!hasResults && !hasNoResults && !isLoading && !hasError) {
            // Selecionar uma frase aleatória
            const randomIndex = Math.floor(Math.random() * placeholderQuotes.length);
            const quote = placeholderQuotes[randomIndex];
            
            // Atualizar o conteúdo
            placeholderElement.innerHTML = `
                <span class="emoji">${quote.emoji}</span>
                <span class="text">${quote.text}</span>
            `;
            
            // Tornar visível
            placeholderElement.style.display = 'block';
            
            // Resetar a animação
            placeholderElement.style.animation = 'none';
            placeholderElement.offsetHeight; // Trigger reflow
            placeholderElement.style.animation = 'fadeInOut 8s ease-in-out';
        } else {
            // Se qualquer outro elemento estiver visível, garantir que o placeholder esteja oculto
            placeholderElement.style.display = 'none';
        }
    }
    
    // Iniciar a rotação de frases
    updatePlaceholder();
    setInterval(updatePlaceholder, 8000); // Trocar a cada 8 segundos
    
    // Adicionar evento quando o usuário clica no campo de pesquisa para esconder o placeholder
    const searchInput = document.getElementById('search-input');
    if (searchInput) {
        searchInput.addEventListener('focus', function() {
            placeholderElement.style.opacity = '0.4';
        });
        
        searchInput.addEventListener('blur', function() {
            placeholderElement.style.opacity = '0.8';
        });
    }
    
    // Adicionar observação para elementos da UI que possam aparecer
    const observer = new MutationObserver(function(mutations) {
        updatePlaceholder(); // Atualizar o placeholder quando houver mudanças
    });
    
    // Observar mudanças de estilo nos elementos principais
    const elementsToObserve = [
        document.getElementById('results-table'),
        document.getElementById('no-results'),
        document.getElementById('loading'),
        document.getElementById('error-message')
    ];
    
    // Iniciar observação para cada elemento
    elementsToObserve.forEach(element => {
        if (element) {
            observer.observe(element, { 
                attributes: true, 
                attributeFilter: ['style'] 
            });
        }
    });
    
    // Adicionar ouvintes de eventos diretamente para os botões de pesquisa
    const searchBtn = document.getElementById('search-btn');
    const searchForm = document.getElementById('search-form');
    
    if (searchBtn) {
        searchBtn.addEventListener('click', function() {
            // Ocultar o placeholder imediatamente ao iniciar uma pesquisa
            placeholderElement.style.display = 'none';
        });
    }
    
    if (searchForm) {
        searchForm.addEventListener('submit', function() {
            // Ocultar o placeholder imediatamente ao enviar o formulário
            placeholderElement.style.display = 'none';
        });
    }
});