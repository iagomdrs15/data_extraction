import streamlit as st
import json
import re
import requests
import pandas as pd
from datetime import datetime

# Configuração da página
st.set_page_config(page_title="SPX Hub Porto Velho", page_icon="📦", layout="wide")

# Inicializa a sessão no estado do app para não perder ao clicar em botões
if 'cookie_session' not in st.session_state:
    st.session_state['cookie_session'] = ""

st.title("📦 Analista Logístico Inteligente - PVH")

# Sidebar com botão de confirmação
with st.sidebar:
    st.header("🔑 Conexão de Elite")
    input_sessao = st.text_area("Sessão da Extensão:", height=100, value=st.session_state['cookie_session'])
    if st.button("✅ Conectar Sessão", use_container_width=True):
        st.session_state['cookie_session'] = input_sessao.strip()
        st.success("Sessão conectada com sucesso!")
    
    if st.session_state['cookie_session']:
        st.caption("🟢 Status: Conectado")
    else:
        st.caption("🔴 Status: Aguardando Sessão")

# Interface Principal
st.subheader("🚀 Extração de Dados em Lote")
lista_brs = st.text_area("Insira os Shipment IDs:", height=150, placeholder="BR268346709914A...")
btn_processar = st.button("🔍 Gerar Relatório Operacional", use_container_width=True)

# Mapeamento de Status Técnico da Shopee (Ajustado para o Hub)
# Se o senhor notar que algum nome está errado, me avise o número do código!
STATUS_MAP = {
    1: "Recebido no Hub",
    2: "Em Processamento / Triagem",
    3: "Em Trânsito (Transferência)",
    4: "Saiu para Entrega",
    5: "Entregue com Sucesso",
    10: "Retornado ao Remetente",
}

def formatar_data(timestamp):
    if not timestamp or timestamp == 0: return "N/A"
    return datetime.fromtimestamp(timestamp).strftime('%d/%m/%Y %H:%M')

def extrair_datas_sla(sla_data):
    registros = sla_data.get('sla_record_list', [])
    data_recebimento = "N/A"
    ultima_at = "N/A"
    
    if registros:
        for reg in registros:
            if "LMHub_Received" in reg.get('sub_type', ''):
                data_recebimento = formatar_data(reg.get('service_start_time'))
                break
        ultimo = registros[-1]
        tempo = ultimo.get('actual_service_end_time') or ultimo.get('service_start_time')
        ultima_at = formatar_data(tempo)
            
    return data_recebimento, ultima_at

if btn_processar:
    sessao = st.session_state['cookie_session']
    if not sessao or not lista_brs:
        st.error("❌ Milorde, conecte a sessão na lateral e insira os IDs primeiro.")
    else:
        try:
            cookies = sessao.replace('\n', '').replace('\r', '').strip()
            csrf = re.search(r'csrftoken=([^;]+)', cookies).group(1) if 'csrftoken' in cookies else 'dummy'
            headers = {
                'Cookie': cookies,
                'X-CSRFToken': csrf,
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*'
            }

            ids = re.findall(r'BR[a-zA-Z0-9]+', lista_brs)
            relatorio_final = []

            with st.status("Consultando malha logística...", expanded=True) as status_ui:
                for bid in ids:
                    url_info = f"https://spx.shopee.com.br/api/fleet_order/order/detail/order_info?shipment_id={bid}"
                    url_sla = f"https://spx.shopee.com.br/api/fleet_order/order/detail/sla_info?shipment_id={bid}"
                    
                    res_info = requests.get(url_info, headers=headers)
                    res_sla = requests.get(url_sla, headers=headers)
                    
                    if res_info.status_code == 200:
                        d_info = res_info.json().get('data', {})
                        d_sla = res_sla.json().get('data', {}) if res_sla.status_code == 200 else {}
                        
                        recebimento, ultima_at = extrair_datas_sla(d_sla)
                        
                        # Pegamos o Status Principal e a Retenção separadamente
                        cod_status = d_info.get('basic_info', {}).get('status')
                        motivo_hold = d_info.get('basic_info', {}).get('on_hold_reason', 0)
                        
                        status_texto = STATUS_MAP.get(cod_status, f"Cód {cod_status}")
                        if motivo_hold != 0:
                            status_texto += f" (Retenção {motivo_hold})"

                        relatorio_final.append({
                            "Shipment ID": bid,
                            "Current Station": d_info.get('basic_info', {}).get('current_station_name', 'N/A'),
                            "Data de Recebimento": recebimento,
                            "Última AT": ultima_at,
                            "Descrição do SKU": "Aguardando URL de Itens",
                            "Status": status_texto
                        })
                    else:
                        st.write(f"❌ Erro ao buscar {bid}.")
                
                status_ui.update(label="Relatório Concluído!", state="complete")

            if relatorio_final:
                df = pd.DataFrame(relatorio_final)
                st.subheader("📊 Painel de Controle Operacional")
                st.dataframe(df, use_container_width=True, hide_index=True)
                
                csv = df.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 Baixar Excel", csv, "relatorio_pvh.csv", "text/csv")
                
        except Exception as e:
            st.error(f"Erro no processamento: {e}")
