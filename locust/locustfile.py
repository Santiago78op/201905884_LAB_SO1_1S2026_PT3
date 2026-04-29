from locust import HttpUser, task, between
import random
from datetime import datetime


# Simula la generación de datos aleatorios para el payload
class WarReportUser(HttpUser):
    wait_time = between(1, 5)

    @task
    def send_war_report(self):
        minValuRange = random.randint(25, 100)
        maxValuRange = random.randint(1000, 3200)
        payload = {
            "country": random.choice(["USA", "RUS", "CHN", "ESP", "GTM"]),
            "warplanes_in_air": random.randint(minValuRange, maxValuRange),
            "warships_in_water": random.randint(minValuRange, maxValuRange),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }

        self.client.post("/grpc-201905884", json=payload)