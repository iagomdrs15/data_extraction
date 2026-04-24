import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="SPX Hub Porto Velho", page_icon="📦", layout="wide")

if 'cookie_session' not in st.session_state:
    st.session_state['cookie_session'] = ""

st.title("📦 Analista Logístico Inteligente - PVH")

# Sidebar
with st.sidebar:
    st.header("🔑 Conexão")
    input_sessao = st.text_area("Sessão da Extensão:", height=100, value=st.session_state['cookie_session'])
    if st.button("✅ Conectar Sessão", use_container_width=True):
        st.session_state['cookie_session'] = input_sessao.strip()
        st.success("Sessão conectada!")
    
    st.caption("🟢 Conectado" if st.session_state['cookie_session'] else "🔴 Desconectado")

# Interface
lista_brs = st.text_area("Shipment IDs:", height=150, placeholder="BR268346709914A...")
btn_processar = st.button("🔍 Gerar Relatório Completo", use_container_width=True)

# Mapeamento de Status (Aceita string ou int)
STATUS_MAP = {
    "1": "Recebido no Hub",
    1: "Recebido no Hub",
    "2": "Em Processamento",
    2: "Em Processamento",
    "3": "Em Trânsito",
    3: "Em Trânsito",
    "4": "Saiu para Entrega",
    4: "Saiu para Entrega",
}

def formatar_data(timestamp):
    if not timestamp or timestamp <= 0: return "N/A"
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

def extrair_datas_sla(sla_data):
    registros = sla_data.get('sla_record_list', [])
    data_rec = "N/A"
    ultima_at = "N/A"
    
    if registros:
        # Busca Recebimento no Hub PVH
        for reg in registros:
            sub = str(reg.get('sub_type', '')).upper()
            if "LMHUB_RECEIVED" in sub or "RECEIVED" in sub:
                data_rec = formatar_data(reg.get('service_start_time'))
                break
        
        # Busca Última AT Realizada
        for reg in reversed(registros):
            final_time = reg.get('actual_service_end_time') or reg.get('service_start_time')
            if final_time and final_time > 0:
                ultima_at = formatar_data(final_time)
                break
    return data_rec, ultima_at

def extrair_sku(item_data):
    """Tenta localizar o nome do produto no JSON de itens"""
    items = item_data.get('items', [])
    if items:
        return items[0].get('item_name', 'SKU não identificado')
    return "N/A"

if btn_processar:
    sessao = st.session_state['cookie_session']
    if not sessao or not lista_brs:
        st.error("❌ Conecte a sessão e insira os IDs.")
    else:
        try:
            cookies = sessao.replace('\n', '').replace('\r', '').strip()
            csrf = re.search(r'csrftoken=([^;]+)', cookies).group(1) if 'csrftoken' in cookies else 'dummy'
            headers = {'Cookie': cookies, 'X-CSRFToken': csrf, 'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'}

            ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
            resultados = []

            progress_bar = st.progress(0)
            for i, bid in enumerate(ids):
                # Chamadas para as 3 APIs principais
                url_info = f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={bid}"
                url_sla = f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}"
                url_item = f"https://spx.shopee.com.br/api/fleet_order/order/detail/item_info?shipment_id={bid}"
                
                r_info = requests.get(url_info, headers=headers).json().get('data', {})
                r_sla = requests.get(url_sla, headers=headers).json().get('data', {})
                r_item = requests.get(url_item, headers=headers).json().get('data', {})

                rec, at = extrair_datas_sla(r_sla)
                sku = extrair_sku(r_item)
                
                cod_status = r_info.get('basic_info', {}).get('status', 'N/A')
                
                resultados.append({
                    "Shipment ID": bid,
                    "Current Station": r_info.get('basic_info', {}).get('current_station_name', 'N/A'),
                    "Data de Recebimento": rec,
                    "Última AT": at,
                    "Descrição do SKU": sku,
                    "Status": STATUS_MAP.get(cod_status, f"Cód {cod_status}")
                })
                progress_bar.progress((i + 1) / len(ids))

            if resultados:
                df = pd.DataFrame(resultados)
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("📥 Baixar Excel", df.to_csv(index=False).encode('utf-8-sig'), "relatorio.csv", "text/csv")
        
        except Exception as e:
            st.error(f"Erro: {e}")
