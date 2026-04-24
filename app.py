import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="SPX Hub Porto Velho", page_icon="📦", layout="wide")

st.title("📦 Analista Logístico Inteligente - PVH")
st.markdown("Extração consolidada: Status + Rastreio de Horários (SLA)")

# Sidebar
with st.sidebar:
    st.header("🔑 Conexão Elite")
    sessao_colada = st.text_area("Sessão da Extensão:", height=100)
    st.info("Utilize a extensão para capturar os cookies antes de processar.")

# Interface Principal
lista_brs = st.text_area("Shipment IDs (um por linha):", height=150, placeholder="BR268346709914A...")
btn = st.button("🚀 Gerar Relatório de Inventário", use_container_width=True)

def formatar_data(timestamp):
    if not timestamp or timestamp == 0: return "N/A"
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

def extrair_datas_sla(sla_data):
    """Garimpa o JSON de SLA para achar o recebimento e a última atividade"""
    registros = sla_data.get('sla_record_list', [])
    data_recebimento = "N/A"
    ultima_at = "N/A"
    
    if registros:
        # 1. Busca o Recebimento no Hub (LMHub_Received)
        for reg in registros:
            if "LMHub_Received" in reg.get('sub_type', ''):
                data_recebimento = formatar_data(reg.get('service_start_time'))
                break
        
        # 2. Busca a Última Atividade (Último registro com tempo final ou inicial)
        ultimo = registros[-1]
        tempo = ultimo.get('actual_service_end_time') or ultimo.get('service_start_time')
        ultima_at = formatar_data(tempo)
            
    return data_recebimento, ultima_at

if btn:
    if not sessao_colada or not lista_brs:
        st.error("❌ Verifique a sessão e a lista de IDs.")
    else:
        try:
            # Configuração de Headers
            cookies = sessao_colada.replace('\n', '').replace('\r', '').strip()
            csrf = re.search(r'csrftoken=([^;]+)', cookies).group(1) if 'csrftoken' in cookies else 'dummy'
            headers = {
                'Cookie': cookies,
                'X-CSRFToken': csrf,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*'
            }

            ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
            relatorio_final = []

            with st.status("Iniciando varredura logística...", expanded=True) as status:
                for bid in ids:
                    st.write(f"🔍 Processando {bid}...")
                    
                    # Chamada 1: Info Geral (Current Station e Status)
                    url_info = f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={bid}"
                    # Chamada 2: Info de Horários (SLA)
                    url_sla = f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}"
                    
                    res_info = requests.get(url_info, headers=headers)
                    res_sla = requests.get(url_sla, headers=headers)
                    
                    if res_info.status_code == 200:
                        d_info = res_info.json().get('data', {})
                        d_sla = res_sla.json().get('data', {}) if res_sla.status_code == 200 else {}
                        
                        # Processamento dos horários
                        recebimento, ultima_at = extrair_datas_sla(d_sla)
                        
                        # Montagem da linha conforme pedido
                        relatorio_final.append({
                            "Shipment ID": bid,
                            "Current Station": d_info.get('basic_info', {}).get('current_station_name', 'N/A'),
                            "Data de Recebimento": recebimento,
                            "Última AT": ultima_at,
                            "Descrição do SKU": "Aguardando URL de Itens", # Próximo passo
                            "Status": "Onhold (Retido)" if d_info.get('basic_info', {}).get('on_hold_reason') != 0 else "Normal"
                        })
                    else:
                        st.write(f"❌ Erro ao buscar {bid}.")
                
                status.update(label="Relatório Concluído!", state="complete")

            if relatorio_final:
                df = pd.DataFrame(relatorio_final)
                st.subheader("📊 Painel de Inventário Porto Velho")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                # Botão de download
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Planilha para o Hub", csv, "inventario_pvh.csv", "text/csv")
                
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
