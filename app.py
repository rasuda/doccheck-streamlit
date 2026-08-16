import base64, hashlib, json, re, time, unicodedata
from collections import defaultdict
from pathlib import Path
import pandas as pd
import streamlit as st
from google import genai
from pydantic import BaseModel, Field

MODEL_ID="gemini-3.7-flash"
DOCS={"invoice":"Commercial Invoice","packing":"Packing List","bl":"Bill of Lading"}
PRIORITY={"shipper_name","consignee_name","commercial_invoice_number","purchase_order","item_quantity","total_quantity","total_packages","net_weight","gross_weight","container_number","seal_number","port_of_loading","port_of_discharge"}
st.set_page_config(page_title="DocCheck",page_icon="🔎",layout="wide")
st.markdown("""<style>.block-container{max-width:1280px;padding-top:2rem}.brand{font-size:.78rem;font-weight:800;letter-spacing:.14em;color:#3165d4}.title{font-size:clamp(2rem,5vw,3.2rem);font-weight:800;color:#10213e}.copy{color:#5d6b82;font-size:1.05rem}.stButton>button{border-radius:11px;font-weight:700;min-height:44px}div[data-testid='stMetric']{background:#fff;border:1px solid #e5eaf2;padding:1rem;border-radius:16px}</style>""",unsafe_allow_html=True)

class FieldData(BaseModel):
    canonical_key:str=Field(description="Chave snake_case padronizada")
    field_name:str
    value:str=Field(description="Valor exatamente como aparece")
    normalized_value:str|None=None
    category:str
    confidence:int=Field(ge=0,le=100)
    source_text:str
    priority:bool
class Extraction(BaseModel):
    document_type:str
    summary:str
    fields:list[FieldData]
    warnings:list[str]=[]

PROMPT="""Analise somente esta imagem de {doc}, documento de importação. Extraia TODOS os campos legíveis sem inventar dados. Preserve value como aparece e use normalized_value para comparação. Use estas canonical_key quando aplicável: shipper_name, shipper_tax_id, shipper_address, consignee_name, consignee_tax_id, consignee_address, notify_party, commercial_invoice_number, packing_list_number, bill_of_lading_number, purchase_order, invoice_date, incoterm, currency, total_invoice_value, item_code, item_description, item_quantity, item_unit, unit_price, item_amount, total_quantity, total_packages, package_type, net_weight, gross_weight, container_number, seal_number, vessel_voyage, booking_number, port_of_loading, port_of_discharge, country_of_origin, payment_terms, shipping_marks. Para itens repetidos, inclua o código no normalized_value (ex.: LUX-20|200). Marque priority para partes, referências, itens/quantidades, volumes, pesos, contêiner/lacre e portos. Inclua evidência e confiança. Responda somente no schema JSON."""

def api_key():
    try:return st.secrets.get("GEMINI_API_KEY")
    except:return None
def extract(data,mime,doc,key):
    c=genai.Client(api_key=key)
    r=c.interactions.create(model=MODEL_ID,input=[{"type":"text","text":PROMPT.format(doc=doc)},{"type":"image","data":base64.b64encode(data).decode(),"mime_type":mime}],response_format={"type":"text","mime_type":"application/json","schema":Extraction.model_json_schema()})
    return Extraction.model_validate_json(r.output_text)
def norm(v):
    if not v:return ""
    v=unicodedata.normalize("NFKD",v).encode("ascii","ignore").decode().lower()
    # Evita falsos positivos entre 1,000.00 / 1000.00 e diferenças de espaços/caixa.
    v=re.sub(r"(?<=\d),(?=\d{3}(?:\D|$))","",v)
    v=v.replace(",",".")
    return re.sub(r"[^a-z0-9.|]","",v)
def signature(files):
    h=hashlib.sha256()
    for k in DOCS:h.update(files[k].getvalue())
    return h.hexdigest()
def compare(raw):
    groups=defaultdict(lambda:defaultdict(list)); labels={}; priorities={}
    for dk,r in raw.items():
        for f in Extraction.model_validate(r).fields:
            groups[f.canonical_key][dk].append(f);labels.setdefault(f.canonical_key,f.field_name);priorities[f.canonical_key]=priorities.get(f.canonical_key,False) or f.priority or f.canonical_key in PRIORITY
    rows=[]
    for k,docs in groups.items():
        shown={};vals={};conf=[]
        for dk in DOCS:
            fs=docs.get(dk,[]);shown[dk]=" | ".join(f.value for f in fs) or "—";vals[dk]=tuple(sorted(norm(f.normalized_value or f.value) for f in fs));conf += [f.confidence for f in fs]
        present=[v for v in vals.values() if v]
        status="Somente informativo" if len(present)<2 else ("Consistente" if len(set(present))==1 else "Divergente")
        rows.append({"Prioritário":"Sim" if priorities[k] else "Não","Campo":labels[k],"Commercial Invoice":shown["invoice"],"Packing List":shown["packing"],"Bill of Lading":shown["bl"],"Status":status,"Confiança mínima":f"{min(conf)}%"})
    return pd.DataFrame(sorted(rows,key=lambda x:({"Divergente":0,"Consistente":1,"Somente informativo":2}[x["Status"]],x["Prioritário"]!="Sim")))
def reset():
    st.session_state.results=None
    st.session_state.debug_mode=False

if "results" not in st.session_state:st.session_state.results=None
if "sig" not in st.session_state:st.session_state.sig=None
if "debug_mode" not in st.session_state:st.session_state.debug_mode=False

st.markdown('<div class="brand">DOCCHECK • IMPORT REVIEW</div><div class="title">Conferência de importação</div><p class="copy">Envie Commercial Invoice, Packing List e Bill of Lading. O sistema extrai todos os campos e destaca as divergências prioritárias.</p>',unsafe_allow_html=True)
st.info("POC: use documentos fictícios ou autorizados e confirme o resultado manualmente.")
st.subheader("Modo de depuração")
st.caption("Executa a comparação usando os três JSONs do repositório. Não chama o Gemini e não consome tokens.")
if st.button("Iniciar comparação — modo debug",type="primary",use_container_width=True):
    try:
        base=Path(__file__).parent/"debug_json"
        paths={"invoice":base/"scenario_2_commercial_invoice.json","packing":base/"scenario_2_packing_list.json","bl":base/"scenario_2_bill_of_lading.json"}
        with st.status("Carregando dados de debug…",expanded=True) as status:
            time.sleep(1)
            loaded={key:Extraction.model_validate(json.loads(path.read_text(encoding="utf-8"))).model_dump() for key,path in paths.items()}
            st.write("Validando os três documentos…")
            st.session_state.results=loaded
            st.session_state.debug_mode=True
            status.update(label="Comparação de debug concluída",state="complete",expanded=False)
        st.rerun()
    except Exception as e:
        st.error(f"Não foi possível carregar os JSONs de debug: {e}")
st.divider()
st.subheader("Modo com IA")
key=api_key()
if not key:st.warning("Configure GEMINI_API_KEY nos Secrets do Streamlit Cloud.")
cols=st.columns(3);files={}
for col,(dk,label) in zip(cols,DOCS.items()):
    with col:
        st.subheader(label);files[dk]=st.file_uploader(label,type=["png","jpg","jpeg","webp"],key=dk,label_visibility="collapsed",on_change=reset)
        if files[dk]:st.image(files[dk].getvalue(),caption=files[dk].name,use_container_width=True)
ready=all(files.values())
if st.button("Iniciar comparação",type="primary",use_container_width=True,disabled=not ready or not key):
    try:
        out={}
        with st.status("Analisando os documentos…",expanded=True) as s:
            time.sleep(2)
            for i,(dk,label) in enumerate(DOCS.items(),1):
                st.write(f"Extraindo {label} ({i}/3)…");f=files[dk];out[dk]=extract(f.getvalue(),f.type or "image/jpeg",label,key).model_dump()
            st.write("Comparando campos…");st.session_state.results=out;st.session_state.sig=signature(files);s.update(label="Conferência concluída",state="complete")
        st.rerun()
    except Exception as e:st.error(f"Não foi possível concluir: {e}")
show_results=st.session_state.results and (st.session_state.debug_mode or (ready and signature(files)==st.session_state.sig))
if show_results:
    raw=st.session_state.results;report=compare(raw);div=report[report.Status=="Divergente"]
    if st.session_state.debug_mode:st.info("Resultado gerado em modo debug, sem consumo de tokens do Gemini.")
    st.divider();a,b,c,d=st.columns(4);a.metric("Documentos",3);b.metric("Campos",len(report));c.metric("Divergências",len(div));d.metric("Prioritárias",len(div[div["Prioritário"]=="Sim"]))
    if div.empty:
        st.success("Nenhuma divergência encontrada.")
    else:
        st.error(f"{len(div)} divergência(s) encontrada(s). Revise antes de prosseguir.")
    t1,t2,t3,t4=st.tabs(["Relatório","Conferência manual","JSON","Alertas"])
    with t1:
        only=st.toggle("Somente prioritários",True);view=report[report["Prioritário"]=="Sim"] if only else report;st.dataframe(view,use_container_width=True,hide_index=True);st.download_button("Baixar CSV",report.to_csv(index=False,sep=";").encode("utf-8-sig"),"relatorio.csv","text/csv",use_container_width=True)
    with t2:
        for dk,label in DOCS.items():
            r=Extraction.model_validate(raw[dk])
            with st.expander(f"{label} — {len(r.fields)} campos",expanded=dk=="invoice"):
                st.caption(r.summary);st.dataframe(pd.DataFrame([{"Campo":f.field_name,"Valor":f.value,"Normalizado":f.normalized_value or "—","Prioritário":"Sim" if f.priority else "Não","Confiança":f"{f.confidence}%","Evidência":f.source_text} for f in r.fields]),use_container_width=True,hide_index=True)
    with t3:
        text=json.dumps({"documents":raw,"comparison":report.to_dict("records")},ensure_ascii=False,indent=2);st.code(text,language="json");st.download_button("Baixar JSON",text,"analise.json","application/json",use_container_width=True)
    with t4:
        alerts=[]
        for dk,label in DOCS.items():
            r=Extraction.model_validate(raw[dk]);alerts += [f"{label}: {w}" for w in r.warnings];alerts += [f"{label}: baixa confiança em {f.field_name} ({f.confidence}%)." for f in r.fields if f.confidence<75]
        if alerts:
            for alert in alerts:
                st.warning(alert)
        else:
            st.success("Nenhum alerta informado.")
