from app.services.mqtt_service import MQTTService
from app.models.message import Message
import json

class MessageQueue:
    def __init__(self):
        self.mqtt_service = MQTTService()
        self.mqtt_service.connect()
        self.mqtt_service.start_consuming()

    def enqueue_message(self, message: Message):
        """将消息发布到MQTT队列"""
        message_data = {
            'message_id': message.id,
            'recipient_id': message.recipient_id,
            'recipient_type': message.recipient_type,
            'content': message.content
        }
        return self.mqtt_service.publish_message(message_data)

    def set_message_handler(self, handler):
        """设置消息处理函数"""
        self.mqtt_service.set_message_callback(handler)
