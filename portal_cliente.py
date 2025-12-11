import streamlit as st
from supabase import create_client
from datetime import datetime
import pandas as pd
import re

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
    .stApp { background-color: #1E1E1E; color: white; }
    .stTextInput > div > div > input { background-color: #333; color: white; border: 1px solid #555; }
    .stButton > button { background-color: #4CAF50; color: white; border-radius: 5px; width: 100%; font-weight: bold;}
    
    /* SALDO */
    .saldo-container {
        background-color: #121212;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        margin-bottom: 25px;
        border: 1px solid #333;
        box-shadow: 0 4px 6px rgba(0,0,0,0.3);
    }
    .saldo-label { font-size: 12px; color: #BBB; text-transform: uppercase; letter-spacing: 1px; }
    .saldo-valor { font-size: 42px; font-weight: 900; margin: 5px 0; }
    .text-neon-green { color: #39FF14; text-shadow: 0 0 10px rgba(57, 255, 20, 0.3); }
    .text-red { color: #FF4444; }
    .saldo-status { font-size: 12px; color: #888; }

    /* TABELA */
    .custom-table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-family: sans-serif; color: #000; }
    .header-month { background-color: #8B7D5B; color: #000; font-weight: bold; text-transform: uppercase; padding: 8px; border: 1px solid #555; }
    .header-sub { background-color: #D1C4A9; font-weight: bold; border: 1px solid #999; text-align: center; }
    .header-sub-blue { background-color: #B0C4DE; text-align: center; border: 1px solid #999; font-weight: bold; }
    .col-header { background-color: #8B7D5B; color: #000; font-weight: bold; text-align: center; font-size: 14px; border: 1px solid #555; padding: 4px; }
    .row-data { background-color: #C8D6E5; border-bottom: 1px solid #FFF; font-size: 14px; }
    .row-data td { padding: 8px 4px; border-right: 2px solid white; }
    .row-data td:last-child { border-right: none; }
    .val-col { text-align: right; font-weight: bold; padding-right: 10px !important; }
    .center-col { text-align: center; }
</style>
""", unsafe_allow_html=True)

# --- LOGIN ---
def login(telefone_digitado, senha):
    try:
        nums = re.sub(r'\D', '', telefone_digitado)
        telefone_formatado = telefone_digitado 
        if len(nums) == 11: telefone_formatado = f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"
        elif len(nums) == 10: telefone_formatado = f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
        response = supabase.table('clientes').select('*').eq('telefone', telefone_formatado).eq('senha_web', senha).execute()
        return response.data[0] if response.data else None
    except: return None

# --- DADOS ---
def carregar_dados_financeiros(client_id):
    # Pagamentos
    resp_pag = supabase.table('transacoes_creditos').select('*').eq('cliente_id', client_id).eq('tipo', 'compra').execute()
    # Serviços
    resp_serv = supabase.table('agendamentos').select("id, data_hora, status, observacoes, animais(nome), servicos_base(nome_servico), lancamentos_servicos(valor_total_cobrado, status_pagamento)").eq('animais.cliente_id', client_id).execute()
    
    lista = []
    saldo = 0.0
    
    for p in resp_pag.data:
        val = float(p.get('valor_em_creditos') or 0)
        if p.get('status_transacao') == 'Confirmado': saldo += val
        lista.append({'dt': p['data_transacao'], 'pet': 'Conta Geral', 'serv': f"Crédito ({p.get('metodo_pagamento')})", 'val': val, 'tipo': 'cred', 'obs': p.get('observacoes') or '', 'status': p.get('status_transacao')})

    for s in resp_serv.data:
        if not s.get('animais'): continue
        lanc = s.get('lancamentos_servicos')
        lanc = lanc[0] if isinstance(lanc, list) and lanc else (lanc if isinstance(lanc, dict) else {})
        val = float(lanc.get('valor_total_cobrado') or 0)
        if s['status'] == 'Concluído': saldo -= val
        lista.append({'dt': s['data_hora'], 'pet': s['animais'].get('nome', 'Pet'), 'serv': s['servicos_base'].get('nome_servico', 'Serviço'), 'val': val, 'tipo': 'deb', 'obs': s.get('observacoes') or '', 'status': s['status']})
        
    return saldo, lista

MESES = {1:'JANEIRO', 2:'FEVEREIRO', 3:'MARÇO', 4:'ABRIL', 5:'MAIO', 6:'JUNHO', 7:'JULHO', 8:'AGOSTO', 9:'SETEMBRO', 10:'OUTUBRO', 11:'NOVEMBRO', 12:'DEZEMBRO'}

# --- INTERFACE ---
if 'cliente_logado' not in st.session_state: st.session_state['cliente_logado'] = None

if not st.session_state['cliente_logado']:
    st.markdown("<br>", unsafe_allow_html=True)
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
    
    # SALDO
    cor = "text-neon-green" if saldo >= 0 else "text-red"
    txt = "CRÉDITO" if saldo >= 0 else "DÉBITO"
    st.markdown(f"""<div class="saldo-container"><div class="saldo-label">SEU SALDO ATUAL</div><div class="saldo-valor {cor}">R$ {abs(saldo):.2f}</div><div class="saldo-status">Status: {txt}</div></div>""", unsafe_allow_html=True)
    
    # TABELA
    if dados:
        df = pd.DataFrame(dados)
        df['date_obj'] = pd.to_datetime(df['dt'])
        df = df.sort_values(by='date_obj', ascending=False)
        df['ano'] = df['date_obj'].dt.year
        df['mes'] = df['date_obj'].dt.month
        
        # Agrupa por Mês
        for (ano, mes), grupo in df.groupby(['ano', 'mes'], sort=False):
            nome_mes = MESES[mes]
            total_mes = grupo[grupo['tipo'] == 'deb']['val'].sum()
            
            # HTML SEM INDENTAÇÃO para evitar bug do Streamlit
            html = f"""<table class="custom-table">
<tr>
<td class="header-month" colspan="2">{nome_mes} - {ano}</td>
<td class="header-month" style="text-align:right">Total</td>
<td class="header-month" style="text-align:right">R$ {total_mes:.2f}</td>
</tr>"""
            
            # Agrupa por Pet dentro do mês
            for pet in grupo['pet'].unique():
                df_pet = grupo[grupo['pet'] == pet]
                
                html += f"""
<tr>
<td class="header-sub" colspan="1">{cli['nome'].split()[0]}</td>
<td class="header-sub-blue" colspan="3">{pet}</td>
</tr>
<tr>
<td class="col-header">Data</td>
<td class="col-header">Serviço</td>
<td class="col-header" style="text-align:right">Valor</td>
<td class="col-header">Ref</td>
</tr>"""
                
                for _, row in df_pet.iterrows():
                    d_str = row['date_obj'].strftime("%d-%b").lower()
                    v_str = f"R$ {row['val']:.2f}"
                    obs = row['obs'][:20]
                    if row['tipo'] == 'cred': v_str = f"+ {v_str}"
                    
                    html += f"""
<tr class="row-data">
<td class="center-col">{d_str}</td>
<td class="center-col">{row['serv']}</td>
<td class="val-col">{v_str}</td>
<td class="center-col" style="font-size:11px; color:#555;">{obs}</td>
</tr>"""
            
            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Sem histórico.")
