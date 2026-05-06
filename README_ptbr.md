# Project S.A.R.A.

Synthetic Adaptive Responsive Assistant

Project S.A.R.A. e uma assistente virtual desenvolvida em Python, com recursos de inteligencia artificial, reconhecimento de voz, sintese de fala, memoria local e acoes basicas do sistema.

O projeto foi desenvolvido com ajuda de IA e pode conter erros, limitacoes ou comportamentos inesperados. Revise o codigo antes de usar em ambientes importantes ou publicar novas versoes.

## Recursos

- Conversa por texto com historico local.
- Comandos por voz usando microfone.
- Respostas por voz com sintese de fala.
- Integracao com Groq para respostas de IA.
- Analise simples de humor da conversa.
- Memoria local para preferencias, notas e conversas.
- Acoes do sistema, como mostrar hora/data, abrir aplicativos, pesquisar na web e tocar musicas.
- Interface grafica com visualizador/HUD.

## Requisitos

- Python 3.9 ou superior.
- Microfone, para comandos de voz.
- Chave de API da Groq, para respostas de IA.

## Instalacao

1. Clone o repositorio:

```bash
git clone <url-do-repositorio>
cd Project-S.A.R.A/sara_assistant
```

2. Crie e ative um ambiente virtual:

```bash
python -m venv venv
```

Windows:

```bash
venv\Scripts\activate
```

Linux/macOS:

```bash
source venv/bin/activate
```

3. Instale as dependencias:

```bash
pip install -r requirements.txt
```

4. Configure a chave da Groq.

Copie o arquivo `.env.example` para `.env` e preencha sua chave:

```env
GROQ_API_KEY=sua_chave_aqui
```

Ou configure a variavel de ambiente:

Windows PowerShell:

```powershell
$env:GROQ_API_KEY = "sua_chave_aqui"
```

Linux/macOS:

```bash
export GROQ_API_KEY="sua_chave_aqui"
```

5. Execute o aplicativo:

```bash
python main.py
```

## Uso

### Comandos de texto

Digite uma mensagem no campo de texto e pressione Enter ou use o botao de envio.

### Comandos de voz

Use o botao de microfone, fale o comando e aguarde o processamento.

### Exemplos de comandos

| Comando | Exemplo |
| --- | --- |
| Ver hora | "Que horas sao?" |
| Ver data | "Que dia e hoje?" |
| Abrir aplicativo | "Abre o bloco de notas" |
| Pesquisar | "Pesquisa sobre Python" |
| Musica | "Toca uma musica do Queen" |

## Estrutura do projeto

```text
sara_assistant/
|-- main.py                  # Arquivo principal
|-- config.py                # Configuracoes gerais
|-- pet_gui.py               # Interface grafica
|-- hud_visualizer.py        # Visualizador/HUD
|-- hud_config.py            # Configuracoes do HUD
|-- requirements.txt         # Dependencias
|-- modules/
|   |-- ai_assistant.py      # Integracao com Groq
|   |-- memory.py            # Memoria local
|   |-- mood_analyzer.py     # Analise de humor
|   |-- notifications.py     # Notificacoes
|   |-- proactive.py         # Comportamento proativo
|   |-- speech_to_text.py    # Reconhecimento de voz
|   |-- system_actions.py    # Acoes do sistema
|   |-- system_monitor.py    # Monitoramento do sistema
|   `-- text_to_speech.py    # Sintese de voz
|-- assets/                  # Recursos visuais
`-- data/                    # Dados locais gerados em execucao
```

## Criar executavel

Para criar um executavel standalone:

```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name="Project-SARA" main.py
```

O executavel sera criado na pasta `dist/`.

## Docker

Este projeto nao e distribuido com Docker por padrao.

Project S.A.R.A. e uma assistente desktop que interage diretamente com o sistema operacional. Ela pode usar interface grafica, microfone, saida de audio, navegador, aplicativos locais, eventos de teclado/mouse e APIs especificas do Windows. Em um container Docker, esse tipo de acesso fica limitado, complexo ou indisponivel, o que reduziria as principais funcionalidades da assistente.

Docker pode ser uma boa opcao no futuro para componentes separados, como uma API local, servicos de memoria, banco de dados, processamento em segundo plano ou integracoes que nao dependam do desktop do usuario. A aplicacao principal deve ser executada nativamente no sistema para manter acesso adequado aos recursos locais.

## Configuracao

Edite `config.py` para personalizar:

- `PET_CONFIG`: nome, cores e parametros visuais mantidos por compatibilidade interna.
- `VOICE_CONFIG`: velocidade, volume e voz usada na sintese de fala.
- `AI_CONFIG`: modelo e parametros da IA.
- `MOOD_COLORS`: cores usadas para estados de humor.

## Seguranca

Nao envie arquivos `.env`, historicos locais, memorias pessoais ou chaves de API para o GitHub. Antes de publicar, confirme se `GROQ_API_KEY` e outros segredos nao aparecem em arquivos versionados.

## Solucao de problemas

### Microfone nao funciona

- Verifique se o PyAudio esta instalado corretamente.
- No Windows, pode ser necessario instalar o Visual C++ Build Tools.
- Confirme se o sistema operacional permitiu acesso ao microfone.

### Erro de API

- Verifique se `GROQ_API_KEY` esta configurada.
- Confirme se a chave esta ativa no painel da Groq.

### Sem som

- Verifique as configuracoes de audio do sistema.
- Teste outra voz ou dispositivo de saida.

## Licenca

MIT License. Consulte o arquivo de licenca do repositorio, se disponivel.

## Contribuicoes

Contribuicoes sao bem-vindas por meio de issues e pull requests.
