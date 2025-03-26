// Função para controlar o Modal de Notícias
document.addEventListener('DOMContentLoaded', function() {
    // Selecionar o botão de notícias corretamente
    const newsBtn = document.querySelector('a[href="/noticias"]');
    const modal = document.getElementById('news-modal');
    const closeBtn = document.querySelector('.close-modal');
    
    // Evento para abrir o modal
    if (newsBtn) {
        newsBtn.addEventListener('click', function(e) {
            e.preventDefault(); // Impedir o comportamento padrão do link
            modal.classList.add('show');
            // Impedir rolagem da página quando o modal está aberto
            document.body.style.overflow = 'hidden';
        });
    }
    
    // Evento para fechar o modal
    if (closeBtn) {
        closeBtn.addEventListener('click', function() {
            modal.classList.remove('show');
            // Restaurar rolagem da página
            document.body.style.overflow = 'auto';
        });
    }
    
    // Fechar o modal se clicar fora dele
    window.addEventListener('click', function(e) {
        if (e.target === modal) {
            modal.classList.remove('show');
            document.body.style.overflow = 'auto';
        }
    });
    
    // Fechar o modal com a tecla ESC
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape' && modal.classList.contains('show')) {
            modal.classList.remove('show');
            document.body.style.overflow = 'auto';
        }
    });
    
    // Evento do botão de contato
    const contactBtn = document.querySelector('.contact-btn');
    
    if (contactBtn) {
        contactBtn.addEventListener('click', function() {
            // Fechar o modal primeiro
            modal.classList.remove('show');
            document.body.style.overflow = 'auto';
            
            // Esperamos um pouco antes de rolar para dar tempo do modal fechar
            setTimeout(() => {
                // Rolar suavemente até o rodapé
                const footer = document.getElementById('footer');
                if (footer) {
                    footer.scrollIntoView({ behavior: 'smooth' });
                    
                    // Destacar visualmente a seção de contato no rodapé
                    const contactSection = document.querySelector('.footer-section:first-child');
                    if (contactSection) {
                        contactSection.classList.add('highlight-contact');
                        
                        setTimeout(() => {
                            contactSection.classList.remove('highlight-contact');
                        }, 3000);
                    }
                }
            }, 300);
        });
    }
});