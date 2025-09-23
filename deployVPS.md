# Deploy VPS - Guia Completo MultasGO

## 🔍 Por que funcionou local mas não na VPS?

### Local (Desenvolvimento)
```bash
python start.py
# Roda direto na porta 8080
# Browser acessa: http://localhost:8080
# SEM proxy, SEM SSL, SEM nginx
```

### VPS (Produção)
```bash
# Aplicação roda na porta 8000
# Nginx faz proxy reverso
# SSL configurado
# Domínio: multasgo.com.br
```

## 🚨 O Problema Específico

1. **Nginx porta 80**: Só redirecionava para HTTPS (sem proxy)
2. **Nginx porta 443**: Tinha proxy MAS SSL pode ter problemas
3. **JavaScript do explorador**: Fazia requests para `/api/v1/infracoes/explorador`
4. **Local**: Funcionava direto
5. **VPS**: Nginx não sabia rotear a API na porta 80

## 📝 Checklist para Próximos Deploys

### 1. Antes de Fazer Deploy
```bash
# Testar se todos os endpoints funcionam
curl http://localhost:8080/
curl http://localhost:8080/explorador
curl http://localhost:8080/api/v1/infracoes/explorador
curl http://localhost:8080/api/v1/infracoes/pesquisa?q=velocidade
```

### 2. Deploy no GitHub
```bash
# Verificar se não há arquivos sensíveis
git status
git add .
git commit -m "Deploy: Nova versão"
git push origin main
```

### 3. Deploy na VPS
```bash
# Conectar na VPS
ssh root@IP-DA-VPS

# Fazer backup e limpar
cd /var/www
rm -rf multasgo_old
mv multasgo multasgo_old  # Backup de segurança

# Clonar nova versão
git clone https://github.com/USUARIO/REPO.git multasgo
cd multasgo

# Instalar dependências
pip3 install -r requirements.txt

# Configurar .env
cp .env.example .env
# Editar .env com configurações corretas
```

### 4. Configurar Nginx Corretamente
```nginx
# /etc/nginx/sites-available/multasgo
server {
    listen 80;
    server_name SEU-DOMINIO.com www.SEU-DOMINIO.com;

    # Servir arquivos estáticos
    location /static/ {
        alias /var/www/multasgo/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Proxy para FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name SEU-DOMINIO.com www.SEU-DOMINIO.com;

    # SSL certificates
    ssl_certificate /etc/letsencrypt/live/SEU-DOMINIO.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/SEU-DOMINIO.com/privkey.pem;

    # Servir arquivos estáticos
    location /static/ {
        alias /var/www/multasgo/app/static/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Proxy para FastAPI
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 5. Configurar Systemd Service
```bash
# /etc/systemd/system/multasgo.service
[Unit]
Description=MultasGO - Sistema de Consulta de Infracoes de Transito
After=network.target

[Service]
Type=exec
User=root
Group=root
WorkingDirectory=/var/www/multasgo
Environment=PYTHONPATH=/var/www/multasgo
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2
Restart=always
RestartSec=3
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### 6. Ativar Serviços
```bash
# Recarregar configurações
systemctl daemon-reload

# Testar e recarregar Nginx
nginx -t
systemctl reload nginx

# Iniciar aplicação
systemctl start multasgo
systemctl enable multasgo
systemctl status multasgo
```

### 7. Testar na VPS Após Deploy
```bash
# Testar TODOS os endpoints
curl http://SEU-DOMINIO.com/
curl http://SEU-DOMINIO.com/explorador
curl http://SEU-DOMINIO.com/api/v1/infracoes/explorador?skip=0&limit=5
curl http://SEU-DOMINIO.com/api/v1/infracoes/pesquisa?q=velocidade

# Testar HTTPS também
curl https://SEU-DOMINIO.com/api/v1/infracoes/explorador?skip=0&limit=5
```

### 8. Verificar Logs se Algo Quebrar
```bash
# Logs do Nginx
tail -f /var/log/nginx/error.log
tail -f /var/log/nginx/access.log

# Logs da aplicação
journalctl -u multasgo -f
journalctl -u multasgo --lines=50

# Status dos serviços
systemctl status nginx
systemctl status multasgo

# Verificar portas
netstat -tulpn | grep :8000
netstat -tulpn | grep :80
netstat -tulpn | grep :443
```

## 🛠️ Comandos de Troubleshooting

### Problemas Comuns

#### 1. "404 Not Found" na API
```bash
# Verificar se proxy está configurado na porta 80
curl -I http://SEU-DOMINIO.com/api/v1/infracoes/explorador

# Se 404, o Nginx não tem proxy na porta 80
# Solução: Adicionar proxy na configuração da porta 80
```

#### 2. "502 Bad Gateway"
```bash
# Aplicação não está rodando
systemctl status multasgo
systemctl start multasgo

# Verificar se está na porta correta
netstat -tulpn | grep :8000
```

#### 3. CSS/JS não carregam
```bash
# Verificar arquivos estáticos
ls -la /var/www/multasgo/app/static/
curl -I http://SEU-DOMINIO.com/static/css/styles.css

# Verificar configuração location /static/ no Nginx
```

#### 4. SSL não funciona
```bash
# Verificar certificados
ls -la /etc/letsencrypt/live/SEU-DOMINIO.com/

# Renovar certificados se necessário
certbot renew
```

## 🎯 Lições Principais

### Local ≠ Produção
- **Local**: Aplicação serve tudo diretamente
- **Produção**: Nginx faz proxy + SSL + domínio

### Sempre Testar TODOS os Endpoints
Não basta testar só a página principal! APIs podem quebrar mesmo com a página funcionando.

### Nginx Precisa de Proxy em AMBAS as Portas
- Porta 80: Para HTTP
- Porta 443: Para HTTPS

### JavaScript Depende das APIs
Se a API não funciona, o JavaScript trava e a página fica "carregando infinitamente".

## 📋 Template de Deploy Checklist

```markdown
# Deploy Checklist - [DATA]

## Pré-Deploy
- [ ] Todos endpoints testados localmente
- [ ] CSS/JS carregando corretamente
- [ ] API retornando dados esperados
- [ ] .gitignore configurado corretamente
- [ ] Arquivos sensíveis não commitados

## Deploy
- [ ] Código commitado e no GitHub
- [ ] Clone na VPS realizado
- [ ] Dependências instaladas
- [ ] .env configurado com dados corretos
- [ ] Banco de dados funcionando

## Configuração VPS
- [ ] Nginx com proxy em porta 80 E 443
- [ ] Systemd service criado e habilitado
- [ ] Aplicação iniciando automaticamente
- [ ] Logs sendo gerados corretamente

## Pós-Deploy
- [ ] Certificado SSL funcionando
- [ ] Página principal carregando
- [ ] Explorador funcionando
- [ ] APIs todas respondendo
- [ ] JavaScript sem erros (F12 no browser)
- [ ] Arquivos estáticos carregando
- [ ] Testes de diferentes endpoints realizados

## Verificações Finais
- [ ] HTTP e HTTPS funcionando
- [ ] Performance adequada
- [ ] Logs sem erros críticos
- [ ] Backup do código antigo feito
```

## 🚀 Comandos de Deploy Rápido

```bash
# Deploy em uma linha (após configuração inicial)
ssh root@IP "cd /var/www && mv multasgo multasgo_old && git clone REPO-URL multasgo && cd multasgo && pip3 install -r requirements.txt && cp .env.example .env && systemctl restart multasgo"

# Verificação rápida
ssh root@IP "systemctl status multasgo && curl -s http://localhost:8000/ | head -5"
```

---

## 🎉 STATUS DO DEPLOY ATUAL

### ✅ Deploy Concluído com Sucesso - Setembro 2025

**Sites Online e Funcionais:**
- 🌐 **MultasGO**: https://multasgo.com.br (Sistema principal)
- 🔍 **Explorador**: https://multasgo.com.br/explorador (Navegação de infrações)
- 📊 **Estatísticas**: https://estatistica.multasgo.com.br (Dashboard de dados)

**Performance Atual:**
- ⚡ **Consultas**: ~13ms de resposta
- 💾 **RAM**: 50% de uso (925MB total)
- 💽 **Disco**: 19% de uso (40GB total)
- 🚀 **Status**: Sistema otimizado e estável

**Correções Aplicadas:**
- ✅ Nginx configurado com proxy em porta 80 e 443
- ✅ Explorador de infrações funcionando corretamente
- ✅ Cache e warm-up ativos
- ✅ SSL certificado e funcionando
- ✅ Auto-restart configurado (systemd)

---

**Última atualização**: Setembro 2025
**Projeto**: MultasGO
**Tipo**: Sistema FastAPI + Nginx + SSL

OBSERVAÇÕES: 
🌐 Seus Sites/Projetos:

  1. /var/www/estatistica - Sistema de Estatísticas

  - Domínio: https://estatistica.multasgo.com.br
  - O que é: Sistema de análise de dados (JavaScript/CSV)
  - Conteúdo: Dashboard com arquivos CSV, gráficos, etc.
  - Tecnologia: Frontend (HTML/JS) + dados CSV
  - Status: Ativo e funcionando

  2. /var/www/multasgo - Sistema MultasGO (nosso projeto)

  - Domínio: https://multasgo.com.br
  - O que é: Sistema de consulta de infrações
  - Tecnologia: FastAPI + Python
  - Status: Ativo e funcionando

  🗂️ Resumo da sua infraestrutura:

  VPS (191.252.201.15)
  ├── multasgo.com.br         → MultasGO (infrações)
  └── estatistica.multasgo.com.br → Dashboard de estatísticas

  ✅ Status Atual: Otimizado

  - /var/www/html removido (era só página padrão do Nginx)
  - 2 projetos ativos funcionando perfeitamente
  - VPS otimizada: 50% RAM, 19% disco, 77% espaço livre