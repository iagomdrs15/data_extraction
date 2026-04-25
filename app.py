import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime
import time

# Configuração da página
st.set_page_config(page_title="Analista SPX - PVH", page_icon="📦", layout="wide")

if 'cookie_session' not in st.session_state:
    st.session_state['cookie_session'] = ""

st.title("📦 Analista Logístico - Painel PVH")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔑 Conexão")
    input_bruto = st.text_area("Cole o Cookie aqui:", height=200, placeholder="SPC_CLIENTID=...")
    
    if st.button("✅ Conectar Sessão", use_container_width=True):
        if input_bruto:
            st.session_state['cookie_session'] = input_bruto.strip()
            st.success("Sessão salva! Pronto para processar.")
        else:
            st.error("Cole o conteúdo primeiro!")

    if st.button("♻️ Limpar Cache"):
        st.session_state.clear()
        st.rerun()

# --- INTERFACE ---
lista_brs = st.text_area("IDs das BRs:", height=150, placeholder="BR266...\nBR262...")
btn_processar = st.button("🔍 Gerar Relatório Operacional", use_container_width=True)

def formatar_data(ts):
    try:
        return datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y %H:%M')
    except:
        return "N/A"

def processar_br(bid, cookie_bruto):
    try:
        # Extração inteligente do CSRF (pega o último token do cookie)
        tokens = re.findall(r'csrftoken=([^; ]+)', cookie_bruto)
        csrf = tokens[-1] if tokens else ""

        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Content-Type': 'application/json',
            'Cookie': cookie_bruto,
            'Host': 'spx.shopee.com.br',
            'Origin': 'https://spx.shopee.com.br',
            'Referer': f'https://spx.shopee.com.br/orderTracking?shipment_id={bid}',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'X-CSRFToken': csrf,
            'X-Requested-With': 'XMLHttpRequest'
        }

        with requests.Session() as s:
            # 1. API de Tracking (Histórico)
            url_track = f"https://spx.shopee.com.br/api/fleet_order/order/detail/get_tracking_list?shipment_id={bid}"
            r_track = s.get(url_track, headers=headers, timeout=15)
            
            if r_track.status_code != 200 or not r_track.text.startswith('{'):
                return {"Shipment ID": bid, "Status Atual": "Sessão Inválida", "Current Station": "N/A"}

            res_track = r_track.json()
            data_track = res_track.get('data', {})
            t_list = data_track.get('tracking_list', [])
            
            status_atual, station, at_code = "N/A", "N/A", "N/A"
            if t_list:
                ultimo = t_list[-1]
                status_atual = ultimo.get('message', "N/A")
                station = ultimo.get('station_name', "N/A")
                
                for e in reversed(t_list):
                    if "Assignment Task [" in e.get('message', ''):
                        match = re.search(r'\[(AT[^\]]+)\]', e['message'])
                        if match: 
                            at_code = match.group(1)
                            break

            # 2. API de SLA (Data no Hub PVH - ID 10951)
            url_sla = f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}"
            r_sla = s.get(url_sla, headers=headers, timeout=15)
            
            data_rec = "N/A"
            if r_sla.status_code == 200 and r_sla.text.startswith('{'):
                sla_info = r_sla.json().get('data', {})
                regs = sla_info.get('sla_record_list', []) or sla_info.get('dynamic_seg_sla_record_list', [])
                for r in regs:
                    # Filtra pelo seu Hub em Porto Velho
                    if r.get('src_station_id') == 10951:
                        data_rec = formatar_data(r.get('service_start_time'))
                        break

            return {
                "Shipment ID": bid,
                "Current Station": station,
                "Data Received no Hub": data_rec,
                "AT": at_code,
                "Status Atual": status_atual
            }
            
    except Exception as e:
        return {"Shipment ID": bid, "Status Atual": f"Erro: {str(e)[:20]}", "Current Station": "N/A"}

# --- EXECUÇÃO ---
if btn_processar:
    cookie = st.session_state.get('cookie_session', "")
    ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
    
    if not cookie:
        st.error("❌ Cole o cookie na lateral primeiro!")
    elif not ids:
        st.warning("⚠️ Insira IDs de BR válidos.")
    else:
        resultados = []
        barra = st.progress(0)
        status_txt = st.empty()
        
        for i, bid in enumerate(ids):
            status_txt.text(f"Consultando {bid}...")
            resultados.append(processar_br(bid, cookie))
            barra.progress((i + 1) / len(ids))
            time.sleep(0.5)
        
        status_txt.empty()
        if resultados:
            df = pd.DataFrame(resultados)
            st.subheader("📊 Relatório Operacional")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Baixar Planilha", csv, "relatorio_pvh.csv", "text/csv")
