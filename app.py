import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime
import time

# Configuração da página para Porto Velho
st.set_page_config(page_title="Analista SPX - PVH", page_icon="📦", layout="wide")

# Inicialização do estado da sessão
if 'cookie_session' not in st.session_state:
    st.session_state['cookie_session'] = ""

st.title("📦 Analista Logístico - Painel PVH")

# --- SIDEBAR: CONEXÃO ---
with st.sidebar:
    st.header("🔑 Conexão")
    input_bruto = st.text_area("Cole a Sessão aqui:", height=200, placeholder="Cole o Cookie (SPC_...) ou o JSON")
    
    if st.button("✅ Conectar Sessão", use_container_width=True):
        if input_bruto:
            conteudo = input_bruto.strip()
            
            # Lógica de detecção para evitar o erro "Extra data"
            if conteudo.startswith('{'):
                try:
                    dados_json = json.loads(conteudo)
                    st.session_state['cookie_session'] = dados_json.get('cookies', conteudo)
                    st.success("Sessão conectada via JSON!")
                except Exception:
                    st.session_state['cookie_session'] = conteudo
                    st.warning("JSON malformado. Salvo como texto simples.")
            else:
                # Aceita o cookie puro (SPC_CLIENTID...) diretamente
                st.session_state['cookie_session'] = conteudo
                st.success("Cookie salvo com sucesso!")
        else:
            st.error("Cole o conteúdo primeiro!")

    if st.button("♻️ Limpar Cache"):
        st.session_state.clear()
        st.rerun()

# --- INTERFACE PRINCIPAL ---
lista_brs = st.text_area("IDs das BRs:", height=150, placeholder="BR266134291302T\nBR262112125115A")
btn_processar = st.button("🔍 Gerar Relatório Operacional", use_container_width=True)

# --- FUNÇÕES DE APOIO ---
def formatar_data(ts):
    try:
        val = int(ts)
        return datetime.fromtimestamp(val).strftime('%d/%m/%Y %H:%M') if val > 0 else "N/A"
    except: return "N/A"

def processar_br(bid, headers):
    """Extração via API usando os endpoints de Tracking e SLA"""
    try:
        # 1. Busca Histórico e Status Atual
        url_track = f"https://spx.shopee.com.br/api/fleet_order/order/detail/get_tracking_list?shipment_id={bid}"
        res_track = requests.get(url_track, headers=headers, timeout=10)
        
        if res_track.status_code != 200 or not res_track.text.strip().startswith('{'):
            return {"Shipment ID": bid, "Status Atual": "Sessão Expirada", "Current Station": "N/A"}
        
        data_track = res_track.json().get('data', {})
        tracking_list = data_track.get('tracking_list', [])
        
        status_atual, current_station, at_code = "N/A", "N/A", "N/A"

        if tracking_list:
            ultimo = tracking_list[-1]
            status_atual = ultimo.get('message', "N/A")
            current_station = ultimo.get('station_name', "N/A")
            
            # Busca a AT (Assignment Task) no histórico
            for evento in reversed(tracking_list):
                msg = evento.get('message', "")
                if "Assignment Task [" in msg:
                    at_match = re.search(r'\[(AT[^\]]+)\]', msg)
                    if at_match:
                        at_code = at_match.group(1)
                        break

        # 2. Busca Data de Recebimento no Hub PVH (ID 10951)
        url_sla = f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}"
        res_sla = requests.get(url_sla, headers=headers, timeout=10)
        
        data_rec = "N/A"
        if res_sla.status_code == 200 and res_sla.text.strip().startswith('{'):
            sla_data = res_sla.json().get('data', {})
            regs = sla_data.get('sla_record_list', []) or sla_data.get('dynamic_seg_sla_record_list', [])
            for r in regs:
                if r.get('sub_type') == "LMHub_Received-LMHub_Assigned" and r.get('src_station_id') == 10951:
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
        return {"Shipment ID": bid, "Status Atual": f"Erro: {str(e)}", "Current Station": "N/A"}

# --- LÓGICA DE EXECUÇÃO ---
if btn_processar:
    cookie_puro = st.session_state.get('cookie_session', "")
    if not cookie_puro:
        st.error("❌ Conecte a sessão na lateral primeiro!")
    elif not lista_brs:
        st.warning("Insira ao menos um ID de BR.")
    else:
        # Extração automática do CSRF do cookie colado
        csrf_match = re.search(r'csrftoken=([^;]+)', cookie_puro)
        csrf_token = csrf_match.group(1) if csrf_match else "dummy"
        
        headers = {
            'Cookie': cookie_puro,
            'X-CSRFToken': csrf_token,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://spx.shopee.com.br/',
            'Origin': 'https://spx.shopee.com.br',
            'X-Requested-With': 'XMLHttpRequest',
            'Accept': 'application/json, text/plain, */*'
        }

        ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
        resultados = []
        
        if not ids:
            st.error("Nenhum ID válido encontrado.")
        else:
            barra = st.progress(0)
            status_msg = st.empty()

            for i, bid in enumerate(ids):
                status_msg.text(f"Processando {bid} ({i+1}/{len(ids)})...")
                resultados.append(processar_br(bid, headers))
                barra.progress((i + 1) / len(ids))
                time.sleep(0.4) # Delay para evitar bloqueio por bot

            status_msg.empty()

            if resultados:
                df = pd.DataFrame(resultados)
                st.subheader("📊 Relatório Operacional")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Planilha", csv, f"relatorio_pvh_{datetime.now().strftime('%H%M')}.csv", "text/csv")
