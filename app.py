import json
import re

def extrair_ultima_at(tracking_list):
    """
    Varre o histórico de rastreamento do mais recente para o antigo
    para encontrar a última Assignment Task (AT) registrada.
    """
    for evento in reversed(tracking_list):
        message = evento.get('message', '')
        # Busca o padrão [AT...] dentro da mensagem
        match = re.search(r'\[(AT\w+)\]', message)
        if match:
            return match.group(1)
    return "N/A"

def parse_shopee_api(json_bruto):
    """
    Faz o parse do JSON bruto tratando erros de formatação
    e extraindo os KPIs logísticos principais.
    """
    try:
        # Resolve o erro 'Extra data': limpa espaços e caracteres antes/depois do JSON
        json_limpo = json_bruto.strip()
        
        # Converte a string para dicionário Python
        data_full = json.loads(json_limpo)
        
        # Navega até a base dos dados
        payload = data_full.get('data', {})
        tracking_list = payload.get('tracking_list', [])
        
        # Extração de informações principais
        shipment_id = payload.get('shipment_id', 'Desconhecido')
        ultima_at = extrair_ultima_at(tracking_list)
        
        # Pega o evento mais recente do topo da lista
        evento_atual = tracking_list[-1] if tracking_list else {}
        status_log = evento_atual.get('message', 'Sem status')
        operador = evento_atual.get('operator', 'Sistema')
        
        # Formata o relatório para o seu Dashboard ou Banco de Dados
        relatorio = {
            "ID_Pacote": shipment_id,
            "Ultima_AT": ultima_at,
            "Status_Atual": status_log,
            "Operador": operador,
            "Timestamp": evento_atual.get('timestamp')
        }
        
        return relatorio

    except json.JSONDecodeError as e:
        return f"Erro de Formato: Certifique-se de copiar o JSON completo (Response). Detalhe: {e}"
    except Exception as e:
        return f"Erro Inesperado: {e}"

# --- ÁREA DE EXECUÇÃO ---

# Exemplo de como você passaria o conteúdo que copiou do Network/Response
json_input = """ 
COLE_AQUI_O_CONTEUDO_DO_RESPONSE
"""

# Se o campo não estiver vazio, processa
if "retcode" in json_input:
    info = parse_shopee_api(json_input)
    
    if isinstance(info, dict):
        print("="*50)
        print(f"RELATÓRIO LOGÍSTICO - HUB PORTO VELHO")
        print("="*50)
        print(f"Pacote: {info['ID_Pacote']}")
        print(f"Última AT: {info['Ultima_AT']}")
        print(f"Status: {info['Status_Atual']}")
        print(f"Operador: {info['Operador']}")
        print("="*50)
        
        # Aqui você poderia inserir no seu SQLite:
        # cursor.execute("INSERT INTO logistica ... VALUES ...")
    else:
        print(info)
else:
    print("Aguardando entrada de dados válida...")
