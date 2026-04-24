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

st.title("📦 Analista Logístico - Painel PVH")

# Sidebar
with st.sidebar:
    st.header("🔑 Conexão")
    input_sessao = st.text_area("Sessão da Extensão:", height=100, value=st.session_state['cookie_session'])
    if st.button("✅ Conectar Sessão", use_container_width=True):
        st.session_state['cookie_session'] = input_sessao.strip()
        st.success("Sessão conectada!")
    st.caption("🟢 Conectado" if st.session_state['cookie_session'] else "🔴 Desconectado")

# Interface Principal
lista_brs = st.text_area("Insira os Shipment IDs (BRs):", height=150, placeholder="BR268346709914A...")
btn_processar = st.button("🔍 Gerar Relatório Operacional", use_container_width=True)

# Mapeamento de Status
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
    """Extrai recebimento e última atividade do histórico"""
    if not isinstance(sla_data, dict): return "N/A", "N/A"
    
    regs = sla_data.get('sla_record_list', []) or sla_data.get('dynamic_seg_sla_record_list', [])
    data_rec, ultima_at = "N/A", "N/A"
    
    if regs:
        for r in regs:
            sub = str(r.get('sub_type', '')).upper()
            if "RECEIVED" in sub:
                data_rec = formatar_data(r.get('service_start_time'))
                break
        
        for r in reversed(regs):
            final_time = r.get('actual_service_end_time') or r.get('service_start_time')
            if final_time and int(final_time) > 0:
                ultima_at = formatar_data(final_time)
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
            relatorio = []

            for bid in ids:
                # 1. Info Geral
                res_info_raw = requests.get(f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={bid}", headers=headers)
                # 2. Info de Horários (SLA)
                res_sla_raw = requests.get(f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}", headers=headers)

                # Validação se o retorno é JSON ou Login
                if "text/html" in res_info_raw.headers.get('Content-Type', ''):
                    st.warning(f"⚠️ A sessão expirou ou foi bloqueada ao tentar ler {bid}. Por favor, pegue uma nova sessão na extensão.")
                    break

                d_info = res_info_raw.json().get('data', {})
                d_sla = res_sla_raw.json().get('data', {})

                rec, at = extrair_info_logistica(d_sla)
                
                st_code = str(d_info.get('basic_info', {}).get('status', ''))
                st_text = STATUS_MAP.get(st_code, f"Cód {st_code}")
                hold = d_info.get('basic_info', {}).get('on_hold_reason', 0)
                if hold != 0: st_text += f" (Retenção {hold})"

                relatorio.append({
                    "Shipment ID": bid,
                    "Current Station": d_info.get('basic_info', {}).get('current_station_name', 'N/A'),
                    "Data Received no Hub": rec,
                    "AT": at,
                    "Status Atual": st_text
                })

            if relatorio:
                df = pd.DataFrame(relatorio)
                st.subheader("📊 Relatório Operacional PVH")
                st.dataframe(df, use_container_width=True, hide_index=True)
                st.download_button("📥 Baixar Excel", df.to_csv(index=False).encode('utf-8-sig'), "inventario_pvh.csv", "text/csv")
        
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
