import requests

# Configurações do proxy
proxy_host = "127.0.0.1"
proxy_port = 3000
proxy_user = "marcosamuelsson"
proxy_password = "11235813"

# Configuração de proxies no formato SOCKS5
proxies = {
    "http": f"socks5h://{proxy_user}:{proxy_password}@{proxy_host}:{proxy_port}",
    "https": f"socks5h://{proxy_user}:{proxy_password}@{proxy_host}:{proxy_port}",
}

# URL de teste
url = "http://httpbin.org/ip"  # Serviço que retorna o IP que fez a requisição.

try:
    # Faz a requisição via proxy
    response = requests.get(url, proxies=proxies, timeout=10)
    print("Resposta do servidor via proxy:")
    print(response.json())
except requests.RequestException as e:
    print(f"Erro ao conectar via proxy: {e}")
