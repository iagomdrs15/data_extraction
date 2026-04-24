import os

# 1. Define o nome da pasta
pasta = "SPX_Extrator_Elite"
os.makedirs(pasta, exist_ok=True)

# 2. O conteúdo do manifest.json (Agora com clipboardWrite e Coringa de domínio)
manifest = """{
  "manifest_version": 3,
  "name": "SPX Extrator Elite",
  "version": "1.1",
  "description": "Captura silenciosa de sessão para o Analista Logístico SPX.",
  "permissions": [
    "cookies",
    "tabs",
    "clipboardWrite"
  ],
  "host_permissions": [
    "*://*.shopee.com.br/*",
    "*://shopee.com.br/*"
  ],
  "action": {
    "default_popup": "popup.html"
  }
}"""

# 3. O conteúdo do popup.html
html = """<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <style>
    body {
      width: 260px;
      padding: 15px;
      font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
      text-align: center;
      background-color: #f8f9fa;
    }
    h3 { margin-top: 0; color: #ee4d2d; }
    button {
      background-color: #ee4d2d; color: white; border: none;
      padding: 10px 15px; font-size: 14px; font-weight: bold;
      border-radius: 5px; cursor: pointer; width: 100%; transition: 0.3s;
    }
    button:hover { background-color: #d73a27; }
    #status { margin-top: 15px; font-size: 13px; font-weight: bold; display: none; word-wrap: break-word;}
  </style>
</head>
<body>
  <h3>📦 Analista SPX</h3>
  <p style="font-size: 12px; color: #555;">Clique abaixo para capturar a sua sessão atualizada.</p>
  <button id="btnExtrair">Extrair Sessão Mágica</button>
  <p id="status">Sessão copiada!</p>
  <script src="popup.js"></script>
</body>
</html>"""

# 4. O conteúdo do popup.js (Agora com detector de erros dedo-duro)
javascript = """document.getElementById('btnExtrair').addEventListener('click', () => {
    const statusText = document.getElementById('status');
    statusText.innerText = "⏳ Extraindo...";
    statusText.style.color = "orange";
    statusText.style.display = "block";

    try {
        const urlSPX = "https://spx.shopee.com.br";
        
        if (!chrome.cookies) {
            throw new Error("Permissão de cookies bloqueada pelo Chrome.");
        }

        chrome.cookies.getAll({ url: urlSPX }, (cookies) => {
            if (chrome.runtime.lastError) {
                statusText.innerText = "❌ Erro do Chrome: " + chrome.runtime.lastError.message;
                statusText.style.color = "red";
                return;
            }
            
            if (!cookies || cookies.length === 0) {
                statusText.innerText = "❌ Nenhum cookie encontrado. Você está logado na SPX?";
                statusText.style.color = "red";
                return;
            }
      
            let cookieString = cookies.map(c => `${c.name}=${c.value}`).join('; ');
      
            navigator.clipboard.writeText(cookieString).then(() => {
                statusText.innerText = "✅ Sessão Copiada! Abrindo o painel...";
                statusText.style.color = "green";
                
                setTimeout(() => {
                    chrome.tabs.create({ url: "https://dataextractionspx.streamlit.app/" });
                }, 1500);
            }).catch(err => {
                statusText.innerText = "❌ Erro ao usar Ctrl+C: " + err.message;
                statusText.style.color = "red";
            });
        });
    } catch (error) {
        statusText.innerText = "❌ Erro Crítico: " + error.message;
        statusText.style.color = "red";
    }
});"""

# 5. Gravando os arquivos
with open(os.path.join(pasta, "manifest.json"), "w", encoding="utf-8") as f:
    f.write(manifest)
with open(os.path.join(pasta, "popup.html"), "w", encoding="utf-8") as f:
    f.write(html)
with open(os.path.join(pasta, "popup.js"), "w", encoding="utf-8") as f:
    f.write(javascript)

print(f"✅ Extensão atualizada para a Versão 1.1!")
