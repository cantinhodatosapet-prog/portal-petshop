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

# --- ESTILOS CSS (VISUAL IDÊNTICO À IMAGEM) ---
st.markdown("""
    <style>
    /* Fundo Geral Dark */
    .stApp { background-color: #1E1E1E; color: white; }
    
    /* Inputs e Botões */
    .stTextInput > div > div > input { background-color: #333; color: white; border: 1px solid #555; }
    .stButton > button { background-color: #4CAF50; color: white; border-radius: 5px; width: 100%; font-weight: bold;}
    
    /* BOX DE SALDO (Topo) */
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

    /* TABELA ESTILIZADA (Ideal.jpeg) */
    .custom-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        font-family: sans-serif;
        color: #000; /* Texto preto na tabela */
    }
    
    /* Cabeçalho do Mês (Bege Escuro/Dourado) */
    .header-month {
        background-color: #8B7D5B; /* Cor aproximada da imagem */
        color: #000;
        font-weight: bold;
        text-transform: uppercase;
        padding: 8px;
        border: 1px solid #555;
    }
    
    /* Linha do Cliente/Pet (Azul Claro e Bege) */
    .header-sub {
        background-color: #D1C4A9; /* Bege claro */
        font-weight: bold;
        border: 1px solid #999;
    }
    .header-sub-blue {
        background-color: #B0C4DE; /* Azul acinzentado */
        text-align: center;
        border: 1px solid #999;
    }
    
    /* Cabeçalho das Colunas (Data, Serviço...) */
    .col-header {
        background-color: #8B7D5B;
        color: #000;
        font-weight: bold;
        text-align: center;
        font-size: 14px;
        border: 1px solid #555;
        padding: 4px;
    }
    
    /* Linhas de Dados (Azul Claro / Branco alternado) */
    .row-data {
        background-color: #C8D6E5; /* Azul claro tabela */
        border-bottom: 1px solid #FFF;
        font-size: 14px;
    }
    .row-data td { padding: 8px 4px; border-right: 2px solid white; }
    .row-data td:last-child { border-right: none; }
    
    .val-col { text-align: right; font-weight: bold; padding-right: 10px !important; }
    .center-col { text-align: center; }
    
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DE LOGIN ---
def login(telefone_digitado, senha):
    try:
        nums = re.sub(r'\D', '', telefone_digitado)
        telefone_formatado = telefone_digitado 
        if len(nums) == 11: telefone_formatado = f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"
        elif len(nums) == 10: telefone_formatado = f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
        
        response = supabase.table('clientes').select('*').eq('telefone', telefone_formatado).eq('senha_web', senha).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro login: {e}")
        return None

# --- CARREGAMENTO DE DADOS ---
def carregar_dados_financeiros(client_id):
    # 1. Busca Pagamentos
    resp_pag = supabase.table('transacoes_creditos').select('*').eq('cliente_id', client_id).eq('tipo', 'compra').execute()
    
    # 2. Busca Serviços
    resp_serv = supabase.table('agendamentos').select(
        "id, data_hora, status, observacoes, animais(nome), servicos_base(nome_servico), lancamentos_servicos(valor_total_cobrado, valor_pago, status_pagamento)"
    ).eq('animais.cliente_id', client_id).execute()
    
    lista_unificada = []
    saldo_calculado = 0.0
    
    # Processa Pagamentos
    for p in resp_pag.data:
        valor = float(p.get('valor_em_creditos') or 0)
        if p.get('status_transacao') == 'Confirmado':
            saldo_calculado += valor
            
        lista_unificada.append({
            'data': p['data_transacao'],
            'pet': 'Conta Geral', # Pagamento entra como geral ou associado ao cliente
            'servico': f"Crédito ({p.get('metodo_pagamento')})",
            'valor': valor,
            'tipo': 'credito',
            'obs': p.get('observacoes') or '',
            'status': p.get('status_transacao')
        })

    # Processa Serviços
    for s in resp_serv.data:
        if not s.get('animais'): continue
        lanc = s.get('lancamentos_servicos')
        if isinstance(lanc, list) and lanc: lanc = lanc[0]
        elif isinstance(lanc, dict): lanc = lanc
        else: lanc = {}
        
        valor_total = float(lanc.get('valor_total_cobrado') or 0)
        status_ag = s['status']
        
        # Debita do saldo se concluído
        if status_ag == 'Concluído':
            saldo_calculado -= valor_total
            
        # Só mostra na tabela se tiver valor ou for agendado/concluído
        lista_unificada.append({
            'data': s['data_hora'],
            'pet': s['animais'].get('nome', 'Pet'),
            'servico': s['servicos_base'].get('nome_servico', 'Serviço'),
            'valor': valor_total,
            'tipo': 'debito',
            'obs': s.get('observacoes') or '',
            'status': status_ag
        })
        
    return saldo_calculado, lista_unificada

# --- MAPA DE MESES (PT-BR) ---
MESES_PT = {
    1: 'JANEIRO', 2: 'FEVEREIRO', 3: 'MARÇO', 4: 'ABRIL', 5: 'MAIO', 6: 'JUNHO',
    7: 'JULHO', 8: 'AGOSTO', 9: 'SETEMBRO', 10: 'OUTUBRO', 11: 'NOVEMBRO', 12: 'DEZEMBRO'
}

# --- TELA PRINCIPAL ---
if 'cliente_logado' not in st.session_state:
    st.session_state['cliente_logado'] = None

if st.session_state['cliente_logado'] is None:
    # TELA DE LOGIN
    st.markdown("<br>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown("<h2 style='text-align: center;'>Gestão PetShop</h2>", unsafe_allow_html=True)
        with st.form("login_form"):
            tel = st.text_input("Telefone", placeholder="(99) 99999-9999")
            senha = st.text_input("Senha", type="password", placeholder="Digite sua senha")
            submitted = st.form_submit_button("ENTRAR")
            
            if submitted:
                user = login(tel, senha)
                if user:
                    st.session_state['cliente_logado'] = user
                    st.rerun()
                else:
                    st.error("Dados inválidos.")

else:
    # ÁREA DO CLIENTE
    cliente = st.session_state['cliente_logado']
    
    # Sidebar
    st.sidebar.markdown(f"### 👤 {cliente['nome'].split()[0]}")
    if st.sidebar.button("Sair"):
        st.session_state['cliente_logado'] = None
        st.rerun()
        
    # Carrega Dados
    saldo, dados = carregar_dados_financeiros(cliente['id'])
    
    # 1. MOSTRAR SALDO (Estilo Neon da Imagem)
    cor_valor = "text-neon-green" if saldo >= 0 else "text-red"
    txt_status = "CRÉDITO" if saldo >= 0 else "DÉBITO"
    
    st.markdown(f"""
    <div class="saldo-container">
        <div class="saldo-label">SEU SALDO ATUAL</div>
        <div class="saldo-valor {cor_valor}">R$ {abs(saldo):.2f}</div>
        <div class="saldo-status">Status: {txt_status}</div>
    </div>
    """, unsafe_allow_html=True)
    
    # 2. PROCESSAMENTO TABELA (Group By Mês)
    if dados:
        df = pd.DataFrame(dados)
        df['dt_obj'] = pd.to_datetime(df['data'])
        df = df.sort_values(by='dt_obj', ascending=False)
        
        # Agrupa por Ano e Mês
        df['ano'] = df['dt_obj'].dt.year
        df['mes'] = df['dt_obj'].dt.month
        
        grupos = df.groupby(['ano', 'mes'], sort=False)
        
        for (ano, mes), grupo in grupos:
            nome_mes = MESES_PT[mes]
            total_mes = grupo[grupo['tipo'] == 'debito']['valor'].sum() # Soma gastos
            
            # Cabeçalho do Mês
            html_tabela = f"""
            <table class="custom-table">
                <tr>
                    <td class="header-month" colspan="2">{nome_mes} - {ano}</td>
                    <td class="header-month" style="text-align:right">Total</td>
                    <td class="header-month" style="text-align:right">R$ {total_mes:.2f}</td>
                </tr>
            """
            
            # Dentro do mês, vamos agrupar por PET (ou mostrar lista se preferir cronológico)
            # A imagem mostra agrupado por "Raquel" (Cliente) e "Megan" (Pet).
            # Vamos simular essa linha de subtítulo
            
            pets_no_mes = grupo['pet'].unique()
            
            for pet in pets_no_mes:
                df_pet = grupo[grupo['pet'] == pet]
                
                # Cabeçalho do Pet (Linha Bege/Azul)
                html_tabela += f"""
                <tr>
                    <td class="header-sub" colspan="1">{cliente['nome'].split()[0]}</td>
                    <td class="header-sub-blue" colspan="3">{pet}</td>
                </tr>
                <tr>
                    <td class="col-header">Data</td>
                    <td class="col-header">Serviço</td>
                    <td class="col-header" style="text-align:right">Valor</td>
                    <td class="col-header">Referência</td>
                </tr>
                """
                
                # Linhas de Dados
                for _, row in df_pet.iterrows():
                    dia_str = row['dt_obj'].strftime("%d-%b").lower() # Ex: 10-dez
                    valor_fmt = f"R$ {row['valor']:.2f}"
                    obs_ref = row['obs'][:20] + "..." if len(row['obs']) > 20 else row['obs']
                    
                    # Se for crédito (pagamento), mostra diferente ou ignora no total de gastos?
                    # Na imagem "Pagamento-pix" aparece. Vamos mostrar.
                    
                    html_tabela += f"""
                    <tr class="row-data">
                        <td class="center-col">{dia_str}</td>
                        <td class="center-col">{row['servico']}</td>
                        <td class="val-col">{valor_fmt}</td>
                        <td class="center-col" style="font-size:11px; color:#555;">{obs_ref}</td>
                    </tr>
                    """
            
            html_tabela += "</table>"
            st.markdown(html_tabela, unsafe_allow_html=True)
            
    else:
        st.info("Nenhum histórico encontrado.")
