import io
import time

import pandas as pd
import streamlit as st


st.set_page_config(
    page_title="DocCheck | Comparação inteligente",
    page_icon="🔎",
    layout="wide",
    initial_sidebar_state="collapsed",
)


st.markdown(
    """
    <style>
    [data-testid="stHeader"] { background: transparent; }
    .block-container { max-width: 1180px; padding-top: 2rem; padding-bottom: 4rem; }
    .brand { font-size: .78rem; font-weight: 800; letter-spacing: .14em; color: #3165d4; }
    .hero-title { font-size: clamp(2rem, 5vw, 3.7rem); line-height: 1.04; font-weight: 800; color: #10213e; margin: .45rem 0 .7rem; }
    .hero-copy { max-width: 760px; font-size: 1.08rem; color: #5d6b82; margin-bottom: 1.4rem; }
    .soft-card { background: #ffffff; color: #262730; border: 1px solid #e5eaf2; border-radius: 18px; padding: 1.15rem 1.3rem; box-shadow: 0 8px 28px rgba(29, 55, 90, .06); }
    .step { display: inline-flex; align-items: center; justify-content: center; width: 28px; height: 28px; border-radius: 50%; background: #eaf1ff; color: #3165d4; font-weight: 800; margin-right: .45rem; }
    .doc-name { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; font-weight: 700; color: #233655; }
    .muted { color: #748197; font-size: .88rem; }
    .severity-high { color: #a92727; background: #ffeded; border-radius: 999px; padding: .2rem .55rem; font-weight: 700; }
    div[data-testid="stMetric"] { background: #ffffff; color: #262730; border: 1px solid #e5eaf2; padding: 1rem; border-radius: 16px; }
    .stButton > button { border-radius: 11px; font-weight: 700; min-height: 44px; }
    .stDownloadButton > button { border-radius: 11px; font-weight: 700; }
    </style>
    """,
    unsafe_allow_html=True,
)


def reset_report() -> None:
    st.session_state.report_ready = False


def build_demo_report(file_names: list[str]) -> pd.DataFrame:
    """Generate coherent fake discrepancies for the visual POC."""
    names = file_names + ["Documento adicional"] * max(0, 3 - len(file_names))
    return pd.DataFrame(
        [
            {
                "Severidade": "Alta",
                "Campo": "Valor total",
                "Documento de referência": names[0],
                "Valor de referência": "R$ 248.750,00",
                "Documento divergente": names[1],
                "Valor divergente": "R$ 247.850,00",
                "Diferença": "R$ 900,00",
            },
            {
                "Severidade": "Alta",
                "Campo": "CNPJ do fornecedor",
                "Documento de referência": names[0],
                "Valor de referência": "12.345.678/0001-90",
                "Documento divergente": names[1],
                "Valor divergente": "12.345.678/0001-09",
                "Diferença": "Dígitos finais",
            },
            {
                "Severidade": "Média",
                "Campo": "Quantidade de volumes",
                "Documento de referência": names[0],
                "Valor de referência": "120 volumes",
                "Documento divergente": names[2],
                "Valor divergente": "118 volumes",
                "Diferença": "2 volumes",
            },
            {
                "Severidade": "Média",
                "Campo": "Data de embarque",
                "Documento de referência": names[0],
                "Valor de referência": "12/08/2026",
                "Documento divergente": names[1],
                "Valor divergente": "13/08/2026",
                "Diferença": "1 dia",
            },
            {
                "Severidade": "Baixa",
                "Campo": "Descrição da mercadoria",
                "Documento de referência": names[0],
                "Valor de referência": "Camiseta 100% algodão",
                "Documento divergente": names[2],
                "Valor divergente": "Camiseta de algodão",
                "Diferença": "Variação textual",
            },
        ]
    )


if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "report_ready" not in st.session_state:
    st.session_state.report_ready = False
if "upload_signature" not in st.session_state:
    st.session_state.upload_signature = ()


@st.dialog("Acessar o DocCheck", width="small", dismissible=False)
def login_dialog() -> None:
    st.caption("POC • Ambiente de demonstração")
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
    st.markdown('<div class="hero-title">Compare documentos.<br>Encontre diferenças.</div>', unsafe_allow_html=True)
    st.markdown('<div class="hero-copy">Uma experiência simples para validar informações em vários documentos e destacar o que precisa de atenção.</div>', unsafe_allow_html=True)
    st.stop()


top_left, top_right = st.columns([5, 1])
with top_left:
    st.markdown('<div class="brand">DOCCHECK • POC</div>', unsafe_allow_html=True)
with top_right:
    if st.button("Sair", use_container_width=True):
        st.session_state.clear()
        st.rerun()

st.markdown('<div class="hero-title">Comparação de documentos</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="hero-copy">Envie os arquivos da mesma operação. O DocCheck confronta os campos equivalentes e organiza as divergências para sua revisão.</div>',
    unsafe_allow_html=True,
)

st.info("Esta é uma POC: os documentos enviados não são lidos e o relatório abaixo usa dados fictícios coerentes para demonstrar o fluxo.", icon="🧪")

st.markdown('### <span class="step">1</span> Carregue os documentos', unsafe_allow_html=True)
uploaded_files = st.file_uploader(
    "Arraste os arquivos para esta área ou clique para selecionar",
    type=["pdf", "docx", "xlsx", "csv", "txt", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="Envie pelo menos dois documentos. Nesta POC, somente nomes e tamanhos são usados.",
    on_change=reset_report,
    label_visibility="visible",
)

signature = tuple((f.name, f.size) for f in uploaded_files)
if signature and signature != st.session_state.upload_signature:
    with st.spinner("Recebendo e preparando os documentos…"):
        time.sleep(2)
    st.session_state.upload_signature = signature

if uploaded_files:
    st.success(f"{len(uploaded_files)} documento(s) carregado(s) com sucesso.", icon="✅")
    cols = st.columns(min(len(uploaded_files), 3))
    for index, file in enumerate(uploaded_files):
        with cols[index % len(cols)]:
            size = f"{file.size / 1024:.1f} KB" if file.size < 1024 * 1024 else f"{file.size / (1024 * 1024):.1f} MB"
            st.markdown(
                f'<div class="soft-card"><div class="doc-name">📄 {file.name}</div><div class="muted">{size} • pronto</div></div>',
                unsafe_allow_html=True,
            )

st.write("")
st.markdown('### <span class="step">2</span> Inicie a comparação', unsafe_allow_html=True)
can_compare = len(uploaded_files) >= 2
if not can_compare:
    st.caption("Carregue pelo menos 2 documentos para liberar a comparação.")

if st.button(
    "✨ Iniciar comparação",
    type="primary",
    use_container_width=True,
    disabled=not can_compare,
):
    progress = st.progress(0, text="Mapeando campos equivalentes…")
    stages = [
        (18, "Identificando os tipos de documento…"),
        (38, "Mapeando campos equivalentes…"),
        (62, "Conferindo valores e datas…"),
        (84, "Classificando divergências…"),
        (100, "Finalizando o relatório…"),
    ]
    for value, label in stages:
        time.sleep(1)
        progress.progress(value, text=f"🔍 {label}")
    progress.empty()
    st.session_state.report_ready = True
    st.toast("Comparação concluída!", icon="✅")

if st.session_state.report_ready and can_compare:
    report = build_demo_report([f.name for f in uploaded_files])
    st.divider()
    st.markdown('### <span class="step">3</span> Relatório de divergências', unsafe_allow_html=True)
    st.caption("Resultado simulado para validação da experiência do usuário.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Documentos", len(uploaded_files))
    m2.metric("Campos comparados", 14)
    m3.metric("Divergências", len(report), delta="Requer revisão", delta_color="inverse")
    m4.metric("Campos consistentes", 9)

    st.write("")
    tab_summary, tab_details, tab_docs = st.tabs(["Visão geral", "Todas as divergências", "Documentos"])

    with tab_summary:
        st.error("2 divergências de alta prioridade precisam ser verificadas.", icon="⚠️")
        for _, row in report.iterrows():
            icon = {"Alta": "🔴", "Média": "🟠", "Baixa": "🟡"}[row["Severidade"]]
            with st.expander(f'{icon} {row["Campo"]}  ·  {row["Severidade"]}'):
                c1, c2 = st.columns(2)
                with c1:
                    st.caption(row["Documento de referência"])
                    st.code(row["Valor de referência"], language=None)
                with c2:
                    st.caption(row["Documento divergente"])
                    st.code(row["Valor divergente"], language=None)
                st.write(f'**Diferença identificada:** {row["Diferença"]}')

    with tab_details:
        st.dataframe(report, use_container_width=True, hide_index=True)
        csv_buffer = io.StringIO()
        report.to_csv(csv_buffer, index=False, sep=";", encoding="utf-8-sig")
        st.download_button(
            "⬇️ Baixar relatório em CSV",
            data=csv_buffer.getvalue().encode("utf-8-sig"),
            file_name="relatorio_divergencias_demo.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with tab_docs:
        for file in uploaded_files:
            st.write(f"✓ **{file.name}** — incluído na comparação simulada")

    if st.button("Fazer nova comparação", use_container_width=True):
        st.session_state.report_ready = False
        st.rerun()
