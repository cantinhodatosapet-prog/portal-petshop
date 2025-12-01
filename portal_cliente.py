import streamlit as st
from supabase import create_client
from datetime import datetime, date
import pandas as pd
import time
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
    .stApp { background-color: #211A18; color: white; }
    .stTextInput > div > div > input { background-color: #4E342E; color: white; border-radius: 10px; border: none; }
    .stButton > button { background-color: #6D4C41; color: white; border-radius: 20px; border: none; width: 100%; }
    .stButton > button:hover { background-color: #5D4037; color: #FFD700; }
    .history-card { background-color: #4E342E; padding: 15px; border-radius: 10px; margin-bottom: 10px; border-left: 5px solid #808080; }
    .card-servico-concluido { border-left-color: #33FF33; }
    .card-servico-pendente { border-left-color: #FF3333; }
    .card-pagamento { border-left-color: #33B5E5; }
    .card-agendado { border-left-color: #FFA500; }
    .card-header { display: flex; justify-content: space-between; font-weight: bold; font-size: 16px; margin-bottom: 5px; }
    .card-sub { font-size: 14px; color: #D7CCC8; }
    .card-value { font-weight: bold; font-size: 16px; text-align: right; }
    .text-green { color: #33FF33; } .text-red { color: #FF3333; } .text-blue { color: #33B5E5; } .text-orange { color: #FFA500; }
    .saldo-box { background-color: rgba(0,0,0,0.2); padding: 20px; border-radius: 15px; text-align: center; margin-bottom: 20px; }
    .saldo-valor { font-size: 32px; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

# --- FUNÇÃO DE LOGIN INTELIGENTE ---
def login(telefone_digitado, senha):
    try:
        # 1. Limpa tudo que não é número
        nums = re.sub(r'\D', '', telefone_digitado)
        
        # 2. Aplica a mesma máscara do App Admin
        telefone_formatado = telefone_digitado # Fallback
        
        if len(nums) == 11:
            # (19) 99294-4966
            telefone_formatado = f"({nums[:2]}) {nums[2:7]}-{nums[7:]}"
        elif len(nums) == 10:
            # (19) 3333-4444
            telefone_formatado = f"({nums[:2]}) {nums[2:6]}-{nums[6:]}"
        
        # 3. Busca no banco usando o formato correto
        response = supabase.table('clientes').select('*').eq('telefone', telefone_formatado).eq('senha_web', senha).execute()
        
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"Erro login: {e}")
        return None

def carregar_dados_financeiros(client_id):
    # 1. Pagamentos Confirmados
    resp_pag = supabase.table('transacoes_creditos').select('*').eq('cliente_id', client_id).eq('tipo', 'compra').execute()
    pagamentos = resp_pag.data
    
    # 2. Serviços (Agendamentos + Lançamentos)
    resp_serv = supabase.table('agendamentos').select(
        "id, data_hora, status, observacoes, animais(nome), servicos_base(nome_servico), lancamentos_servicos(valor_total_cobrado, valor_pago, status_pagamento)"
    ).eq('animais.cliente_id', client_id).execute()
    
    lista_unificada = []
    saldo_calculado = 0.0
    
    for p in pagamentos:
        valor = float(p.get('valor_em_creditos') or 0)
        status = p.get('status_transacao')
        if status == 'Confirmado': saldo_calculado += valor
        lista_unificada.append({
            'tipo': 'pagamento', 'data_iso': p['data_transacao'], 'titulo': 'PAGAMENTO',
            'descricao': f"Método: {p.get('metodo_pagamento') or 'N/A'}", 'valor': valor,
            'status': status, 'obs': p.get('observacoes'), 'comprovante': p.get('url_comprovante')
        })

    for s in resp_serv.data:
        if not s.get('animais'): continue
        lanc = s.get('lancamentos_servicos')
        if isinstance(lanc, list) and lanc: lanc = lanc[0]
        elif isinstance(lanc, dict): lanc = lanc
        else: lanc = {}
        valor_total = float(lanc.get('valor_total_cobrado') or 0)
        status_ag = s['status']; status_fin = lanc.get('status_pagamento')
        pet_nome = s['animais'].get('nome', 'Pet'); serv_nome = s['servicos_base'].get('nome_servico', 'Serviço')
        if status_ag == 'Concluído': saldo_calculado -= valor_total
        lista_unificada.append({
            'tipo': 'servico', 'data_iso': s['data_hora'], 'titulo': 'SERVIÇO',
            'descricao': f"{pet_nome} | {serv_nome}", 'valor': valor_total,
            'status': status_ag, 'status_fin': status_fin, 'obs': s.get('observacoes')
        })
        
    lista_unificada.sort(key=lambda x: x['data_iso'], reverse=True)
    return saldo_calculado, lista_unificada

# --- TELA PRINCIPAL ---
if 'cliente_logado' not in st.session_state:
    st.session_state['cliente_logado'] = None

if st.session_state['cliente_logado'] is None:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.title("Gestão PetShop")
    st.markdown("### Área do Cliente")
    
    with st.form("login_form"):
        # Placeholder orienta o usuário, mas a lógica aceita apenas números também
        tel = st.text_input("Telefone", placeholder="(11) 99999-9999")
        senha = st.text_input("Senha", type="password", placeholder="Senha Web")
        submitted = st.form_submit_button("ACESSAR")
        
        if submitted:
            user = login(tel, senha)
            if user:
                st.session_state['cliente_logado'] = user
                st.rerun()
            else:
                st.error("Telefone ou senha incorretos.")
else:
    cliente = st.session_state['cliente_logado']
    st.sidebar.title(f"Olá, {cliente['nome'].split()[0]}!")
    if st.sidebar.button("Sair"):
        st.session_state['cliente_logado'] = None
        st.rerun()
        
    saldo_real, historico = carregar_dados_financeiros(cliente['id'])
    cor_saldo = "text-green" if saldo_real >= 0 else "text-red"
    txt_saldo = "CRÉDITO" if saldo_real >= 0 else "DÉBITO"
    
    st.markdown(f"""<div class="saldo-box"><div style="font-size: 14px; color: #D7CCC8;">SEU SALDO ATUAL</div><div class="{cor_saldo} saldo-valor">R$ {abs(saldo_real):.2f}</div><div style="font-size: 12px; color: #AAA;">Status: {txt_saldo}</div></div>""", unsafe_allow_html=True)
    
    with st.expander("Filtros de Visualização"):
        col1, col2 = st.columns(2)
        with col1: filtro_tipo = st.multiselect("Mostrar:", ["Serviços", "Pagamentos"], default=["Serviços", "Pagamentos"])
        with col2: filtro_status = st.multiselect("Status:", ["Concluído", "Pendente", "Agendado"], default=["Concluído", "Pendente", "Agendado"])
            
    st.markdown("### Histórico")
    for item in historico:
        if item['tipo'] == 'servico' and "Serviços" not in filtro_tipo: continue
        if item['tipo'] == 'pagamento' and "Pagamentos" not in filtro_tipo: continue
        
        try: dt_obj = datetime.fromisoformat(item['data_iso'])
        except: dt_obj = datetime.now()
        data_fmt = dt_obj.strftime("%d/%m/%Y - %H:%M")
        css_card = "history-card"; cor_valor = "white"; texto_status = item['status']
        
        html_content = ""
        if item['tipo'] == 'servico':
            if item['status'] == 'Concluído':
                if item['status_fin'] == 'Pendente':
                    css_card += " card-servico-pendente"; cor_valor = "text-red"; texto_status = "Concluído (Pendente)"
                    if "Pendente" not in filtro_status: continue
                else:
                    css_card += " card-servico-concluido"; cor_valor = "text-green"; texto_status = "Concluído (Pago)"
                    if "Concluído" not in filtro_status: continue
            elif item['status'] == 'Agendado':
                css_card += " card-agendado"; cor_valor = "text-orange"
                if "Agendado" not in filtro_status: continue
            else: continue 
            
            html_content = f"""<div class="{css_card}"><div class="card-header"><span>{item['descricao']}</span><span class="{cor_valor}">R$ {item['valor']:.2f}</span></div><div class="card-sub">Data: {data_fmt}</div><div class="card-sub">Status: {texto_status}</div><div class="card-sub" style="font-style: italic;">{item['obs'] or ''}</div></div>"""
        
        elif item['tipo'] == 'pagamento':
            if item['status'] == 'Confirmado':
                css_card += " card-pagamento"; cor_valor = "text-blue"
                html_content = f"""<div class="{css_card}"><div class="card-header"><span>{item['titulo']}</span><span class="{cor_valor}">+ R$ {item['valor']:.2f}</span></div><div class="card-sub">Data: {data_fmt}</div><div class="card-sub">{item['descricao']}</div><div class="card-sub">Status: Confirmado</div></div>"""

        if html_content:
            st.markdown(html_content, unsafe_allow_html=True)
            if item.get('comprovante'): st.link_button("📄 Ver Comprovante", item['comprovante'])