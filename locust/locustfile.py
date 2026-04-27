from locust import HttpUser, task, between
import random
from datetime import datetime


# Simula la generación de datos aleatorios para el payload
class WarReportUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def send_war_report(self):
        payload = {
            "country": random.choice(["USA", "RUS", "CHN", "ESP", "GTM"]),
            "warplanes_in_air": random.randint(0, 50),
            "warships_in_water": random.randint(0, 30),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        self.client.post("/grpc-201905884", json=payload)