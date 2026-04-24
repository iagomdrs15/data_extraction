import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="SPX Hub Porto Velho", page_icon="📦", layout="wide")

# Gerenciamento de Sessão para não perder o login ao trocar de aba
if 'cookie_session' not in st.session_state:
    st.session_state['cookie_session'] = ""

st.title("📦 Analista Logístico - Painel PVH")

# Barra Lateral: Conexão
with st.sidebar:
    st.header("🔑 Conexão")
    input_sessao = st.text_area("Sessão da Extensão:", height=100, value=st.session_state['cookie_session'])
    if st.button("✅ Conectar Sessão", use_container_width=True):
        st.session_state['cookie_session'] = input_sessao.strip()
        st.success("Sessão conectada!")
    st.caption("🟢 Conectado" if st.session_state['cookie_session'] else "🔴 Desconectado")

# Área de Trabalho
lista_brs = st.text_area("Insira os Shipment IDs (BRs):", height=150, placeholder="BR268346709914A...")
btn_processar = st.button("🔍 Gerar Relatório", use_container_width=True)

# Mapeamento de Status Técnico (Ajuste os nomes conforme sua tela oficial)
STATUS_MAP = {
    "1": "Recebido no Hub",
    "2": "Em Processamento",
    "3": "Em Trânsito",
    "4": "Saiu para Entrega",
    "5": "Entregue",
}

def formatar_data(ts):
    try: 
        ts_int = int(ts)
        return datetime.fromtimestamp(ts_int).strftime('%d/%m/%Y %H:%M') if ts_int > 0 else "N/A"
    except: return "N/A"

def extrair_info_logistica(sla_data):
    """Filtra o recebimento no hub e a última atividade real"""
    regs = sla_data.get('sla_record_list', []) or sla_data.get('dynamic_seg_sla_record_list', [])
    data_rec = "N/A"
    ultima_at = "N/A"
    
    if regs:
        # 1. Busca Recebimento no Hub
        for r in regs:
            sub_type = str(r.get('sub_type', '')).upper()
            if "LMHUB_RECEIVED" in sub_type or "RECEIVED" in sub_type:
                data_rec = formatar_data(r.get('service_start_time'))
                break
        
        # 2. Busca o último evento com horário final registrado
        for r in reversed(regs):
            final_time = r.get('actual_service_end_time') or r.get('service_start_time')
            if final_time and int(final_time) > 0:
                ultima_at = formatar_data(final_time)
                break
                
    return data_rec, ultima_at

if btn_processar:
    sessao = st.session_state['cookie_session']
    if not sessao or not lista_brs:
        st.error("❌ Milorde, conecte a sessão e insira os IDs.")
    else:
        try:
            # Preparação do Header
            cookies = sessao.replace('\n', '').replace('\r', '').strip()
            csrf = re.search(r'csrftoken=([^;]+)', cookies).group(1) if 'csrftoken' in cookies else 'dummy'
            headers = {'Cookie': cookies, 'X-CSRFToken': csrf, 'User-Agent': 'Mozilla/5.0'}

            ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
            relatorio = []

            for bid in ids:
                # Consultamos as duas APIs que trazem o que você precisa
                url_info = f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={bid}"
                url_sla = f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}"
                
                res_info = requests.get(url_info, headers=headers).json().get('data', {})
                res_sla = requests.get(url_sla, headers=headers).json().get('data', {})

                rec, at = extrair_info_logistica(res_sla)
                
                # Tratamento do Status
                st_code = str(res_info.get('basic_info', {}).get('status', ''))
                st_text = STATUS_MAP.get(st_code, f"Cód {st_code}")
                
                # Se houver Onhold Reason, anexamos ao status para não haver erro de interpretação
                hold_reason = res_info.get('basic_info', {}).get('on_hold_reason', 0)
                if hold_reason != 0:
                    st_text += f" (Retenção {hold_reason})"

                relatorio.append({
                    "Shipment ID": bid,
                    "Current Station": res_info.get('basic_info', {}).get('current_station_name', 'N/A'),
                    "Data Recebimento no Hub": rec,
                    "Última AT": at,
                    "Status Atual": st_text
                })

            if relatorio:
                df = pd.DataFrame(relatorio)
                st.subheader("📊 Relatório Operacional Consolidado")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Download
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Planilha", csv, "relatorio_spx_pvh.csv", "text/csv")
            else:
                st.error("Nenhum dado retornado. Verifique a sessão.")

        except Exception as e:
            st.error(f"Erro no processamento: {e}")
