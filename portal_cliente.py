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

# --- ESTILOS CSS (Refinado conforme 'cli mel.png') ---
st.markdown("""
<style>
    /* Fundo Dark */
    .stApp { background-color: #121212; color: #E0E0E0; font-family: sans-serif; }
    
    /* Inputs e Botões */
    .stTextInput > div > div > input { background-color: #2C2C2C; color: white; border: 1px solid #444; border-radius: 5px; }
    .stButton > button { background-color: #4CAF50; color: white; font-weight: bold; width: 100%; border-radius: 5px; border: none; }
    .stButton > button:hover { background-color: #45a049; }
    
    /* BOX SALDO */
    .saldo-container {
        background-color: #1E1E1E;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 30px;
        border: 1px solid #333;
        box-shadow: 0 4px 15px rgba(0,0,0,0.6);
    }
    .saldo-titulo { font-size: 12px; color: #BBB; text-transform: uppercase; letter-spacing: 2px; margin-bottom: 5px; }
    .saldo-valor { font-size: 48px; font-weight: 900; margin: 0; line-height: 1.1; }
    .saldo-status { font-size: 14px; color: #888; margin-top: 5px; }
    .neon-green { color: #39FF14; text-shadow: 0 0 15px rgba(57, 255, 20, 0.5); }
    .neon-red { color: #FF4444; text-shadow: 0 0 15px rgba(255, 68, 68, 0.5); }

    /* TABELA FLUIDA */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 25px;
        background-color: #D1C4A9; /* Cor de fundo base para evitar buracos */
    }
    
    /* 1. Cabeçalho do Mês (Dourado/Bege Escuro) */
    .header-month {
        background-color: #8B7D5B;
        color: #000;
        font-weight: 800;
        text-transform: uppercase;
        padding: 12px 15px;
        font-size: 14px;
        border: 1px solid #555;
        letter-spacing: 0.5px;
    }
    
    /* 2. Barra Cliente | Pet (Bege e Azul) */
    .header-client {
        background-color: #E0D6BC; /* Bege mais claro */
        color: #000;
        font-weight: 700;
        padding: 10px 15px;
        border: 1px solid #999;
        font-size: 14px;
        width: 35%;
        vertical-align: middle;
    }
    .header-pet {
        background-color: #B0C4DE; /* Azul suave */
        color: #000;
        font-weight: 700;
        text-align: center;
        padding: 10px;
        border: 1px solid #999;
        font-size: 14px;
        vertical-align: middle;
    }
    
    /* 3. Títulos das Colunas (Data, Serviço...) */
    .col-header {
        background-color: #A69B80; /* Tom intermediário */
        color: #000;
        font-weight: 700;
        text-align: center;
        font-size: 13px;
        padding: 6px;
        border: 1px solid #777;
    }
    
    /* 4. Linhas de Dados */
    .row-data td {
        background-color: #DAE5F0; /* Azul bem clarinho */
        color: #000;
        border-bottom: 1px solid #FFF;
        border-right: 1px solid #FFF;
        padding: 12px 8px;
        font-size: 13px;
        vertical-align: middle;
    }
    .row-data td:last-child { border-right: none; }
    
    /* Utilitários de Texto */
    .center-col { text-align: center; }
    .left-col { text-align: left; padding-left: 10px !important; }
    .val-col { text-align: right; font-weight: 700; padding-right: 15px !important; white-space: nowrap; }
    .ref-col { font-size: 11px; color: #444; font-style: italic; line-height: 1.2; text-align: center;}
    
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

# --- DADOS ---
def carregar_dados_financeiros(client_id):
    # Pagamentos (Créditos)
    resp_pag = supabase.table('transacoes_creditos').select('*').eq('cliente_id', client_id).eq('tipo', 'compra').execute()
    # Serviços (Débitos)
    resp_serv = supabase.table('agendamentos').select(
        "id, data_hora, status, observacoes, animais(nome), servicos_base(nome_servico), lancamentos_servicos(valor_total_cobrado, status_pagamento)"
    ).eq('animais.cliente_id', client_id).execute()
    
    lista = []
    saldo = 0.0
    
    # Processa Pagamentos
    for p in resp_pag.data:
        v = float(p.get('valor_em_creditos') or 0)
        if p.get('status_transacao') == 'Confirmado': 
            saldo += v
        
        # Pagamento entra como "Conta Geral"
        lista.append({
            'dt': p['data_transacao'], 
            'pet': 'Conta Geral', 
            'serv': f"Crédito ({p.get('metodo_pagamento')})", 
            'val': v, 
            'tipo': 'cred', 
            'obs': p.get('observacoes') or '',
            'status': p.get('status_transacao')
        })

    # Processa Serviços
    for s in resp_serv.data:
        if not s.get('animais'): continue
        lanc = s.get('lancamentos_servicos')
        lanc = lanc[0] if isinstance(lanc, list) and lanc else (lanc if isinstance(lanc, dict) else {})
        v = float(lanc.get('valor_total_cobrado') or 0)
        
        if s['status'] == 'Concluído': 
            saldo -= v
        
        lista.append({
            'dt': s['data_hora'], 
            'pet': s['animais'].get('nome', 'Pet'), 
            'serv': s['servicos_base'].get('nome_servico', 'Serviço'), 
            'val': v, 
            'tipo': 'deb', 
            'obs': s.get('observacoes') or '',
            'status': s['status']
        })
        
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
    
    # 1. SALDO NEON
    cor_s = "neon-green" if saldo >= 0 else "neon-red"
    txt_s = "CRÉDITO" if saldo >= 0 else "DÉBITO"
    
    st.markdown(f"""
    <div class="saldo-container">
        <div class="saldo-titulo">SEU SALDO ATUAL</div>
        <div class="saldo-valor {cor_s}">R$ {abs(saldo):.2f}</div>
        <div class="saldo-status">Status: {txt_s}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. TABELAS (Group By Mês -> Depois por Pet)
    if dados:
        df = pd.DataFrame(dados)
        df['date_obj'] = pd.to_datetime(df['dt'])
        df = df.sort_values(by='date_obj', ascending=False)
        df['ano'] = df['date_obj'].dt.year
        df['mes'] = df['date_obj'].dt.month
        
        # Loop por Mês
        for (ano, mes), grupo_mes in df.groupby(['ano', 'mes'], sort=False):
            nome_mes = MESES[mes]
            total_mes = grupo_mes[grupo_mes['tipo']=='deb']['val'].sum()
            
            # ATENÇÃO: HTML colado à esquerda para evitar quebra de código no Streamlit
            html = f"""<table class="custom-table">
<tr>
<td class="header-month" colspan="2">{nome_mes} - {ano}</td>
<td class="header-month" style="text-align:right">TOTAL</td>
<td class="header-month" style="text-align:right">R$ {total_mes:.2f}</td>
</tr>"""
            
            # Loop por Pet dentro do Mês (Cria o bloco Cliente | Pet uma vez)
            pets = grupo_mes['pet'].unique()
            for pet in pets:
                df_pet = grupo_mes[grupo_mes['pet'] == pet]
                
                # Título do Grupo (Tamara | Capitu ou Tamara | Conta Geral)
                html += f"""
<tr>
<td class="header-client" colspan="1">{cli['nome'].split()[0]}</td>
<td class="header-pet" colspan="3">{pet}</td>
</tr>
<tr>
<td class="col-header">Data</td>
<td class="col-header">Serviço</td>
<td class="col-header" style="text-align:right">Valor</td>
<td class="col-header">Ref</td>
</tr>"""
                
                # Linhas de Itens
                for _, row in df_pet.iterrows():
                    d_str = row['date_obj'].strftime("%d-%b").lower()
                    v_str = f"R$ {row['val']:.2f}"
                    obs_ref = row['obs'] if row['obs'] else ""
                    
                    if row['tipo'] == 'cred': 
                        v_str = f"+ {v_str}"
                    
                    html += f"""
<tr class="row-data">
<td class="center-col">{d_str}</td>
<td class="left-col">{row['serv']}</td>
<td class="val-col">{v_str}</td>
<td class="ref-col">{obs_ref}</td>
</tr>"""
            
            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)
            
    else:
        st.info("Nenhum histórico encontrado.")
