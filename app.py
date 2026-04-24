import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime
import time

st.set_page_config(page_title="Analista SPX - PVH", page_icon="📦", layout="wide")

if 'cookie_session' not in st.session_state:
    st.session_state['cookie_session'] = ""

st.title("📦 Analista Logístico - Painel PVH")

with st.sidebar:
    st.header("🔑 Conexão")
    input_sessao = st.text_area("Cole a Sessão aqui:", height=100, value=st.session_state['cookie_session'])
    if st.button("✅ Conectar Sessão", use_container_width=True):
        st.session_state['cookie_session'] = input_sessao.strip()
        st.success("Sessão salva!")
    
    if st.button("♻️ Limpar Cache"):
        st.session_state.clear()
        st.rerun()

lista_brs = st.text_area("IDs das BRs:", height=150, placeholder="Uma por linha...")
btn_processar = st.button("🔍 Gerar Relatório", use_container_width=True)

STATUS_MAP = {"1": "Recebido no Hub", "2": "Em Processamento", "3": "Em Trânsito", "4": "Saiu para Entrega", "5": "Entregue"}

def extrair_info_logistica(sla_data):
    if not isinstance(sla_data, dict): return "N/A", "N/A"
    regs = sla_data.get('sla_record_list', []) or sla_data.get('dynamic_seg_sla_record_list', [])
    data_rec, ultima_at = "N/A", "N/A"
    if regs:
        for r in regs:
            if "RECEIVED" in str(r.get('sub_type', '')).upper():
                ts = r.get('service_start_time')
                data_rec = datetime.fromtimestamp(int(ts)).strftime('%d/%m/%Y %H:%M') if ts else "N/A"
                break
        ult = regs[-1]
        ts_ult = ult.get('actual_service_end_time') or ult.get('service_start_time')
        ultima_at = datetime.fromtimestamp(int(ts_ult)).strftime('%d/%m/%Y %H:%M') if ts_ult else "N/A"
    return data_rec, ultima_at

if btn_processar:
    if not st.session_state['cookie_session']:
        st.error("❌ Conecte a sessão primeiro!")
    else:
        try:
            cookies = st.session_state['cookie_session'].replace('\n', '').strip()
            csrf = re.search(r'csrftoken=([^;]+)', cookies).group(1) if 'csrftoken' in cookies else "dummy"
            
            # Headers ultra-completos para evitar bloqueio
            headers = {
                'Cookie': cookies,
                'X-CSRFToken': csrf,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Referer': 'https://spx.shopee.com.br/orderTracking',
                'Origin': 'https://spx.shopee.com.br',
                'X-Requested-With': 'XMLHttpRequest'
            }

            ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
            relatorio = []

            for bid in ids:
                url = f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={bid}"
                res = requests.get(url, headers=headers)
                
                # DIAGNÓSTICO EM CASO DE ERRO
                if res.status_code != 200:
                    st.error(f"❌ Erro {res.status_code} na BR {bid}. O servidor da Shopee recusou o acesso.")
                    continue
                
                if not res.text.startswith('{'):
                    st.warning(f"⚠️ A Shopee retornou uma página de login em vez de dados para {bid}. Sessão inválida.")
                    continue

                d_info = res.json().get('data', {})
                # Segunda chamada para as datas
                res_sla = requests.get(f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}", headers=headers).json().get('data', {})
                
                rec, at = extrair_info_logistica(res_sla)
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
                time.sleep(0.5) # Pequena pausa para não ser bloqueado por velocidade

            if relatorio:
                df = pd.DataFrame(relatorio)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("Nenhum dado capturado. Verifique se o cookie na barra lateral está completo.")

        except Exception as e:
            st.error(f"Erro Crítico: {e}")
