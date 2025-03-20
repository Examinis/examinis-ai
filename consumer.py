import http.client
import json
import os
import pika
import time
import logging

# Configuração de logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('examinis-ai-consumer')

# Configurações do Ollama
ollama_host = os.environ.get("OLLAMA_HOST", "127.0.0.1")
ollama_port = os.environ.get("OLLAMA_PORT", "11434")
ollama_endpoint = f"{ollama_host}:{ollama_port}"

# Configurações do RabbitMQ
rabbitmq_host = os.environ.get("RABBITMQ_HOST", "rabbitmq")
rabbitmq_user = os.environ.get("RABBITMQ_USER", "guest")
rabbitmq_pass = os.environ.get("RABBITMQ_PASS", "guest")
rabbitmq_port = int(os.environ.get("RABBITMQ_PORT", "5672"))
queue_name = os.environ.get("QUEUE_NAME", "ai.feedback.requests")
response_exchange = os.environ.get("RESPONSE_EXCHANGE", "examinis")

logger.info(f"Conectando ao Ollama em {ollama_endpoint}")
logger.info(f"Conectando ao RabbitMQ em {rabbitmq_host}:{rabbitmq_port}")

def process_ollama_query(question_text, correct_answer, choosen_answer):
    """Processa a consulta no Ollama e retorna a resposta"""
    prompt = f"""Vou lhe passar uma questão que respondi errado, junto com a resposta certa dessa questão e a resposta que escolhi. 
Explique o raciocínio correto para chegar na resposta certa. 
Seja o mais breve possível em sua resposta! 
Em hipótese alguma me mencione na resposta!!! 
Escreva de uma forma impessoal, de forma alguma devolva respostas como "Vamos começar pela análise da resposta incorreta"!!! 
Lembre-se que eu terei acertado apenas se a resposta certa for igual a resposta escolhida, caso contrário sempre trate a resposta escolhida como errada! 
Questão: {question_text} 
Resposta certa: {correct_answer} 
Resposta escolhida: {choosen_answer}"""

    logger.info("Enviando prompt para o modelo")
    
    # Criar conexão com o servidor Ollama
    conn = http.client.HTTPConnection(ollama_endpoint)
    
    # Definir o corpo da requisição
    body = json.dumps({
        "model": "deepseek-r1:1.5b",
        "prompt": prompt,
        "stream": False,
    })
    
    try:
        # Enviar a requisição POST
        headers = {'Content-Type': 'application/json'}
        conn.request("POST", "/api/generate", body=body, headers=headers)
        response = conn.getresponse()
        
        # Obter a resposta
        response_body = response.read().decode("utf-8")
        data = json.loads(response_body)
        
        if "response" in data:
            logger.info(f"Resposta do LLM: {data['response'].split("</think>")[1]}")
            return data["response"]
        else:
            logger.error(f"Erro: Resposta inesperada do LLM: {data}")
            return "Não foi possível gerar um feedback para esta resposta."
    except Exception as e:
        logger.error(f"Erro ao processar consulta Ollama: {str(e)}")
        return f"Erro ao processar a análise: {str(e)}"
    finally:
        conn.close()

def callback(ch, method, properties, body):
    """Função de callback para processar mensagens recebidas"""
    try:
        logger.info(f"Recebida mensagem: {properties.message_id}")
        
        # Decodificar a mensagem
        payload = json.loads(body)
        logger.info(f"Payload recebido: {payload}")
        
        # Extrair dados do payload
        id_exam = payload.get('id_exam')
        id_question = payload.get('id_question')
        question_text = payload.get('question_text')
        choosen_option = payload.get('choosen_option')
        correct_option = payload.get('correct_option')
        user_id = payload.get('user_id')
        
        # Processar a consulta com o modelo Ollama
        feedback = process_ollama_query(question_text, correct_option, choosen_option)
        
        # Preparar resposta
        response_payload = {
            'id_exam': id_exam,
            'id_question': id_question,
            'user_id': user_id,
            'feedback': feedback
        }
        
        # Gerar routing key para a resposta
        routing_key = f"ai.feedback.response.{id_question}"
        
        # Publicar resposta
        ch.basic_publish(
            exchange=response_exchange,
            routing_key=routing_key,
            body=json.dumps(response_payload),
            properties=pika.BasicProperties(
                delivery_mode=2,  # torna a mensagem persistente
                content_type='application/json',
                correlation_id=properties.message_id,
                message_id=f"feedback-{id_exam}-{id_question}-{int(time.time())}"
            )
        )
        
        logger.info(f"Resposta enviada com routing_key={routing_key}")
        
        # Confirmar processamento da mensagem
        ch.basic_ack(delivery_tag=method.delivery_tag)
        
    except Exception as e:
        logger.error(f"Erro ao processar mensagem: {str(e)}")
        # Rejeitar mensagem em caso de erro para posterior reprocessamento
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def main():
    # Estabelecer conexão com RabbitMQ
    credentials = pika.PlainCredentials(rabbitmq_user, rabbitmq_pass)
    parameters = pika.ConnectionParameters(
        host=rabbitmq_host,
        port=rabbitmq_port,
        credentials=credentials,
        heartbeat=600,
        blocked_connection_timeout=300
    )
    
    while True:
        try:
            logger.info("Tentando conectar ao RabbitMQ...")
            connection = pika.BlockingConnection(parameters)
            channel = connection.channel()
            
            # Declarar a fila a ser consumida
            channel.queue_declare(queue=queue_name, durable=True)
            
            # Declarar exchange para respostas
            channel.exchange_declare(exchange=response_exchange, exchange_type='topic', durable=True)
            
            # Configurar o consumo da fila
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=queue_name, on_message_callback=callback)
            
            logger.info(f"Aguardando mensagens na fila {queue_name}...")
            channel.start_consuming()
            
        except pika.exceptions.AMQPConnectionError as error:
            logger.warning(f"Conexão com RabbitMQ falhou: {error}, tentando novamente em 5 segundos...")
            time.sleep(5)
        except KeyboardInterrupt:
            logger.info("Consumidor interrompido manualmente")
            break
        except Exception as e:
            logger.error(f"Erro inesperado: {str(e)}")
            time.sleep(5)

if __name__ == "__main__":
    main()