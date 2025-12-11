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

# --- ESTILOS CSS (BASEADO NO SEU PRINT 'CLIENTES WEB.PNG' e 'IDEAL.JPEG') ---
st.markdown("""
    <style>
    /* Fundo Geral */
    .stApp { background-color: #1E1E1E; color: white; }
    
    /* Inputs */
    .stTextInput > div > div > input { background-color: #333; color: white; border: 1px solid #555; }
    .stButton > button { background-color: #4CAF50; color: white; font-weight: bold; width: 100%; border-radius: 5px; }
    
    /* SALDO BOX */
    .saldo-container {
        background-color: #121212;
        border-radius: 10px;
        padding: 25px;
        text-align: center;
        margin-bottom: 30px;
        border: 1px solid #333;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .saldo-titulo { font-size: 14px; color: #BBB; text-transform: uppercase; letter-spacing: 2px; }
    .saldo-valor { font-size: 48px; font-weight: 900; margin: 10px 0; }
    .saldo-status { font-size: 14px; color: #888; }
    .neon-green { color: #39FF14; text-shadow: 0 0 15px rgba(57, 255, 20, 0.4); }
    .neon-red { color: #FF4444; text-shadow: 0 0 15px rgba(255, 68, 68, 0.4); }

    /* TABELA CUSTOMIZADA */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        font-family: 'Arial', sans-serif;
        margin-bottom: 30px;
        color: #000;
    }
    
    /* Cabeçalho do Mês (Bege Escuro) */
    .header-month {
        background-color: #8B7D5B;
        color: #000;
        font-weight: bold;
        text-transform: uppercase;
        padding: 10px;
        border: 1px solid #555;
        font-size: 15px;
    }
    
    /* Linha do Cliente (Bege Claro) */
    .header-sub {
        background-color: #D1C4A9;
        font-weight: bold;
        padding: 8px;
        border: 1px solid #999;
        text-align: center;
    }
    
    /* Linha do Pet (Azul Claro) */
    .header-sub-blue {
        background-color: #B0C4DE;
        font-weight: bold;
        padding: 8px;
        border: 1px solid #999;
        text-align: center;
    }
    
    /* Cabeçalhos das Colunas */
    .col-header {
        background-color: #8B7D5B;
        color: #000;
        font-weight: bold;
        text-align: center;
        font-size: 14px;
        padding: 6px;
        border: 1px solid #666;
    }
    
    /* Linhas de Dados */
    .row-data td {
        background-color: #C8D6E5;
        border-bottom: 1px solid #FFF;
        border-right: 2px solid #FFF;
        padding: 10px 5px;
        font-size: 14px;
        vertical-align: middle;
    }
    .row-data td:last-child { border-right: none; }
    
    .center-col { text-align: center; }
    .val-col { text-align: right; font-weight: bold; padding-right: 15px !important; }
    
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
    except Exception as e:
        print(e)
        return None

# --- DADOS ---
def carregar_dados(client_id):
    # Pagamentos
    res_pag = supabase.table('transacoes_creditos').select('*').eq('cliente_id', client_id).eq('tipo', 'compra').execute()
    # Serviços
    res_serv = supabase.table('agendamentos').select(
        "id, data_hora, status, observacoes, animais(nome), servicos_base(nome_servico), lancamentos_servicos(valor_total_cobrado, status_pagamento)"
    ).eq('animais.cliente_id', client_id).execute()
    
    lista = []
    saldo = 0.0
    
    # Processar Pagamentos
    for p in res_pag.data:
        v = float(p.get('valor_em_creditos') or 0)
        if p.get('status_transacao') == 'Confirmado': saldo += v
        lista.append({
            'dt': p['data_transacao'], 'pet': 'Geral', 'servico': f"Crédito ({p.get('metodo_pagamento')})",
            'valor': v, 'tipo': 'cred', 'obs': p.get('observacoes') or '', 'status': p.get('status_transacao')
        })
        
    # Processar Serviços
    for s in res_serv.data:
        if not s.get('animais'): continue
        lanc = s.get('lancamentos_servicos')
        lanc = lanc[0] if isinstance(lanc, list) and lanc else (lanc if isinstance(lanc, dict) else {})
        v = float(lanc.get('valor_total_cobrado') or 0)
        if s['status'] == 'Concluído': saldo -= v
        
        lista.append({
            'dt': s['data_hora'], 
            'pet': s['animais'].get('nome', 'Pet'), 
            'servico': s['servicos_base'].get('nome_servico', 'Serviço'),
            'valor': v, 'tipo': 'deb', 'obs': s.get('observacoes') or '', 'status': s['status']
        })
        
    return saldo, lista

MESES = {1:'JANEIRO', 2:'FEVEREIRO', 3:'MARÇO', 4:'ABRIL', 5:'MAIO', 6:'JUNHO', 7:'JULHO', 8:'AGOSTO', 9:'SETEMBRO', 10:'OUTUBRO', 11:'NOVEMBRO', 12:'DEZEMBRO'}

# --- APP ---
if 'cliente_logado' not in st.session_state:
    st.session_state['cliente_logado'] = None

if not st.session_state['cliente_logado']:
    st.markdown("<br><br>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown("<h2 style='text-align:center;'>Área do Cliente</h2>", unsafe_allow_html=True)
        with st.form("login"):
            tel = st.text_input("Telefone", placeholder="(99) 99999-9999")
            sen = st.text_input("Senha", type="password")
            if st.form_submit_button("ENTRAR"):
                u = login(tel, sen)
                if u: 
                    st.session_state['cliente_logado'] = u
                    st.rerun()
                else: st.error("Dados inválidos.")
else:
    cli = st.session_state['cliente_logado']
    st.sidebar.write(f"Olá, {cli['nome'].split()[0]}")
    if st.sidebar.button("Sair"):
        st.session_state['cliente_logado'] = None
        st.rerun()
        
    saldo, dados = carregar_dados(cli['id'])
    
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
    
    # 2. TABELAS POR MÊS
    if dados:
        df = pd.DataFrame(dados)
        df['date_obj'] = pd.to_datetime(df['dt'])
        df = df.sort_values(by='date_obj', ascending=False)
        df['ano'] = df['date_obj'].dt.year
        df['mes'] = df['date_obj'].dt.month
        
        # Agrupa por Mês (Garante que cria uma tabela para CADA mês que tem dados)
        for (ano, mes), grupo_mes in df.groupby(['ano', 'mes'], sort=False):
            nome_mes = MESES[mes]
            total_mes = grupo_mes[grupo_mes['tipo']=='deb']['valor'].sum()
            
            # Inicia HTML da Tabela do Mês
            html = f"""
            <table class="custom-table">
                <tr>
                    <td class="header-month" colspan="2">{nome_mes} - {ano}</td>
                    <td class="header-month" style="text-align:right">Total Gasto</td>
                    <td class="header-month" style="text-align:right">R$ {total_mes:.2f}</td>
                </tr>
            """
            
            # Dentro do mês, agrupa por Pet para fazer os subtítulos
            pets = grupo_mes['pet'].unique()
            for pet in pets:
                df_pet = grupo_mes[grupo_mes['pet'] == pet]
                
                # Cabeçalho do Pet (Igual imagem)
                html += f"""
                <tr>
                    <td class="header-sub" colspan="1">{cli['nome'].split()[0]}</td>
                    <td class="header-sub-blue" colspan="3">{pet}</td>
                </tr>
                <tr>
                    <td class="col-header">Data</td>
                    <td class="col-header">Serviço</td>
                    <td class="col-header" style="text-align:right">Valor</td>
                    <td class="col-header">Referência</td>
                </tr>
                """
                
                # Linhas
                for _, row in df_pet.iterrows():
                    d_str = row['date_obj'].strftime("%d-%b").lower()
                    v_str = f"R$ {row['valor']:.2f}"
                    obs = row['obs'][:30]
                    # Se for Pagamento (Crédito), destaca diferente ou mostra normal
                    if row['tipo'] == 'cred': 
                        v_str = f"+ {v_str}"
                        obs = "Pagamento Recebido"
                    
                    html += f"""
                    <tr class="row-data">
                        <td class="center-col">{d_str}</td>
                        <td class="center-col">{row['servico']}</td>
                        <td class="val-col">{v_str}</td>
                        <td class="center-col" style="font-size:11px; color:#555;">{obs}</td>
                    </tr>
                    """
            
            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)
    else:
        st.info("Sem histórico.")
