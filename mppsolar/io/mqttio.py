import logging
import paho.mqtt.publish as publish
import paho.mqtt.subscribe as subscribe
import paho.mqtt.client as mqttc

import time

from .baseio import BaseIO
from ..helpers import get_kwargs

log = logging.getLogger("MPP-Solar")


class MqttIO(BaseIO):
    def __init__(self, *args, **kwargs) -> None:
        # self._serial_port = device_path
        # self._serial_baud = serial_baud
        self.mqtt_broker = get_kwargs(kwargs, "mqtt_broker", "localhost")
        self.mqtt_port = get_kwargs(kwargs, "mqtt_port", 1883)
        self.mqtt_user = get_kwargs(kwargs, "mqtt_user")
        self.mqtt_pass = get_kwargs(kwargs, "mqtt_pass")
        self._name = get_kwargs(kwargs, "name")
        log.info(
            f"MqttIO.__init__ name: {self._name},  mqtt_broker: {self.mqtt_broker}, port: {self.mqtt_port}, user: {self.mqtt_user}, pass: {self.mqtt_pass}"
        )
        self._msg = None

    def sub_cb(self, client, userdata, message):
        log.debug(f"Mqttio sub_cb got msg, topic: {message.topic}, payload: {message.payload}")
        self._msg = message

    def send_and_receive(self, *args, **kwargs) -> dict:
        full_command = get_kwargs(kwargs, "full_command")
        client_id = self._name

        wait_time = 5
        response_line = None
        command_topic = f"{client_id}/command"
        result_topic = f"{client_id}/result"
        # print(self.mqtt_broker)
        # Create mqtt client
        # Client(client_id="", clean_session=True, userdata=None, protocol=MQTTv311, transport="tcp")
        mqtt_client = mqttc.Client()
        # mqtt_client.on_connect = on_connect

        if self.mqtt_user is not None and self.mqtt_pass is not None:
            # auth = {"username": self.mqtt_user, "password": self.mqtt_pass}
            log.info(f"Using mqtt authentication, username: {self.mqtt_user}, password: [supplied]")
            mqtt_client.username_pw_set(self.mqtt_user, password=self.mqtt_pass)
        else:
            log.debug("No mqtt authentication used")
            # auth = None

        # connect(host, port=1883, keepalive=60, bind_address="")
        mqtt_client.connect(self.mqtt_broker, port=self.mqtt_port)

        payload = full_command
        log.debug(f"Publishing {payload} to topic: {command_topic}")

        # publish(topic, payload=None, qos=0, retain=False)
        mqtt_client.publish(command_topic, payload=payload)

        mqtt_client.on_message = self.sub_cb
        mqtt_client.subscribe(result_topic)
        mqtt_client.loop_start()
        time.sleep(wait_time)
        mqtt_client.loop_stop(force=False)

        if self._msg is None:
            # Didnt get a result
            return {
                "ERROR": [
                    f"Mqtt result message not received on topic {result_topic} after {wait_time}sec",
                    "",
                ]
            }
        else:
            msg = self._msg
            self._msg = None
            log.debug(f"mqtt response on {msg.topic} was: {msg.payload}")
            return msg.payload
