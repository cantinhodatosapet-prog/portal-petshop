import streamlit as st
from supabase import create_client
from datetime import datetime
import pandas as pd
import re
import time

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Área do Cliente", page_icon="🐾", layout="centered")

# --- CREDENCIAIS ---
SUPABASE_URL = "https://arfwuywrqssizlbsenqt.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImFyZnd1eXdycXNzaXpsYnNlbnF0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NjQ1NTc1ODQsImV4cCI6MjA4MDEzMzU4NH0.dS7FJWl6wAhmshHfR6ZTN7hRsbQJAqML3CWkZFXKXuQ"

@st.cache_resource
def init_connection():
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = init_connection()

# --- ESTILOS CSS ---
st.markdown("""
<style>
    .stApp { background-color: #121212; color: #E0E0E0; font-family: sans-serif; }
    .stTextInput > div > div > input, .stSelectbox > div > div > div { 
        background-color: #2C2C2C; color: white; border: 1px solid #444; border-radius: 5px; 
    }
    .stButton > button { background-color: #4CAF50; color: white; font-weight: bold; width: 100%; border-radius: 5px; border: none; }
    
    /* BOX SALDO */
    .saldo-container {
        background-color: #1E1E1E; border-radius: 12px; padding: 20px; text-align: center;
        margin-bottom: 20px; border: 1px solid #333; box-shadow: 0 4px 15px rgba(0,0,0,0.6);
    }
    .saldo-titulo { font-size: 12px; color: #888; text-transform: uppercase; letter-spacing: 2px; }
    .saldo-valor { font-size: 48px; font-weight: 900; margin: 5px 0; line-height: 1.1; }
    .neon-green { color: #39FF14; text-shadow: 0 0 15px rgba(57, 255, 20, 0.5); }
    .neon-red { color: #FF4444; text-shadow: 0 0 15px rgba(255, 68, 68, 0.5); }

    /* TABELA UNIFICADA */
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 30px; background-color: #D1C4A9; }
    
    /* Cabeçalho Principal */
    .header-main {
        background-color: #8B7D5B; color: #000; font-weight: 800; text-transform: uppercase;
        padding: 12px 15px; font-size: 14px; border: 1px solid #555; letter-spacing: 0.5px;
    }
    
    /* Divisores de Seção */
    .section-header {
        background-color: #333; color: #FFF; font-weight: bold; text-align: left;
        padding: 8px 15px; font-size: 12px; letter-spacing: 1px; text-transform: uppercase;
        border-left: 5px solid;
    }
    .sec-serv { border-left-color: #FFA500; } 
    .sec-pag { border-left-color: #39FF14; } 
    
    /* Colunas e Linhas */
    .col-header {
        background-color: #A69B80; color: #000; font-weight: 700; text-align: center;
        font-size: 13px; padding: 6px; border: 1px solid #777;
    }
    .row-data td {
        background-color: #DAE5F0; color: #000; border-bottom: 1px solid #FFF;
        border-right: 1px solid #FFF; padding: 12px 8px; font-size: 13px; vertical-align: middle;
    }
    .row-data td:last-child { border-right: none; }
    
    .center-col { text-align: center; }
    .left-col { text-align: left; padding-left: 10px !important; }
    .val-col { text-align: right; font-weight: 700; padding-right: 15px !important; white-space: nowrap; }
    
    /* STATUS PILLS */
    .status-pill {
        display: inline-block; padding: 4px 8px; border-radius: 4px; 
        font-size: 10px; font-weight: 800; text-transform: uppercase; color: #FFF; min-width: 80px;
    }
    .st-verde { background-color: #2E7D32; }   
    .st-verde-claro { background-color: #8BC34A; color: #000; }
    .st-vermelho { background-color: #C62828; } 
    .st-laranja { background-color: #EF6C00; }  
    .st-azul { background-color: #1565C0; }     

    /* Área PIX */
    .pix-box {
        background-color: #2C2C2C; padding: 15px; border-radius: 8px; margin-bottom: 15px; border: 1px dashed #555;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
def login(telefone_digitado, senha):
    try:
        nums = re.sub(r'\D', '', telefone_digitado)
        tel_fmt = telefone_digitado 
        if len(nums) == 11: tel_fmt = f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"
        elif len(nums) == 10: tel_fmt = f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
        response = supabase.table('clientes').select('*').eq('telefone', tel_fmt).eq('senha_web', senha).execute()
        return response.data[0] if response.data else None
    except: return None

# --- UPLOAD DE COMPROVANTE ---
def enviar_pagamento(client_id, valor, metodo, arquivo):
    try:
        url_publica = None
        if arquivo:
            # Nome do arquivo: ID_CLIENTE_TIMESTAMP.ext
            ext = arquivo.name.split('.')[-1]
            nome_arq = f"{client_id}_{int(datetime.now().timestamp())}.{ext}"
            
            # Upload para o Bucket 'comprovantes'
            # ATENÇÃO: Precisa criar o bucket 'comprovantes' no Supabase Storage e deixá-lo público
            supabase.storage.from_("comprovantes").upload(path=nome_arq, file=arquivo.getvalue(), file_options={"content-type": arquivo.type})
            url_publica = supabase.storage.from_("comprovantes").get_public_url(nome_arq)

        # Insere na tabela como PENDENTE
        dados = {
            "cliente_id": client_id,
            "tipo": "compra", # Crédito
            "valor_em_creditos": valor,
            "metodo_pagamento": metodo,
            "status_transacao": "Pendente", # Aguarda sua aprovação
            "data_transacao": datetime.now().isoformat(),
            "observacoes": f"Enviado pelo Portal. Comp: {'Sim' if url_publica else 'Não'}",
            "url_comprovante": url_publica
        }
        supabase.table("transacoes_creditos").insert(dados).execute()
        return True
    except Exception as e:
        st.error(f"Erro ao enviar: {e}")
        return False

# --- DADOS ---
def carregar_dados_financeiros(client_id):
    resp_pag = supabase.table('transacoes_creditos').select('*').eq('cliente_id', client_id).eq('tipo', 'compra').execute()
    resp_serv = supabase.table('agendamentos').select(
        "id, data_hora, status, observacoes, animais(nome), servicos_base(nome_servico), lancamentos_servicos(valor_total_cobrado, status_pagamento)"
    ).eq('animais.cliente_id', client_id).execute()
    
    lista = []
    saldo = 0.0
    
    for p in resp_pag.data:
        v = float(p.get('valor_em_creditos') or 0)
        status = p.get('status_transacao')
        if status == 'Confirmado': saldo += v
        
        label = "Confirmado" if status == 'Confirmado' else "Pendente"
        css = "st-azul" if status == 'Confirmado' else "st-vermelho"
        # Se for pendente, avisa que está em análise
        obs_texto = p.get('observacoes') or f"Via {p.get('metodo_pagamento')}"
        if status == 'Pendente': obs_texto = "Em análise..."

        lista.append({
            'dt': p['data_transacao'], 'pet': 'Geral', 'desc': f"Crédito ({p.get('metodo_pagamento')})", 
            'val': v, 'tipo': 'cred', 'label': label, 'css': css, 'ref': obs_texto
        })

    for s in resp_serv.data:
        if not s.get('animais'): continue
        lanc = s.get('lancamentos_servicos')
        lanc = lanc[0] if isinstance(lanc, list) and lanc else (lanc if isinstance(lanc, dict) else {})
        v = float(lanc.get('valor_total_cobrado') or 0)
        
        st_ag = s['status']
        st_fin = lanc.get('status_pagamento')
        if st_ag == 'Concluído': saldo -= v
        
        if st_ag == 'Agendado': label, css = "Agendado", "st-laranja"
        elif st_ag == 'Concluído':
            if st_fin == 'Pago': label, css = "Pago", "st-verde"
            else: label, css = "Pendente", "st-vermelho"
        elif st_ag == 'Cancelado': label, css = "Cancelado", "st-vermelho"
        else: label, css = st_ag, "st-laranja"

        lista.append({
            'dt': s['data_hora'], 'pet': s['animais'].get('nome', 'Pet'), 'desc': s['servicos_base'].get('nome_servico', 'Serviço'),
            'val': v, 'tipo': 'deb', 'label': label, 'css': css, 'ref': s.get('observacoes') or '',
            'status_ag': st_ag
        })
    
    # Lógica Agendado (Pago)
    if saldo > 0:
        agendados_indices = [i for i, item in enumerate(lista) if item['tipo'] == 'deb' and item['status_ag'] == 'Agendado']
        agendados_indices.sort(key=lambda idx: lista[idx]['dt'])
        saldo_temp = saldo
        for idx in agendados_indices:
            if saldo_temp >= lista[idx]['val']:
                lista[idx]['label'] = "Agendado (Pago)"
                lista[idx]['css'] = "st-verde-claro"
                saldo_temp -= lista[idx]['val']
            else: break

    return saldo, lista

MESES = {1:'JANEIRO', 2:'FEVEREIRO', 3:'MARÇO', 4:'ABRIL', 5:'MAIO', 6:'JUNHO', 7:'JULHO', 8:'AGOSTO', 9:'SETEMBRO', 10:'OUTUBRO', 11:'NOVEMBRO', 12:'DEZEMBRO'}

# --- APP ---
if 'cliente_logado' not in st.session_state: st.session_state['cliente_logado'] = None

if not st.session_state['cliente_logado']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h2 style='text-align: center;'>Gestão PetShop</h2>", unsafe_allow_html=True)
        with st.form("login"):
            tel = st.text_input("Telefone", placeholder="(99) 99999-9999")
            sen = st.text_input("Senha", type="password")
            if st.form_submit_button("ENTRAR"):
                user = login(tel, sen)
                if user:
                    st.session_state['cliente_logado'] = user
                    st.rerun()
                else: st.error("Dados inválidos.")
else:
    cli = st.session_state['cliente_logado']
    st.sidebar.markdown(f"### 👤 {cli['nome'].split()[0]}")
    if st.sidebar.button("Sair"):
        st.session_state['cliente_logado'] = None
        st.rerun()
        
    saldo, dados = carregar_dados_financeiros(cli['id'])
    
    # 1. SALDO
    cor_s = "neon-green" if saldo >= 0 else "neon-red"
    txt_s = "CRÉDITO" if saldo >= 0 else "DÉBITO"
    st.markdown(f"""<div class="saldo-container"><div class="saldo-label">SEU SALDO ATUAL</div><div class="saldo-valor {cor_s}">R$ {abs(saldo):.2f}</div><div class="saldo-status">Status: {txt_s}</div></div>""", unsafe_allow_html=True)
    
    # 2. NOVO PAGAMENTO (Expandir)
    with st.expander("💸 INFORMAR PAGAMENTO / PIX"):
        st.markdown("""
        <div class="pix-box">
            <b>Chave PIX:</b> 19992944966 (Celular)<br>
            <b>Favorecido:</b> Cantinho da Tosa<br>
            <span style="font-size:12px; color:#888;">Faça o pagamento pelo seu banco e anexe o comprovante abaixo.</span>
        </div>
        """, unsafe_allow_html=True)
        
        with st.form("form_pagamento"):
            c_val, c_met = st.columns(2)
            val_pag = c_val.number_input("Valor Pago (R$)", min_value=0.0, step=10.0)
            met_pag = c_met.selectbox("Forma", ["Pix", "Cartão Crédito", "Cartão Débito", "Dinheiro"])
            arq = st.file_uploader("Comprovante (Imagem/PDF)", type=['png','jpg','jpeg','pdf'])
            
            if st.form_submit_button("ENVIAR COMPROVANTE"):
                if val_pag > 0:
                    with st.spinner("Enviando..."):
                        if enviar_pagamento(cli['id'], val_pag, met_pag, arq):
                            st.success("Pagamento enviado para análise! O saldo atualizará após a confirmação.")
                            time.sleep(2)
                            st.rerun()
                else:
                    st.warning("Informe o valor.")

    # 3. TABELAS
    if dados:
        df = pd.DataFrame(dados)
        df['date_obj'] = pd.to_datetime(df['dt'])
        df = df.sort_values(by='date_obj', ascending=False)
        df['ano'] = df['date_obj'].dt.year
        df['mes'] = df['date_obj'].dt.month
        
        for (ano, mes), grupo_mes in df.groupby(['ano', 'mes'], sort=False):
            nome_mes = MESES[mes]
            total_gastos = grupo_mes[grupo_mes['tipo']=='deb']['val'].sum()
            
            pets_no_mes = grupo_mes[grupo_mes['pet'] != 'Geral']['pet'].unique()
            pets_str = ", ".join(pets_no_mes) if len(pets_no_mes) > 0 else "Geral"
            
            html = f"""
<table class="custom-table">
    <tr>
        <td class="header-main" colspan="2">{nome_mes} {ano} <span style="color:#444; margin:0 10px;">|</span> {cli['nome'].split()[0]} - {pets_str}</td>
        <td class="header-main" style="text-align:right">TOTAL</td>
        <td class="header-main" style="text-align:right">R$ {total_gastos:.2f}</td>
    </tr>
    <tr>
        <td class="col-header">Data</td>
        <td class="col-header">Descrição</td>
        <td class="col-header" style="text-align:right">Valor</td>
        <td class="col-header">Status</td>
    </tr>
"""
            servicos = grupo_mes[grupo_mes['tipo'] == 'deb']
            if not servicos.empty:
                html += """<tr><td colspan="4" class="section-header sec-serv">SERVIÇOS REALIZADOS</td></tr>"""
                for _, row in servicos.iterrows():
                    d = row['date_obj'].strftime("%d/%b").lower()
                    v = f"R$ {row['val']:.2f}"
                    status = f"<span class='status-pill {row['css']}'>{row['label']}</span>"
                    html += f"""<tr class="row-data"><td class="center-col">{d}</td><td class="left-col">{row['desc']}</td><td class="val-col">{v}</td><td class="center-col">{status}</td></tr>"""

            pagamentos = grupo_mes[grupo_mes['tipo'] == 'cred']
            if not pagamentos.empty:
                html += """<tr><td colspan="4" class="section-header sec-pag">PAGAMENTOS / CRÉDITOS</td></tr>"""
                for _, row in pagamentos.iterrows():
                    d = row['date_obj'].strftime("%d/%b").lower()
                    v = f"+ R$ {row['val']:.2f}"
                    status = f"<span class='status-pill {row['css']}'>{row['label']}</span>"
                    html += f"""<tr class="row-data"><td class="center-col">{d}</td><td class="left-col">{row['desc']}</td><td class="val-col" style="color:#2E7D32;">{v}</td><td class="center-col">{status}</td></tr>"""

            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)
            
    else:
        st.info("Nenhum histórico encontrado.")
