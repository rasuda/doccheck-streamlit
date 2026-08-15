# DocCheck — POC em Streamlit

Protótipo para validar o fluxo de comparação de vários documentos e apresentação de divergências.

## O que esta versão faz

- Login em modal; qualquer usuário e senha não vazios são aceitos.
- Upload múltiplo de PDF, Word, Excel, CSV, TXT e imagens.
- Simulação de preparação por 2 segundos.
- Simulação de comparação por 5 segundos, com mensagens de progresso.
- Relatório fictício coerente, métricas, níveis de severidade e download em CSV.

> A POC não lê nem interpreta o conteúdo dos arquivos. Os resultados são simulados e isso é informado na interface.

## Como executar

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

O Streamlit abrirá o endereço local, geralmente `http://localhost:8501`.

## Próxima versão sugerida

Adicionar extração real de texto e tabelas, normalização dos campos e comparação assistida por IA, mantendo validações determinísticas para CNPJ, datas, moedas, quantidades e números de documento.
