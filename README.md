# Skoob Uploader

Script Python que lê uma lista em PDF e marca os livros como `Lido` no Skoob, um por vez.

## Instalação

Para uso normal, instale o pacote com `pipx`, que cria um ambiente isolado e disponibiliza o comando no sistema:

```bash
python3 -m pip install --user pipx
python3 -m pipx ensurepath
pipx install .
```

O comando acima deve ser executado dentro de uma cópia local do projeto. Para instalar diretamente do GitHub:

```bash
pipx install git+https://github.com/andrediasgustavo/skoob-uploader.git
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

Para desenvolvimento, mantenha a instalação manual abaixo. Nesse modo, os comandos com `PYTHONPATH=src` usados mais adiante devem ser executados a partir da pasta do projeto:

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

O navegador padrão é o Google Chrome instalado no computador. Mesmo assim, o Google pode bloquear o login quando o Chrome é iniciado pelo Playwright. Para contas Google, o caminho recomendado é iniciar o Chrome manualmente via CDP, conforme explicado abaixo. O Chromium continua disponível como alternativa, mas também pode apresentar bloqueios em logins do Google.

O procedimento completo para usar o Chrome via CDP está na seção **Primeira execução**. Esse é o caminho recomendado caso o Google bloqueie o login.

Se o Chrome não estiver instalado, escolha `chromium` durante o setup. Se a instalação automática do Chromium falhar, execute manualmente:

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

### Status por livro

Por padrão, todo livro é marcado como `Lido`. Para aplicar outro status, adicione uma tag entre colchetes no final da entrada:

```text
● O Hobbit - J. R. R. Tolkien - livro
● Duna - Frank Herbert - livro - [lendo]
● Akira - Katsuhiro Otomo - quadrinho - [quero ler]
● Fundação - Isaac Asimov - livro - [abandonei]
```

Os status reconhecidos são:

- `[lido]`
- `[lendo]`
- `[quero ler]`
- `[relendo]`
- `[abandonei]`

Uma tag ausente ou desconhecida usa o padrão `Lido` e não interrompe o lote. Tags desconhecidas são registradas no relatório como ignoradas.

Também são aceitos os marcadores `●`, `•` e `*`. No formato estruturado, o tipo deve ser `livro` ou `quadrinho`. O parser reconhece cabeçalhos de ano/mês, entradas que continuam na linha seguinte e volumes como `Vol 1`.

O formato estruturado é o mais confiável. Tabelas complexas, PDFs com texto desordenado ou layouts muito diferentes podem exigir ajustes no arquivo antes da execução.

## Primeira execução

### Caminho recomendado: Chrome via CDP

Use este caminho quando o login passa pelo Google ou quando aparecer a mensagem `Esse navegador ou app pode não ser seguro`.

1. Feche todas as janelas do Chrome.
2. Inicie o Chrome com um perfil separado:

```bash
"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
	--remote-debugging-port=9222 \
	--user-data-dir="$HOME/.skoob-chrome-profile"
```

3. Faça login no Skoob nessa janela.
4. Em outro terminal, execute:

```bash
skoob-uploader run data/livros.pdf --limit 1 --cdp-url http://127.0.0.1:9222
```

Na primeira execução, o programa pedirá confirmação no terminal depois que a página estiver pronta. Pressione `Enter`. A senha nunca é armazenada pelo programa.

### Caminho alternativo: navegador iniciado pelo programa

Também é possível executar sem `--cdp-url`:

```bash
skoob-uploader run data/livros.pdf --limit 1
```

Nesse modo, o programa abre um perfil separado próprio. Faça login nesse navegador na primeira execução. Esse perfil não é o seu perfil pessoal do Chrome e o Google pode bloquear o login por detectar automação. Se isso acontecer, use o caminho via CDP acima.

Se a sessão expirar ou você quiser trocar de conta, use `--login-wait` para forçar uma nova confirmação:

```bash
skoob-uploader run data/livros.pdf --limit 1 --login-wait
```

Use `--no-login-wait` somente em execução automatizada ou sem interface.

Comece com um livro:

```bash
PYTHONPATH=src python -m skoob_uploader.main data/livros.pdf --limit 1
```

Para não aguardar a confirmação manual, use `--no-login-wait`. Essa opção só deve ser usada quando a sessão persistente já estiver autenticada.

Por padrão, o script processa todos os livros encontrados no PDF. Para executar o lote completo:

```bash
PYTHONPATH=src python -m skoob_uploader.main data/livros.pdf --limit 0
```

O resultado é salvo em `reports/skoob-results.csv`. Além do resultado, o CSV registra o status desejado, o status atual encontrado e qualquer tag desconhecida que tenha sido ignorada. Títulos que não tiverem resultado ou cuja página não começar com o título pesquisado são registrados sem serem marcados.

## Testes

```bash
python -m pytest -q
```
