import http.client
import json
import os
import time

# Configure the LLM endpoint using environment variables
ollama_host = os.environ.get("OLLAMA_HOST", "127.0.0.1")
ollama_port = os.environ.get("OLLAMA_PORT", "11434")
endpoint = f"{ollama_host}:{ollama_port}"

print(f"Conectando ao Ollama em {endpoint}")

# Define a prompt
question = f"""Rochas são agregados sólidos e naturais, estudados num ramo da Geologia chamado de Petrologia. De acordo com a composição, os materiais formadores de rochas são, EXCETO"""
correct_answer = f"""Gases"""
choosen_answer = f"""Matéria orgânica"""
prompt = f"""Vou lhe passar uma questão, junto com a resposta certa dessa questão e a resposta que escolhi. Caso tenha acertado, explique o porquê de estar certa. Caso tenha errado, explique o raciocínio correto para chegar na resposta certa. Seja o mais breve possível em sua resposta! Em hipótese alguma me mencione na resposta!!! Escreva de uma forma impessoal, de forma alguma devolva respostas como "Vamos começar pela análise da resposta incorreta"!!! Lembre-se que eu terei acertado apenas se a resposta certa for igual a resoposta escolhida, caso contrário sempre trate a resposta escolhida como errada! Questão: {question} Resposta certa: {correct_answer} Resposta escolhida: {choosen_answer}"""

print("Enviando prompt para o modelo...")

# Create a connection to the server
conn = http.client.HTTPConnection(endpoint)

# Define the request body
body = json.dumps({
    "model": "deepseek-r1:1.5b",
    "prompt": prompt,
    "stream": False,
})

# Send the POST request to the /api/generate endpoint
headers = {'Content-Type': 'application/json'}
try:
    print("Enviando requisição...")
    conn.request("POST", "/api/generate", body=body, headers=headers)
    print("Aguardando resposta...")
    response = conn.getresponse()
    
    # Get the response
    print("Lendo resposta...")
    response_body = response.read().decode("utf-8")
    
    # Convert the JSON response to a dictionary
    print("Processando JSON...")
    data = json.loads(response_body)
    
    # Check if there is a "response" key and print only its content
    if "response" in data:
        print("\n--- RESPOSTA DO MODELO ---")
        print(data["response"])
        print("--- FIM DA RESPOSTA ---\n")
    else:
        print("Erro: Resposta inesperada do LLM", data)
    
    # Aguarda um pouco antes de encerrar para garantir que toda a saída seja exibida
    print("Processamento concluído.")
    time.sleep(1)
except Exception as e:
    print(f"Erro: {e}")
finally:
    conn.close()
    print("Conexão fechada.")

print("Script finalizado com sucesso!")
# Aguardar um momento adicional para garantir que todas as mensagens sejam exibidas
time.sleep(2)