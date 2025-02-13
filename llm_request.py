import http.client
import json

# Configure the local LLM endpoint
endpoint = "127.0.0.1:11434"

# Define a prompt
question = f"""Rochas são agregados sólidos e naturais, estudados num ramo da Geologia chamado de
Petrologia. De acordo com a composição, os materiais formadores de rochas são, EXCETO"""
correct_answer = f"""Gases"""
choosen_answer = f"""Matéria orgânica"""


prompt = f"""Vou lhe passar uma questão, junto com a resposta certa dessa questão e a resposta que escolhi.
Caso tenha acertado, explique o porquê de estar certa. Caso tenha errado, explique o raciocínio
correto para chegar na resposta certa. Seja o mais breve possível em sua resposta!
Em hipótese alguma me mencione na resposta!!! Escreva de uma forma impessoal, de forma
alguma devolva respostas como "Vamos começar pela análise da resposta incorreta"!!!
Lembre-se que eu terei acertado apenas se a resposta certa for igual a resoposta escolhida,
caso contrário sempre trate a resposta escolhida como errada!
Questão: {question}
Resposta certa: {correct_answer}
Resposta escolhida: {choosen_answer}"""

# Create a connection to the server
conn = http.client.HTTPConnection(endpoint)

# Define the request body
body = json.dumps({ 
    "model": "deepseek-r1:8b",
    "prompt": prompt,
    "stream": False,
    # "options": {
    #     "temperature": 0.75,
    # }
})  # Deactivate streaming

# Send the POST request to the /api/generate endpoint
headers = {'Content-Type': 'application/json'}

try:
    conn.request("POST", "/api/generate", body=body, headers=headers)
    response = conn.getresponse()  # Get the response
    response_body = response.read().decode("utf-8")  # Decode the response to text

    # Convert the JSON response to a dictionary
    data = json.loads(response_body)

    # Check if there is a "response" key and print only its content
    if "response" in data:
        print(data["response"])
    else:
        print("Error: Unexpected response from LLM", data)

except Exception as e:
    print(f"Erro: {e}")

finally:
    conn.close()
