import pika


class Consumer:
    """
    This class is responsible for consuming messages from the queue.
    """

    # TODO - Finish the implementation of the consumer class latter

    def __init__(self, queue_name: str, ):
        self.queue_connection = None
        self.queue_name = queue_name
        self.channel = self.queue_connection.channel()
        self.channel.queue_declare(queue=self.queue_name)

    def create_connection(self, host: str = "localhost") -> None:
        """
        Create a connection to the queue server.
        :param host: The host of the queue server.
        """
        self.queue_connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    
    def callback(self, ch, method, properties, body):
        print(f" [x] Received {body}")