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
    "580": "BackLog (Aguardando)",
}

def formatar_data(ts):
    try: 
        ts_int = int(ts)
        return datetime.fromtimestamp(ts_int).strftime('%d/%m/%Y %H:%M') if ts_int > 0 else "N/A"
    except: return "N/A"

def extrair_at_e_operador(tracking_data):
    """Extrai o ID da AT e o último operador do histórico real de rastreio"""
    ultima_at = "N/A"
    ultimo_op = "N/A"
    
    if not tracking_data or 'tracking_list' not in tracking_data:
        return ultima_at, ultimo_op
    
    logs = tracking_data.get('tracking_list', [])
    
    # Varre do fim para o início para pegar as infos mais recentes
    for evento in reversed(logs):
        msg = evento.get('message', '')
        
        # 1. Busca ID da AT (padrão [AT...])
        if ultima_at == "N/A":
            match = re.search(r'\[(AT\w+)\]', msg)
            if match:
                ultima_at = match.group(1)
        
        # 2. Busca último operador humano/sistema
        if ultimo_op == "N/A":
            ultimo_op = evento.get('operator', 'N/A')
            
        if ultima_at != "N/A" and ultimo_op != "N/A":
            break
            
    return ultima_at, ultimo_op

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
                # 1. Info Geral (Basic e Order Info)
                res_info_raw = requests.get(f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={bid}", headers=headers)
                # 2. Info de Rastreio Completo (Para pegar a AT e o Operador)
                res_track_raw = requests.get(f"https://spx.shopee.com.br/api/fleet_order/order/detail/tracking_info?shipment_id={bid}", headers=headers)
                # 3. Info de Horários (SLA) para pegar a data de recebimento
                res_sla_raw = requests.get(f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}", headers=headers)

                if "text/html" in res_info_raw.headers.get('Content-Type', ''):
                    st.warning(f"⚠️ Sessão expirada em {bid}.")
                    break

                d_info = res_info_raw.json().get('data', {})
                d_track = res_track_raw.json().get('data', {})
                d_sla = res_sla_raw.json().get('data', {})

                # Extração via lógica integrada
                at_id, operador = extrair_at_e_operador(d_track)
                
                # Pega recebimento do SLA
                data_rec = "N/A"
                sla_regs = d_sla.get('sla_record_list', []) or []
                for r in sla_regs:
                    if "RECEIVED" in str(r.get('sub_type', '')).upper():
                        data_rec = formatar_data(r.get('service_start_time'))
                        break

                # Status formatado
                st_code = str(d_info.get('basic_info', {}).get('status', ''))
                st_text = STATUS_MAP.get(st_code, f"Cód {st_code}")
                hold = d_info.get('basic_info', {}).get('on_hold_reason', 0)
                if hold != 0: st_text += f" (Retenção {hold})"

                relatorio.append({
                    "Shipment ID": bid,
                    "Current Station": d_info.get('basic_info', {}).get('current_station_name', 'N/A'),
                    "Recebido no Hub": data_rec,
                    "Última AT": at_id,
                    "Último Operador": operador,
                    "Status Atual": st_text
                })

            if relatorio:
                df = pd.DataFrame(relatorio)
                st.subheader("📊 Relatório Operacional PVH")
                
                # Estilização básica para destacar retenções
                def highlight_status(val):
                    color = 'red' if 'Retenção' in str(val) else 'white'
                    return f'color: {color}'

                st.dataframe(df.style.map(highlight_status, subset=['Status Atual']), use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Relatório (CSV)", csv, f"relatorio_pvh_{datetime.now().strftime('%d_%m')}.csv", "text/csv")
        
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
