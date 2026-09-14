# Skoob Uploader

Script Python que lê uma lista em PDF e marca os livros como `Lido` no Skoob, um por vez.

## Instalação

Para uso normal, instale o pacote com `pipx`, que cria um ambiente isolado e disponibiliza o comando no sistema:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install .
```

No Windows, use `py -m pip install --user pipx` e `py -m pipx ensurepath`.

### Comando não encontrado após a instalação

O `pipx` pode instalar o pacote corretamente e ainda informar que o diretório de executáveis não está no `PATH`. Nesse caso, execute:

```bash
pipx ensurepath
```

Depois, abra um novo terminal. No macOS ou Linux, também é possível recarregar a sessão atual com:

```bash
source ~/.zprofile
```

No Windows, feche e abra o PowerShell ou o Prompt de Comando. Confirme a instalação com:

```bash
skoob-uploader --help
```

Para desenvolvimento, mantenha a instalação manual abaixo:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

## Configuração inicial

Execute uma vez:

```bash
skoob-uploader setup
```

O assistente verifica o navegador escolhido antes de salvar a configuração. Para `chromium`, ele instala automaticamente o navegador gerenciado pelo Playwright. Para `chrome`, ele verifica se o Google Chrome está instalado no sistema. O caminho do PDF e a escolha do navegador são salvos em um arquivo de configuração no diretório do usuário.

O assistente não solicita nem armazena a senha do Skoob. O perfil persistente do navegador também fica fora do projeto, evitando misturar sessão e arquivos gerados com o código.

O navegador padrão é o Chromium, instalado automaticamente pelo Playwright. O Google Chrome continua disponível como opção avançada, caso já esteja instalado.

Se o Chrome não estiver instalado, escolha `chromium` durante o setup ou instale o Google Chrome antes de tentar novamente. Se a instalação automática do Chromium falhar, execute manualmente:

```bash
python -m playwright install chromium
```

## Uso

Depois da configuração, execute:

```bash
skoob-uploader
```

Também é possível informar o PDF diretamente:

```bash
skoob-uploader data/livros.pdf --limit 1
```

O comando equivalente, em formato mais explícito, é:

```bash
skoob-uploader run data/livros.pdf --limit 1
```

Para executar o lote completo, use `--limit 0`. Argumentos informados na linha de comando têm prioridade sobre o arquivo de configuração. O resultado é salvo em `reports/skoob-results.csv` ou no caminho configurado.

## Formato do PDF

O PDF precisa conter texto selecionável. PDFs escaneados, formados apenas por imagens, precisam passar por OCR antes do uso.

São aceitos os formatos abaixo.

Lista simples, com um título por linha:

```text
O Hobbit
Xogun
Duna
```

Lista estruturada, com marcador, título, autor e tipo:

```text
● O Hobbit - J. R. R. Tolkien - livro
● Xogun - James Clavell - livro
● Akira - Katsuhiro Otomo - quadrinho
```

Também são aceitos os marcadores `●`, `•` e `*`. No formato estruturado, o tipo deve ser `livro` ou `quadrinho`. O parser reconhece cabeçalhos de ano/mês, entradas que continuam na linha seguinte e volumes como `Vol 1`.

O formato estruturado é o mais confiável. Tabelas complexas, PDFs com texto desordenado ou layouts muito diferentes podem exigir ajustes no arquivo antes da execução.

## Primeira execução

O navegador abre visível por padrão. O script aguarda uma confirmação antes de começar: faça login manualmente no Skoob, deixe a página pronta e pressione `Enter` no terminal. A sessão fica em um diretório persistente de dados do usuário; o script não recebe nem armazena senha.

Por padrão, a automação abre o Chrome instalado com um perfil dedicado. Isso não reutiliza automaticamente o perfil pessoal do Chrome, porque o Chrome bloqueia perfis que já estão abertos.

O uso comum não exige CDP. Essa opção é avançada e só é necessária para reutilizar uma sessão de Chrome iniciada separadamente. Feche todas as janelas do Chrome e inicie uma instância dedicada com CDP. Usar um perfil separado evita que uma instância normal já aberta ignore a flag ou bloqueie o perfil:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
	--remote-debugging-port=9222 \
	--user-data-dir="$HOME/.skoob-chrome-profile"
```

Depois execute o script conectado a essa janela:

```bash
PYTHONPATH=src python -m skoob_uploader.main data/livros.pdf --limit 1 --cdp-url http://127.0.0.1:9222
```

Assim, faça login nessa janela do Chrome antes de pressionar `Enter`. Não use o mesmo perfil em duas instâncias simultâneas.

Comece com um livro:

```bash
PYTHONPATH=src python -m skoob_uploader.main data/livros.pdf --limit 1
```

Para não aguardar a confirmação manual, use `--no-login-wait`. Essa opção só deve ser usada quando a sessão persistente já estiver autenticada.

Por padrão, o script processa todos os livros encontrados no PDF. Para executar o lote completo:

```bash
PYTHONPATH=src python -m skoob_uploader.main data/livros.pdf --limit 0
```

O resultado é salvo em `reports/skoob-results.csv`. Títulos que não tiverem resultado ou cuja página não começar com o título pesquisado são registrados sem serem marcados.

## Testes

```bash
python -m pytest -q
```
