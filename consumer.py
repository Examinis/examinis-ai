import pika
import os
import time
import json
import http.client
from pika.exceptions import AMQPConnectionError

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "examinis-rabbitmq")
QUEUE_NAME = "ai.feedback.requests"
OLLAMA_SERVERS = os.getenv("OLLAMA_SERVERS", "localhost:11434").split(",")
MAX_RETRIES = 10
RETRY_DELAY = 5  # seconds

def process_question(data):
    """Send the question to an Ollama server and return the response."""
    # Choose a server (for simplicity, using the first one)
    server = OLLAMA_SERVERS[0]
    
    # Configure the request
    question = data.get("question", "")
    correct_answer = data.get("correct_answer", "")
    chosen_answer = data.get("chosen_answer", "")
    
    prompt = f"""Vou lhe passar uma questão, junto com a resposta certa dessa questão e a resposta que escolhi.
Caso tenha acertado, explique o porquê de estar certa. Caso tenha errado, explique o raciocínio
correto para chegar na resposta certa. Seja o mais breve possível em sua resposta!
Em hipótese alguma me mencione na resposta!!! Escreva de uma forma impessoal, de forma
alguma devolva respostas como "Vamos começar pela análise da resposta incorreta"!!!
Lembre-se que eu terei acertado apenas se a resposta certa for igual a resoposta escolhida,
caso contrário sempre trate a resposta escolhida como errada!
Questão: {question}
Resposta certa: {correct_answer}
Resposta escolhida: {chosen_answer}"""

    # Create a connection to the server
    hostname, port = server.split(":")
    conn = http.client.HTTPConnection(hostname, int(port))

    # Define the request body
    body = json.dumps({ 
        "model": "deepseek-r1:1.5b",
        "prompt": prompt,
        "stream": False
    })

    # Send the request
    headers = {'Content-Type': 'application/json'}

    try:
        conn.request("POST", "/api/generate", body=body, headers=headers)
        response = conn.getresponse()
        response_body = response.read().decode("utf-8")
        
        # Parse the response
        data = json.loads(response_body)
        
        if "response" in data:
            return data["response"]
        else:
            return f"Error: Unexpected response from LLM: {data}"
            
    except Exception as e:
        return f"Error processing request: {str(e)}"
    finally:
        conn.close()

def callback(ch, method, properties, body):
    """Função que processa mensagens da fila."""
    try:
        print(f"[x] Mensagem recebida: {body.decode()}", flush=True)
        data = json.loads(body.decode())
        
        # Process the message
        response = process_question(data)
        print(f"[x] Resposta gerada: {response[:100]}...", flush=True)
        
        # Acknowledge the message
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
        # Here you would typically send the response back to another queue
        # or store it somewhere for the client to retrieve
        
    except json.JSONDecodeError:
        print(f"[!] Erro: mensagem não é um JSON válido: {body.decode()}", flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
    except Exception as e:
        print(f"[!] Erro no processamento: {str(e)}", flush=True)
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def connect_to_rabbitmq():
    """Establish connection to RabbitMQ with retries."""
    for attempt in range(MAX_RETRIES):
        try:
            print(f"Tentando conectar ao RabbitMQ em {RABBITMQ_HOST} (tentativa {attempt+1})", flush=True)
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(host=RABBITMQ_HOST)
            )
            channel = connection.channel()
            
            # Declare the queue to ensure it exists
            channel.queue_declare(queue=QUEUE_NAME, durable=True)
            
            # Configure to only get one message at a time
            channel.basic_qos(prefetch_count=1)
            
            # Set up the consumer
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)
            
            return connection, channel
        except AMQPConnectionError as e:
            print(f"Falha ao conectar: {str(e)}", flush=True)
            if attempt < MAX_RETRIES - 1:
                print(f"Aguardando {RETRY_DELAY} segundos antes de tentar novamente...", flush=True)
                time.sleep(RETRY_DELAY)
            else:
                print("Número máximo de tentativas excedido. Desistindo.", flush=True)
                raise

if __name__ == "__main__":
    print("Aguardando RabbitMQ...", flush=True)
    print(f"RabbitMQ Host: {RABBITMQ_HOST}", flush=True)
    print(f"Ollama Servers: {OLLAMA_SERVERS}", flush=True)
    
    try:
        # Connect to RabbitMQ
        connection, channel = connect_to_rabbitmq()
        
        print(f"Conexão estabelecida com RabbitMQ em {RABBITMQ_HOST}", flush=True)
        print(f"Aguardando mensagens na fila {QUEUE_NAME}. Para sair, pressione CTRL+C", flush=True)
        
        # Start consuming messages
        channel.start_consuming()
        
    except KeyboardInterrupt:
        print("Consumidor interrompido pelo usuário", flush=True)
        if 'connection' in locals() and connection.is_open:
            connection.close()
    except Exception as e:
        print(f"Erro crítico: {str(e)}", flush=True)