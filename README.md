# Navegador COP31 — cop31.grupotrie.com.br

Guia em português para navegar a COP31 (Antalya, 9–20 de novembro de 2026), com feed de monitoramento atualizado por agentes e interface em sete idiomas (pt, en, es, fr, ru, zh, ar).

Site estático servido pelo GitHub Pages a partir da raiz deste repositório (`CNAME`, `.nojekyll`).

## Estrutura

| Caminho | O que é | Quem edita |
|---|---|---|
| `index.html` | A página inteira (HTML + CSS + JS), **sempre em português**. Fonte única do conteúdo. | pessoas / sessões de edição do guia |
| `data/feed.json` | Itens do monitoramento (publicações e posts). | agentes de monitoramento (web a cada 6 h, redes a cada hora) via artefato + sync horário da sessão principal |
| `i18n/pt.json` | Tabela de strings extraída de `index.html` (chave → texto em português). Gerada, não editar à mão. | `tools/i18n.mjs extract` |
| `i18n/<lang>.json` | Traduções (mesmas chaves). O que faltar cai no português automaticamente. | `tools/i18n.mjs merge` |
| `i18n/glossary.md` | Terminologia obrigatória para tradutores (humanos ou agentes). | pessoas |
| `i18n/todo.<lang>.json` | Strings ainda não traduzidas (gerado). | — |
| `tools/i18n.mjs` | Extrai, divide em lotes, valida e mescla traduções. | — |
| `tools/test_i18n.mjs` | Teste headless do seletor de idioma. | — |

## Como funciona o multilíngue

A página não é duplicada por idioma. O código que identifica as unidades fica em `index.html` entre os marcadores `/*i18n-core-begin*/` e `/*i18n-core-end*/`; `tools/i18n.mjs` executa esse mesmo código em jsdom, por isso as chaves coincidem. No carregamento, o script percorre o DOM estático, identifica cada unidade traduzível (parágrafo, célula, rótulo, atributo `title`/`aria-label`/`placeholder`) e calcula uma chave a partir do texto em português (hash FNV-1a). Ao escolher um idioma, baixa `i18n/<lang>.json` e substitui cada unidade cuja chave exista no arquivo; as demais ficam em português. Strings geradas por script (contagens, datas, status do feed) usam o objeto `J0` e a tabela de dados `d:`; os resumos do feed vêm em português (`summary`) e nos outros seis idiomas (`summary_i18n`, escritos pelos próprios agentes); o rótulo do tipo usa chaves `d:`. Faltando a tradução, mostra-se o português.

Consequências práticas:

- Editar um parágrafo em português muda a chave dele → só esse parágrafo volta a aparecer em português nos outros idiomas até ser retraduzido. Nada quebra.
- Adicionar uma aba/seção nova em `index.html` não exige tocar nas traduções: ela aparece em português em todos os idiomas até ser traduzida.
- A escolha de idioma fica em `localStorage` (`cop31nav.lang`); `?lang=en` na URL força um idioma; sem escolha prévia, usa o idioma do navegador se for um dos sete.

## Fluxo de atualização (durante a COP)

1. Edite `index.html` em português (texto, novas seções, novas abas). Para uma aba nova: acrescente o `<a class="nav-item" data-view="x">` na `nav.rail`, a `<section class="view" id="view-x" data-view="x" hidden>` e o nome em `VIEWS` no script.
2. Regere a tabela e veja o que falta por idioma:
   ```sh
   cd tools && npm install   # só na primeira vez (jsdom)
   node tools/i18n.mjs extract
   ```
3. Traduza o que falta. Para agentes: `node tools/i18n.mjs split <lang> 20000` cria lotes em `i18n/work/<lang>.N.json`; cada lote vai para um agente barato (Haiku, esforço baixo) com `tools/agent_prompt.md`, que grava `i18n/work/out/<lang>.N.json`. Chinês e árabe passam por revisão em um modelo maior (Sonnet) antes de mesclar.
4. Valide e mescle (rejeita entradas com tags, atributos ou `{placeholders}` alterados; grava `i18n/rejected.<lang>.json` para retrabalho):
   ```sh
   node tools/i18n.mjs merge en i18n/work/out/en.*.json
   node tools/i18n.mjs status
   ```
5. Teste e publique:
   ```sh
   node tools/test_i18n.mjs        # ou: node tools/test_i18n.mjs en
   git add -A && git commit -m "..." && git push
   ```

Mudanças só no `data/feed.json` (agentes) não exigem nada disso.

## Regras de conteúdo

- Documentos internos de parceiros/clientes podem informar o texto, mas nunca são citados nas Fontes.
- Fontes em ordem alfabética.
- Contas de redes sociais não verificadas aparecem marcadas como tal no feed.

## Versão 1.0 (branch `v1-launch`)

- **Hoje na COP31** (`#hoje`, topo do Panorama): curadoria editorial em `data/today.json`, publicada só com aprovação humana e fonte verificada. Fluxo em `docs/editorial.md`.
- **Pulso social** (`#pulso`): posts brutos das contas monitoradas; Bluesky ao vivo pela API pública, X, Instagram e YouTube como cartões e incorporações sob demanda. Contas em `data/pulse.json` (`tools/build_pulse.py`).
- Atualizações: hora da coleta separada da hora de carregamento, cobertura, estados de lentidão e erro com nova tentativa, posts com link de perfil sinalizados.
- Validação e testes: `python3 -I tools/validate_feed.py`, `python3 -I -m unittest discover -s tests`, `node tests/test_v1.mjs`, `node tests/test_qa.mjs` (regressões das issues #2–#9), `node tools/test_i18n.mjs [lang]`; rodam no GitHub Actions (`.github/workflows/tests.yml`).
- Arquitetura, auditoria das plataformas e limitações: `docs/v1.md`.
