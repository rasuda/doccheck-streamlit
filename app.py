import base64
import json

import pandas as pd
import streamlit as st
from google import genai
from pydantic import BaseModel, Field


MODEL_ID = "gemini-3.7-flash"

st.set_page_config(page_title="DocCheck | Extração inteligente", page_icon="🔎", layout="wide")

st.markdown(
    """
    <style>
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem; }
    .brand { font-size: .78rem; font-weight: 800; letter-spacing: .14em; color: #3165d4; }
    .hero-title { font-size: clamp(2rem, 5vw, 3.5rem); line-height: 1.04; font-weight: 800; color: #10213e; margin: .45rem 0 .7rem; }
    .hero-copy { max-width: 780px; font-size: 1.08rem; color: #5d6b82; margin-bottom: 1.4rem; }
    .step { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: #eaf1ff; color: #3165d4; font-weight: 800; margin-right: .45rem; }
    div[data-testid="stMetric"] { background: #ffffff; color: #262730; border: 1px solid #e5eaf2; padding: 1rem; border-radius: 16px; }
    .stButton > button { border-radius: 11px; font-weight: 700; min-height: 44px; }
    </style>
    """,
    unsafe_allow_html=True,
)


class ExtractedField(BaseModel):
    field_name: str = Field(description="Nome claro do campo, em português")
    value: str = Field(description="Valor exatamente como aparece no documento")
    normalized_value: str | None = Field(default=None, description="Valor padronizado, sem alterar o significado")
    category: str = Field(description="Categoria do campo")
    confidence: int = Field(ge=0, le=100, description="Confiança estimada da leitura")
    source_text: str = Field(description="Trecho visível que sustenta a extração")


class DocumentExtraction(BaseModel):
    document_type: str = Field(description="Tipo provável do documento")
    language: str = Field(description="Idioma predominante")
    summary: str = Field(description="Resumo objetivo em uma frase")
    fields: list[ExtractedField] = Field(description="Campos relevantes e legíveis encontrados")
    warnings: list[str] = Field(default_factory=list, description="Problemas de legibilidade ou informações incertas")


EXTRACTION_PROMPT = """
Você é especialista em leitura de documentos empresariais. Analise somente a imagem
fornecida e extraia todos os campos relevantes e legíveis.

Regras:
- Não invente, complete ou presuma valores.
- Preserve cada valor exatamente como aparece no documento.
- Use normalized_value somente para padronizar datas, números e valores.
- Se um texto estiver ilegível, não o inclua e registre o problema em warnings.
- Inclua identificadores, partes, endereços, datas, moedas, valores, quantidades,
  pesos, referências logísticas, descrições e outros campos úteis visíveis.
- Informe uma confiança realista e uma pequena evidência visível para cada campo.
- Responda exclusivamente no JSON definido pelo schema.
"""


def reset_extraction() -> None:
    st.session_state.extraction = None
    st.session_state.analyzed_signature = None


def get_api_key() -> str | None:
    try:
        return st.secrets.get("GEMINI_API_KEY")
    except (FileNotFoundError, KeyError):
        return None


def analyze_image(image_bytes: bytes, mime_type: str, api_key: str) -> DocumentExtraction:
    client = genai.Client(api_key=api_key)
    interaction = client.interactions.create(
        model=MODEL_ID,
        input=[
            {"type": "text", "text": EXTRACTION_PROMPT},
            {
                "type": "image",
                "data": base64.b64encode(image_bytes).decode("utf-8"),
                "mime_type": mime_type,
            },
        ],
        response_format={
            "type": "text",
            "mime_type": "application/json",
            "schema": DocumentExtraction.model_json_schema(),
        },
    )
    return DocumentExtraction.model_validate_json(interaction.output_text)


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "extraction" not in st.session_state:
    st.session_state.extraction = None
if "analyzed_signature" not in st.session_state:
    st.session_state.analyzed_signature = None


@st.dialog("Acessar o DocCheck", width="small", dismissible=False)
def login_dialog() -> None:
    st.caption("POC • Extração de campos com IA")
    with st.form("login_form"):
        user = st.text_input("Usuário ou e-mail", placeholder="nome@empresa.com")
        password = st.text_input("Senha", type="password", placeholder="••••••••")
        submitted = st.form_submit_button("Entrar", type="primary", use_container_width=True)
        if submitted:
            if user.strip() and password.strip():
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Preencha usuário e senha. Qualquer combinação é válida nesta demonstração.")


if not st.session_state.authenticated:
    login_dialog()
    st.markdown('<div class="brand">DOCCHECK</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-title">Transforme documentos<br>em dados estruturados.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-copy">Envie a imagem de um documento e valide os campos identificados pela inteligência artificial.</div>', unsafe_allow_html=True)
    st.stop()


top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown('<div class="brand">DOCCHECK • EXTRACTION POC</div>', unsafe_allow_html=True)
with top_right:
    if st.button("Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.markdown('<div class="hero-title">Extração de campos</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-copy">Carregue a imagem de um documento. O Gemini identifica seu tipo e transforma as informações visíveis em campos estruturados.</div>',
    unsafe_allow_html=True,
)
st.info("POC para documentos fictícios ou sem informações confidenciais. A camada gratuita do Gemini pode usar o conteúdo enviado para melhoria dos produtos.", icon="🧪")

api_key = get_api_key()
if not api_key:
    st.warning("A chave do Gemini ainda não foi configurada. Adicione GEMINI_API_KEY nos Secrets do aplicativo no Streamlit Cloud.", icon="🔑")

st.markdown('### <span class="step">1</span> Envie a imagem do documento', unsafe_allow_html=True)
uploaded_image = st.file_uploader(
    "Selecione uma imagem nítida e completa",
    type=["png", "jpg", "jpeg", "webp"],
    help="Formatos aceitos: PNG, JPG, JPEG e WEBP. Limite recomendado: até 20 MB.",
    on_change=reset_extraction,
)

if uploaded_image:
    image_bytes = uploaded_image.getvalue()
    mime_type = uploaded_image.type or "image/jpeg"
    signature = (uploaded_image.name, uploaded_image.size)
    preview_col, action_col = st.columns([1.15, 1], gap="large")

    with preview_col:
        st.image(image_bytes, caption=uploaded_image.name, use_container_width=True)

    with action_col:
        st.markdown('### <span class="step">2</span> Extraia os campos', unsafe_allow_html=True)
        st.write("A IA analisará somente as informações visíveis e retornará dados estruturados.")
        st.caption(f"Modelo: {MODEL_ID}")
        if st.button("✨ Analisar documento", type="primary", use_container_width=True, disabled=not bool(api_key)):
            try:
                with st.status("Analisando o documento…", expanded=True) as status:
                    st.write("🔍 Identificando o tipo de documento")
                    st.write("🧾 Localizando campos e valores")
                    extraction = analyze_image(image_bytes, mime_type, api_key)
                    st.write("✅ Validando a estrutura do resultado")
                    st.session_state.extraction = extraction.model_dump()
                    st.session_state.analyzed_signature = signature
                    status.update(label="Extração concluída", state="complete", expanded=False)
                st.rerun()
            except Exception as exc:
                error_text = str(exc)
                if "429" in error_text or "RESOURCE_EXHAUSTED" in error_text:
                    st.error("A cota gratuita do Gemini foi atingida. Aguarde a renovação e tente novamente.")
                elif "API_KEY" in error_text.upper() or "401" in error_text or "403" in error_text:
                    st.error("A chave do Gemini não foi aceita. Verifique o Secret GEMINI_API_KEY.")
                else:
                    st.error(f"Não foi possível analisar o documento: {error_text}")

    if st.session_state.extraction and st.session_state.analyzed_signature == signature:
        result = DocumentExtraction.model_validate(st.session_state.extraction)
        st.divider()
        st.markdown('### <span class="step">3</span> Campos extraídos', unsafe_allow_html=True)
        m1, m2, m3 = st.columns(3)
        m1.metric("Tipo de documento", result.document_type)
        m2.metric("Idioma", result.language)
        m3.metric("Campos encontrados", len(result.fields))
        st.write(f"**Resumo:** {result.summary}")

        rows = [{
            "Campo": field.field_name,
            "Valor extraído": field.value,
            "Valor normalizado": field.normalized_value or "—",
            "Categoria": field.category,
            "Confiança": f"{field.confidence}%",
            "Evidência": field.source_text,
        } for field in result.fields]
        dataframe = pd.DataFrame(rows)
        tab_fields, tab_json, tab_warnings = st.tabs(["Campos", "JSON", "Alertas"])

        with tab_fields:
            st.dataframe(dataframe, use_container_width=True, hide_index=True)
            st.download_button("⬇️ Baixar campos em CSV", data=dataframe.to_csv(index=False, sep=";").encode("utf-8-sig"), file_name="campos_extraidos.csv", mime="text/csv", use_container_width=True)
        with tab_json:
            json_text = json.dumps(result.model_dump(), ensure_ascii=False, indent=2)
            st.code(json_text, language="json")
            st.download_button("⬇️ Baixar resultado em JSON", data=json_text.encode("utf-8"), file_name="extracao_documento.json", mime="application/json", use_container_width=True)
        with tab_warnings:
            if result.warnings:
                for warning in result.warnings:
                    st.warning(warning)
            else:
                st.success("Nenhum alerta de legibilidade informado pelo modelo.", icon="✅")

        if st.button("Analisar outra imagem", use_container_width=True):
            reset_extraction()
            st.rerun()
else:
    st.caption("Nenhuma imagem enviada.")

