class Tanque:
    def __init__(self, nome, capacidade):
        self.nome = nome
        self.capacidade = capacidade
        self.nivel_atual = 0

    def exibir(self):
        print(f"Tanque: {self.nome}")
        print(f"Capacidade: {self.capacidade} L")
        print(f"Nível atual: {self.nivel_atual} L")

nome = input("Nome do tanque: ")
capacidade = float(input("Capacidade (L): "))

tanque = Tanque(nome, capacidade)

print("\nTanque cadastrado com sucesso!")
tanque.exibir()