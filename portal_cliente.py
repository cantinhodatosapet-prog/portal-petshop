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
            
            # --- CORREÇÃO: HTML sem indentação para não quebrar o visual ---
            html_tabela = f"""
<table class="custom-table">
    <tr>
        <td class="header-month" colspan="2">{nome_mes} - {ano}</td>
        <td class="header-month" style="text-align:right">Total</td>
        <td class="header-month" style="text-align:right">R$ {total_mes:.2f}</td>
    </tr>
"""
            
            pets_no_mes = grupo['pet'].unique()
            
            for pet in pets_no_mes:
                df_pet = grupo[grupo['pet'] == pet]
                
                # Cabeçalho do Pet
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
