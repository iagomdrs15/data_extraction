import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime
import time

# Configuração da página para Porto Velho
st.set_page_config(page_title="Analista SPX - PVH", page_icon="📦", layout="wide")

if 'cookie_session' not in st.session_state:
    st.session_state['cookie_session'] = ""

st.title("📦 Analista Logístico - Painel PVH")

# --- SIDEBAR: CONEXÃO ---
with st.sidebar:
    st.header("🔑 Conexão")
    input_bruto = st.text_area("Cole a Sessão aqui:", height=200, placeholder="SPC_CLIENTID=...")
    
    if st.button("✅ Conectar Sessão", use_container_width=True):
        if input_bruto:
            conteudo = input_bruto.strip()
            # Blindagem contra erro de JSON - Se não começar com '{', é cookie puro
            if not conteudo.startswith('{'):
                st.session_state['cookie_session'] = conteudo
                st.success("Cookie salvo!")
            else:
                try:
                    dados_json = json.loads(conteudo)
                    st.session_state['cookie_session'] = dados_json.get('cookies', conteudo)
                    st.success("Sessão extraída do JSON!")
                except:
                    st.session_state['cookie_session'] = conteudo
                    st.success("Salvo como texto.")
        else:
            st.error("Cole o conteúdo primeiro!")

    if st.button("♻️ Limpar Cache"):
        st.session_state.clear()
        st.rerun()

# --- INTERFACE PRINCIPAL ---
lista_brs = st.text_area("IDs das BRs:", height=150, placeholder="Insira as BRs aqui...")
btn_processar = st.button("🔍 Gerar Relatório Operacional", use_container_width=True)

def formatar_data(ts):
    try:
        val = int(ts)
        return datetime.fromtimestamp(val).strftime('%d/%m/%Y %H:%M') if val > 0 else "N/A"
    except: return "N/A"

def processar_br(bid, headers):
    try:
        # 1. Busca Tracking List
        url_track = f"https://spx.shopee.com.br/api/fleet_order/order/detail/get_tracking_list?shipment_id={bid}"
        res_track = requests.get(url_track, headers=headers, timeout=15)
        
        # Se não retornar um JSON válido, a sessão caiu
        if res_track.status_code != 200 or not res_track.text.strip().startswith('{'):
            return {"Shipment ID": bid, "Status Atual": "Sessão Expirada", "Current Station": "N/A"}
        
        res_json = res_track.json()
        if res_json.get('retcode') != 0:
            return {"Shipment ID": bid, "Status Atual": f"Shopee: {res_json.get('message')}", "Current Station": "N/A"}

        data_track = res_json.get('data', {})
        tracking_list = data_track.get('tracking_list', [])
        
        status_atual, current_station, at_code = "N/A", "N/A", "N/A"

        if tracking_list:
            ultimo = tracking_list[-1]
            status_atual = ultimo.get('message', "N/A")
            current_station = ultimo.get('station_name', "N/A")
            
            for evento in reversed(tracking_list):
                msg = evento.get('message', "")
                if "Assignment Task [" in msg:
                    at_match = re.search(r'\[(AT[^\]]+)\]', msg)
                    if at_match:
                        at_code = at_match.group(1)
                        break

        # 2. Busca SLA (Recebimento no Hub PVH - 10951)
        url_sla = f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}"
        res_sla = requests.get(url_sla, headers=headers, timeout=15)
        
        data_rec = "N/A"
        if res_sla.status_code == 200 and res_sla.text.strip().startswith('{'):
            sla_data = res_sla.json().get('data', {})
            regs = sla_data.get('sla_record_list', []) or sla_data.get('dynamic_seg_sla_record_list', [])
            for r in regs:
                if r.get('src_station_id') == 10951:
                    data_rec = formatar_data(r.get('service_start_time'))
                    break
        
        return {
            "Shipment ID": bid,
            "Current Station": current_station,
            "Data Received no Hub": data_rec,
            "AT": at_code,
            "Status Atual": status_atual
        }
    except Exception as e:
        return {"Shipment ID": bid, "Status Atual": f"Erro Conexão", "Current Station": "N/A"}

if btn_processar:
    cookie_puro = st.session_state.get('cookie_session', "")
    if not cookie_puro:
        st.error("❌ Conecte a sessão primeiro!")
    else:
        # Ajuste Crítico de CSRF: A Shopee às vezes exige o token sem aspas ou espaços
        csrf_tokens = re.findall(r'csrftoken=([^;]+)', cookie_puro)
        csrf_token = csrf_tokens[-1].strip() if csrf_tokens else ""
        
        headers = {
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Cookie': cookie_puro,
            'Host': 'spx.shopee.com.br',
            'Referer': 'https://spx.shopee.com.br/orderTracking',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
            'X-CSRFToken': csrf_token,
            'X-Requested-With': 'XMLHttpRequest'
        }

        ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
        if not ids:
            st.warning("Insira IDs válidos.")
        else:
            resultados = []
            barra = st.progress(0)
            status_text = st.empty()
            
            for i, bid in enumerate(ids):
                status_text.text(f"Consultando {bid}...")
                resultados.append(processar_br(bid, headers))
                barra.progress((i + 1) / len(ids))
                time.sleep(0.6) # Delay para evitar detecção de robô
            
            status_text.empty()
            if resultados:
                df = pd.DataFrame(resultados)
                st.subheader("📊 Relatório Operacional")
                st.dataframe(df, use_container_width=True, hide_index=True)
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Planilha", csv, "relatorio_pvh.csv", "text/csv")
