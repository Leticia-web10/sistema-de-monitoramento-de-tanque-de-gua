import csv
import random
from datetime import datetime, timedelta

nivel = 1000
hora = datetime(2026, 9, 5, 8, 0)

with open("medicoes.csv", "w", newline="") as arquivo:
    escritor = csv.writer(arquivo)

    # Cabeçalho
    escritor.writerow(["data_hora", "nivel_agua", "consumo_energia", "status"])

    for i in range(50):

        # Consumo de água
        nivel -= random.randint(5, 20)

        # Se o tanque estiver muito vazio, liga a bomba
        if nivel < 300:
            nivel = 1000
            consumo = round(random.uniform(2.5, 3.5), 2)
            status = "Bomba Ligada"
        else:
            consumo = round(random.uniform(0.0, 0.3), 2)
            status = "Normal"

        escritor.writerow([
            hora.strftime("%d/%m/%Y %H:%M"),
            nivel,
            consumo,
            status
        ])

        hora += timedelta(minutes=10)

print("Arquivo medicoes.csv criado com sucesso!")