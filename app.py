import streamlit as st
import json
import re
import requests

# Configuração da página
st.set_page_config(page_title="Analista Logístico SPX", page_icon="📦", layout="centered")

st.title("📦 Analista Logístico Inteligente")
st.markdown("Bem-vindo! Cole sua sessão capturada pelo **Favorito Mágico** para iniciar a conexão segura.")

# 1. Campos de Entrada
sessao_colada = st.text_input("🔑 Sessão (Ctrl+V):", type="password", help="Cole o código gerado pelo seu Favorito Mágico aqui.")

st.markdown("---")
st.subheader("🛠️ Área de Teste de API")
api_url = st.text_input("🔗 URL da API da SPX para testar:", 
                        placeholder="Ex: https://spx.shopee.com.br/api/v1/logistics/brs...",
                        help="Pegue esta URL na aba Network (Rede) do Inspecionar (F12).")

# 2. Botão de Ação
if st.button("🚀 Conectar e Extrair Dados", use_container_width=True):
    if not sessao_colada:
        st.warning("⚠️ Por favor, cole a sessão mágica primeiro.")
    elif not api_url:
        st.warning("⚠️ Por favor, informe a URL da API que deseja testar.")
    else:
        try:
            # 3. Descriptografando a Sessão
            dados_sessao = json.loads(sessao_colada)
            usuario = dados_sessao.get('usuario', 'Desconhecido')
            cookies_string = dados_sessao.get('cookies', '')
            
            # 4. Garimpando a Trava de Segurança (CSRF Token)
            csrf_match = re.search(r'csrftoken=([^;]+)', cookies_string)
            csrf_token = csrf_match.group(1) if csrf_match else ''
            
            if not csrf_token:
                st.error("❌ Falha de segurança: 'csrftoken' não encontrado na sessão. Refaça o login no sistema.")
            else:
                st.success(f"✅ Autenticado com sucesso! Usuário reconhecido: **{usuario}**")
                
                # 5. Montando o Disfarce (Headers)
                headers = {
                    'Cookie': cookies_string,
                    'X-CSRFToken': csrf_token,
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                    'Accept': 'application/json, text/plain, */*'
                }
                
                # 6. O Ataque Silencioso
                with st.spinner("Conectando aos servidores da SPX..."):
                    resposta = requests.get(api_url, headers=headers)
                    
                    # 7. Análise da Resposta
                    if resposta.status_code == 200:
                        st.success("🎯 Sucesso! Dados interceptados perfeitamente:")
                        # Exibe o JSON cru na tela para você analisar como os dados vêm estruturados
                        st.json(resposta.json())
                    else:
                        st.error(f"❌ Erro na extração. O servidor respondeu com o código: {resposta.status_code}")
                        # Mostra a mensagem de erro que o servidor enviou (ótimo para debug)
                        st.text(resposta.text)
                        
        except json.JSONDecodeError:
            st.error("❌ Formato de sessão inválido. Você copiou o texto inteiro do Favorito Mágico?")
        except Exception as e:
            st.error(f"❌ Ocorreu um erro inesperado: {e}")
