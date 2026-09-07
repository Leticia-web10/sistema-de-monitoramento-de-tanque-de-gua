import csv
import random
from datetime import datetime, timedelta


class Bomba:
    def __init__(self):
        self.ligada = False

    def ligar(self):
        self.ligada = True
        return round(random.uniform(2.5, 3.5), 2)  # consumo quando ligada

    def desligar(self):
        self.ligada = False
        return round(random.uniform(0.0, 0.3), 2)  # consumo em repouso


class Tanque:
    def __init__(self, nome, capacidade):
        self.nome = nome
        self.capacidade = capacidade
        self.nivel_atual = capacidade
        self.bomba = Bomba()

    def atualizar_nivel(self):
        """Simula uma nova medição: consome água e decide se a bomba liga."""
        self.nivel_atual -= random.randint(5, 20)

        if self.nivel_atual < 300:
            self.nivel_atual = self.capacidade
            consumo = self.bomba.ligar()
            status = "Bomba Ligada"
        else:
            consumo = self.bomba.desligar()
            status = "Normal"

        return consumo, status

    def mostrar_nivel(self):
        """Exibe o nível atual do tanque."""
        print(f"Nível atual do tanque: {self.nivel_atual} L")


# Programa principal
tanque = Tanque("Caixa d'água", 1000)
hora = datetime(2026, 9, 5, 8, 0)

with open("medicoes.csv", "w", newline="") as arquivo:
    escritor = csv.writer(arquivo)
    escritor.writerow(["data_hora", "nivel_agua", "consumo_energia", "status"])

    for i in range(50):
        consumo, status = tanque.atualizar_nivel()

        # Exibe em tempo real (critério de aceite da issue #02)
        print(f"[{hora.strftime('%d/%m/%Y %H:%M')}] "
              f"Nível: {tanque.nivel_atual} L | Consumo: {consumo} kWh | Status: {status}")

        escritor.writerow([
            hora.strftime("%d/%m/%Y %H:%M"),
            tanque.nivel_atual,
            consumo,
            status
        ])

        hora += timedelta(minutes=10)

print("\nArquivo medicoes.csv criado com sucesso!")