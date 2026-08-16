# DocCheck — POC de extração de campos

Protótipo em Streamlit para validar a extração de campos de documentos em imagem usando o Gemini 3.7 Flash.

## Fluxo

- Login demonstrativo: qualquer usuário e senha não vazios.
- Upload de uma imagem PNG, JPG, JPEG ou WEBP.
- Envio da imagem ao Gemini 3.7 Flash.
- Retorno com tipo do documento, idioma, resumo, campos, valores, confiança e evidência.
- Visualização em tabela e download em CSV ou JSON.

## Configuração da chave

Crie uma chave no Google AI Studio e configure no Streamlit Cloud em **App settings → Secrets**:

```toml
GEMINI_API_KEY = "sua-chave-aqui"
```

Nunca salve a chave diretamente no código ou no GitHub.

## Execução local

```bash
python -m pip install -r requirements.txt
streamlit run app.py
```

Para desenvolvimento local, crie `.streamlit/secrets.toml` com a mesma variável. Esse arquivo não deve ser publicado.

## Privacidade

Use apenas documentos fictícios ou sem informações confidenciais. A camada gratuita do Gemini pode usar o conteúdo enviado para melhoria dos produtos do Google.

