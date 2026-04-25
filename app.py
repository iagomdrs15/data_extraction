import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime
import time
import random

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
            # Limpa o cookie de quebras de linha que podem vir da colagem
            st.session_state['cookie_session'] = input_bruto.strip().replace('\n', '').replace('\r', '')
            st.success("Sessão salva!")
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
        # Extração do último CSRF token disponível no cookie
        tokens = re.findall(r'csrftoken=([^; ]+)', cookie_bruto)
        csrf = tokens[-1] if tokens else ""

        # Headers REFORÇADOS (Baseados em uma sessão real do SPX)
        headers = {
            'authority': 'spx.shopee.com.br',
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'cookie': cookie_bruto,
            'referer': f'https://spx.shopee.com.br/orderTracking?shipment_id={bid}',
            'sec-ch-ua': '"Chromium";v="124", "Google Chrome";v="124", "Not-A.Brand";v="99"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'x-csrftoken': csrf,
            'x-requested-with': 'XMLHttpRequest'
        }

        with requests.Session() as s:
            # 1. API de Tracking
            url_track = f"https://spx.shopee.com.br/api/fleet_order/order/detail/get_tracking_list?shipment_id={bid}"
            r_track = s.get(url_track, headers=headers, timeout=15)
            
            # Debug: Se não começar com {, algo deu errado na autenticação
            if not r_track.text.strip().startswith('{'):
                return {"Shipment ID": bid, "Status Atual": "Sessão Inválida (Bloqueio Shopee)", "Current Station": "N/A"}

            res_track = r_track.json()
            if res_track.get('retcode') != 0:
                return {"Shipment ID": bid, "Status Atual": f"Erro: {res_track.get('message', 'Sessão Expirada')}", "Current Station": "N/A"}

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

            # 2. API de SLA (Hub PVH - ID 10951)
            url_sla = f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}"
            r_sla = s.get(url_sla, headers=headers, timeout=15)
            
            data_rec = "N/A"
            if r_sla.status_code == 200 and r_sla.text.startswith('{'):
                sla_info = r_sla.json().get('data', {})
                regs = sla_info.get('sla_record_list', []) or sla_info.get('dynamic_seg_sla_record_list', [])
                for r in regs:
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
        return {"Shipment ID": bid, "Status Atual": f"Erro Conexão", "Current Station": "N/A"}

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
            status_txt.text(f"Consultando {bid} ({i+1}/{len(ids)})...")
            resultados.append(processar_br(bid, cookie))
            barra.progress((i + 1) / len(ids))
            # Delay humano variável
            time.sleep(random.uniform(0.5, 1.0))
        
        status_txt.empty()
        if resultados:
            df = pd.DataFrame(resultados)
            st.subheader("📊 Relatório Operacional")
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            csv = df.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 Baixar Planilha", csv, "relatorio_pvh.csv", "text/csv")
