import streamlit as st
import json
import re
import requests
import pandas as pd

# Configuração da página
st.set_page_config(page_title="Analista Logístico SPX", page_icon="📦", layout="wide")

st.title("📦 Analista Logístico Inteligente")
st.markdown("Integração direta com o portal SPX via API.")

# Sidebar para configurações de acesso
with st.sidebar:
    st.header("🔑 Configuração de Acesso")
    sessao_colada = st.text_area("Sessão ou Cookie Cru:", height=200, help="Cole aqui o Cookie gigante da aba Network.")
    st.info("A sessão é mantida apenas na memória temporária desta aba.")

# Área principal
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("🚀 Extração em Lote")
    lista_brs = st.text_area("Lista de Shipment IDs (um por linha):", 
                             placeholder="BR262635244052P\nBR123456789...",
                             height=200)
    
    botao_executar = st.button("Buscar Dados das BRs", use_container_width=True)

# Lógica de Extração
if botao_executar:
    if not sessao_colada:
        st.error("❌ Milorde, por favor cole a sessão na barra lateral.")
    elif not lista_brs:
        st.warning("⚠️ Insira ao menos um código de remessa (BR).")
    else:
        try:
            # 1. Modo de Leitura Inteligente (Aceita JSON ou Texto Cru)
            try:
                dados_sessao = json.loads(sessao_colada)
                cookies_string = dados_sessao.get('cookies', '')
            except json.JSONDecodeError:
                cookies_string = sessao_colada # Assume que é o texto cru copiado da Network
            
            # 2. Extrair CSRF Token
            csrf_match = re.search(r'csrftoken=([^;]+)', cookies_string)
            csrf_token = csrf_match.group(1) if csrf_match else 'dummy_token'
            
            # 3. Limpar a lista de BRs
            ids_para_buscar = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
            
            if not ids_para_buscar:
                st.error("❌ Nenhum código BR válido foi detectado no texto.")
            else:
                headers = {
                    'Cookie': cookies_string,
                    'X-CSRFToken': csrf_token,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json, text/plain, */*'
                }

                resultados = []
                progresso = st.progress(0)
                
                for i, shipment_id in enumerate(ids_para_buscar):
                    url = f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={shipment_id}"
                    
                    with st.spinner(f"Buscando {shipment_id}..."):
                        resp = requests.get(url, headers=headers)
                        if resp.status_code == 200:
                            dados_brutos = resp.json()
                            # Ajuste de navegação no JSON caso a estrutura da SPX seja encadeada
                            info = dados_brutos.get('data', dados_brutos)
                            info['shipment_id_search'] = shipment_id 
                            resultados.append(info)
                        else:
                            st.error(f"Erro no ID {shipment_id}: Status {resp.status_code} - Resposta: {resp.text}")
                    
                    progresso.progress((i + 1) / len(ids_para_buscar))

                # 4. Exibição dos Resultados em Tabela
                if resultados:
                    st.success(f"🎯 Extração concluída! {len(resultados)} remessas processadas.")
                    df = pd.DataFrame(resultados)
                    
                    st.subheader("📊 Tabela Consolidada")
                    st.dataframe(df, use_container_width=True)
                    
                    csv = df.to_csv(index=False).encode('utf-8')
                    st.download_button("📥 Baixar Planilha (CSV)", csv, "dados_spx.csv", "text/csv")

        except Exception as e:
            st.error(f"❌ Erro crítico: {e}")
