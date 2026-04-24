import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="SPX Hub Porto Velho", page_icon="📦", layout="wide")

st.title("📦 Analista Logístico Inteligente - PVH")

# Sidebar
with st.sidebar:
    st.header("🔑 Conexão")
    sessao_colada = st.text_area("Cole a Sessão da Extensão:", height=100)
    st.info("Utilize a extensão Elite para capturar os cookies.")

# Campos solicitados
st.subheader("🚀 Extração de Dados Específicos")
lista_brs = st.text_area("Lista de Shipment IDs:", height=150, placeholder="BR268346709914A...")
btn = st.button("🚀 Gerar Relatório Detalhado", use_container_width=True)

# Mapeamento de Status (Ajuste conforme a realidade do seu Hub)
STATUS_MAP = {
    1: "Recebido no Hub",
    2: "Em Processamento",
    3: "Em Trânsito",
    4: "Entregue",
    10: "Retornado",
}

def formatar_data(timestamp):
    if not timestamp or timestamp == 0: return "N/A"
    # Converte timestamp Unix (segundos) para data legível
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

def mapear_dados_especificos(raw_data):
    b = raw_data.get('basic_info', {})
    
    # Nota: SKU e Datas específicas de eventos costumam vir de outras APIs
    # Se o dado não estiver neste JSON, deixamos o campo pronto para receber a nova API
    return {
        "Shipment ID": b.get('shipment_id'),
        "Current Station": b.get('current_station_name'),
        "Status": STATUS_MAP.get(b.get('status'), f"Cód {b.get('status')}"),
        "Data de Recebimento": "Localizar API 'logistics_path'", # Placeholder
        "Última AT": formatar_data(b.get('sla_tag_info', {}).get('update_time')),
        "Descrição do SKU": "Localizar API 'item_info'" # Placeholder
    }

if btn:
    if not sessao_colada or not lista_brs:
        st.error("❌ Verifique a sessão e a lista de BRs.")
    else:
        try:
            cookies = sessao_colada.replace('\n', '').replace('\r', '').strip()
            csrf = re.search(r'csrftoken=([^;]+)', cookies).group(1) if 'csrftoken' in cookies else 'dummy'
            
            headers = {
                'Cookie': cookies,
                'X-CSRFToken': csrf,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*'
            }

            ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
            final_data = []

            with st.spinner("Conectando à malha logística..."):
                for bid in ids:
                    url = f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={bid}"
                    res = requests.get(url, headers=headers)
                    if res.status_code == 200:
                        raw = res.json().get('data', {})
                        if raw:
                            final_data.append(mapear_dados_especificos(raw))
            
            if final_data:
                df = pd.DataFrame(final_data)
                st.subheader("📊 Visão Operacional Detalhada")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Relatório (Excel)", csv, "relatorio_pvh_detalhado.csv", "text/csv")
            else:
                st.error("❌ Nenhum dado retornado. Verifique a sessão.")

        except Exception as e:
            st.error(f"Erro Crítico: {e}")
