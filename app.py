import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SPX Hub Porto Velho", page_icon="📦", layout="wide")

# Gerenciamento de Sessão
if 'cookie_session' not in st.session_state:
    st.session_state['cookie_session'] = ""

st.title("📦 Analista Logístico Inteligente - PVH")

# Sidebar
with st.sidebar:
    st.header("🔑 Conexão")
    input_sessao = st.text_area("Cole a Sessão da Extensão:", height=100, value=st.session_state['cookie_session'])
    if st.button("✅ Conectar Sessão", use_container_width=True):
        st.session_state['cookie_session'] = input_sessao.strip()
        st.success("Sessão conectada!")
    
    st.caption("🟢 Conectado" if st.session_state['cookie_session'] else "🔴 Desconectado")

# Interface
lista_brs = st.text_area("Shipment IDs (BRs):", height=150, placeholder="BR268346709914A...")
btn_processar = st.button("🔍 Gerar Relatório Completo", use_container_width=True)

# Mapeamento de Status Reforçado (Trata números e textos)
STATUS_MAP = {
    "1": "Recebido no Hub",
    "2": "Em Processamento",
    "3": "Em Trânsito",
    "4": "Saiu para Entrega",
    "5": "Entregue",
}

def formatar_data(timestamp):
    try:
        if not timestamp or int(timestamp) <= 0: return "N/A"
        return datetime.fromtimestamp(int(timestamp)).strftime('%d/%m/%Y %H:%M')
    except:
        return "N/A"

def extrair_datas_sla(sla_data):
    """Vasculha o JSON por qualquer menção a recebimento ou atividade"""
    registros = sla_data.get('sla_record_list', []) or sla_data.get('dynamic_seg_sla_record_list', [])
    data_rec = "N/A"
    ultima_at = "N/A"
    
    if registros:
        # Busca o primeiro sinal de vida no Hub (Recebido)
        for reg in registros:
            tipo = str(reg.get('sub_type', '')).upper()
            if "RECEIVED" in tipo:
                data_rec = formatar_data(reg.get('service_start_time'))
                break
        
        # Busca o último evento registrado (Última AT)
        for reg in reversed(registros):
            tempo = reg.get('actual_service_end_time') or reg.get('service_start_time')
            if tempo and tempo > 0:
                ultima_at = formatar_data(tempo)
                break
    return data_rec, ultima_at

if btn_processar:
    sessao = st.session_state['cookie_session']
    if not sessao or not lista_brs:
        st.error("❌ Conecte a sessão na lateral e insira os IDs.")
    else:
        try:
            cookies = sessao.replace('\n', '').replace('\r', '').strip()
            csrf = re.search(r'csrftoken=([^;]+)', cookies).group(1) if 'csrftoken' in cookies else 'dummy'
            headers = {'Cookie': cookies, 'X-CSRFToken': csrf, 'User-Agent': 'Mozilla/5.0'}

            ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
            resultados = []
            raw_debug = {} # Para o painel de diagnóstico

            for bid in ids:
                # 3 URLs para buscar tudo
                url_info = f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={bid}"
                url_sla = f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}"
                url_item = f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_items?shipment_id={bid}"
                
                # Coleta
                res_info = requests.get(url_info, headers=headers).json().get('data', {})
                res_sla = requests.get(url_sla, headers=headers).json().get('data', {})
                res_item = requests.get(url_item, headers=headers).json().get('data', {})

                # Salva um exemplo para debug
                raw_debug[bid] = {"info": res_info, "sla": res_sla, "item": res_item}

                # Processamento
                rec, at = extrair_datas_sla(res_sla)
                
                # Tenta pegar SKU de diferentes lugares do JSON
                sku = "N/A"
                if res_item.get('items'):
                    sku = res_item['items'][0].get('item_name', 'N/A')
                elif res_info.get('order_items'):
                    sku = res_info['order_items'][0].get('item_name', 'N/A')

                # Correção do Status
                status_raw = str(res_info.get('basic_info', {}).get('status', 'N/A'))
                status_traduzido = STATUS_MAP.get(status_raw, f"Cód {status_raw}")

                resultados.append({
                    "Shipment ID": bid,
                    "Current Station": res_info.get('basic_info', {}).get('current_station_name', 'N/A'),
                    "Data de Recebimento": rec,
                    "Última AT": at,
                    "Descrição do SKU": sku,
                    "Status": status_traduzido
                })

            if resultados:
                df = pd.DataFrame(resultados)
                st.subheader("📊 Relatório Operacional")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # ÁREA DE DIAGNÓSTICO (Caso continue N/A)
                with st.expander("🛠️ Diagnóstico Técnico (Clique se houver N/A)"):
                    st.write("Se os dados estão N/A, copie o conteúdo abaixo e mande para o suporte:")
                    st.json(raw_debug)
            else:
                st.error("Nenhum dado encontrado.")

        except Exception as e:
            st.error(f"Erro Crítico: {e}")
