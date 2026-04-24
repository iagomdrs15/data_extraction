import json
import re
import requests

def extrair_dados_spx(sessao_colada, url_da_api):
    # 1. Transforma o texto colado em um dicionário Python
    dados_sessao = json.loads(sessao_colada)
    cookies_string = dados_sessao['cookies']
    usuario = dados_sessao['usuario']
    
    # 2. Garimpa o CSRF Token (Obrigatório para a SPX não bloquear)
    csrf_match = re.search(r'csrftoken=([^;]+)', cookies_string)
    csrf_token = csrf_match.group(1) if csrf_match else ''

    # 3. Monta o disfarce perfeito (Headers)
    headers = {
        'Cookie': cookies_string,
        'X-CSRFToken': csrf_token,
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'application/json, text/plain, */*'
    }

    print(f"Iniciando extração para o usuário: {usuario}...")

    # 4. Faz o ataque silencioso à API
    resposta = requests.get(url_da_api, headers=headers)
    
    if resposta.status_code == 200:
        return resposta.json() # Retorna os dados prontos para análise!
    else:
        return f"Erro na extração: {resposta.status_code}"
