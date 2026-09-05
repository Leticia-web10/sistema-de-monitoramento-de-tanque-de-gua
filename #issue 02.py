#issue 02
import matplotlib.pyplot as plt
import numpy as np

class Tanque:
    def __init__(self, nome, capacidade, lista=[1000, 2000, 5000, 10000]):
        self.nome = nome
        self.capacidade = capacidade
        self.nivel_atual = 0
        self.conjunto = lista

    def simular(self):
        tempos = []
        niveis = []

        for i, nivel in enumerate(self.conjunto):
            self.nivel_atual = nivel
            print(f"Medição {i+1}: {self.nivel_atual} litros")

            tempos.append(i + 1)
            niveis.append(self.nivel_atual)

        plt.plot(tempos, niveis, marker='o')
        plt.title("Nível de Água do Tanque")
        plt.xlabel("Medição")
        plt.ylabel("Nível (litros)")
        plt.grid(True)
        plt.show()

    def atualizar_nivel(self, novo_nivel):
        self.nivel_atual = novo_nivel

    def mostrar_nivel(self):
        print(f"Nível atual do tanque: {self.nivel_atual} litros")


# Teste
tanque = Tanque("Caixa d'água", 10000)

tanque.atualizar_nivel(650)
tanque.mostrar_nivel()

tanque.simular()

class Tanque:
    def __init__(self, nome, capacidade):
        self.nome = nome
        self.capacidade = capacidade
        self.nivel_atual = 0

    def atualizar_nivel(self, novo_nivel):
        self.nivel_atual = novo_nivel
        print(f"Nova medição registrada: {self.nivel_atual} litros")

    def mostrar_nivel(self):
        print(f"Nível atual do tanque: {self.nivel_atual} litros")


# Teste
tanque = Tanque("Caixa d'água", 10000)

tanque.mostrar_nivel()

tanque.atualizar_nivel(650)
tanque.mostrar_nivel()

tanque.atualizar_nivel(720)
tanque.mostrar_nivel()

tanque.atualizar_nivel(810)
tanque.mostrar_nivel()

import matplotlib.pyplot as plt

def simular(self, tempo):
    niveis_registrados = []
    i = 0
    while i < tempo and i < len(self.conjunto):
        self.nivel_atual = self.conjunto[i]
        print(self.nivel_atual)
        niveis_registrados.append(self.nivel_atual)
        i += 1

    # Gráfico entra aqui, depois que o loop terminou
    plt.plot(niveis_registrados, marker='o')
    plt.title(f"Nível do tanque: {self.nome}")
    plt.xlabel("Medição")
    plt.ylabel("Nível (L)")
    plt.show()