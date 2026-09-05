import os
class Tanque:
    def __init__(self, nome, capacidade, lista=[1000,2000,5000,10000]):
        self.nome = nome
        self.capacidade = capacidade
        self.nivel_atual = 0
        self.conjunto=lista

    def simular(self, tempo):

        i = 0
        while i< tempo:
            self.nivel_atual = self.conjunto[i]
            print(self.nivel_atual)
           # sleep(1000)
           # chama o matplolib
           #classe da interface
            i+=1

        
    def atualizar_nivel(self, novo_nivel):
        self.nivel_atual = novo_nivel

    def mostrar_nivel(self):
        print(f"Nível atual do tanque: {self.nivel_atual} litros")


#testes
tanque = Tanque("Caixa d'água", 1000)
tanque.atualizar_nivel(650)
tanque.mostrar_nivel()
tanque.simular(5)