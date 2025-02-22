# Chatbot de Terapia por WhatsApp com Voz

## Recursos
- Integração com WPPConnect
- Suporte para mensagens de voz e texto
- Conversas terapêuticas com IA
- Memória persistente usando Postgres
- Suporte ao idioma português

## Pré-requisitos
- Python 3.8+
- WPPConnect
- Conta no WhatsApp
- Biblioteca de reconhecimento de fala

## Instalação

1. Instalar dependências do sistema:
```bash
# Para Ubuntu/Debian
sudo apt-get install python3-pyaudio portaudio19-dev ffmpeg
```

2. Crie o ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate
```


2. Instalar dependências do Python:
```bash
pip install -r requirements.txt
```

3. Configurar WPPConnect
- Instale o servidor WPPConnect: https://github.com/wppconnect-team/wppconnect-server
- Inicie o servidor WPPConnect
- Obtenha um token de autenticação

4. Configurar variáveis de ambiente:
Crie um arquivo `.env` com:
```
WPPCONNECT_SESSION_NAME=seu_session_name
WPPCONNECT_TOKEN=seu_token_wppconnect

# OPENAI Configuration
OPENAI_API_KEY=sua_chave_openai

```

## Componentes
- `requirements.txt`: Dependências do projeto

## Uso
1. Inicie o servidor WPPConnect
2. Execute o bot:
```bash
cd app/agent
uvicorn main:app --host 0.0.0.0 --port 8000 --reload  
```

## Observações
- Requer configuração do servidor WPPConnect
- Usa Reconhecimento de Fala do Google
- Gera respostas em português
- Memória de conversa persistente por usuário

## Limitações
- Requer conexão estável com a internet
- Precisão do reconhecimento de fala depende da qualidade do áudio
- Depende da disponibilidade do servidor WPPConnect

## Configuração Adicional
- Personalize a persona da Dra. Sofia no código-fonte
- Ajuste os parâmetros do modelo de linguagem conforme necessário
