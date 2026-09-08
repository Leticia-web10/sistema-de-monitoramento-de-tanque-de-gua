class Tanque:
    def __init__(self, nome, capacidade):
        self.nome = nome
        self.capacidade = capacidade
        self.nivel_atual = 0

    def atualizar_nivel(self, nivel):
        self.nivel_atual = nivel

    def exibir(self):
        percentual = (self.nivel_atual / self.capacidade) * 100

        print(f"\nTanque: {self.nome}")
        print(f"Capacidade: {self.capacidade} L")
        print(f"Nível atual: {self.nivel_atual} L")
        print(f"Ocupação: {percentual:.1f}%")

        if self.nivel_atual < 0.2 * self.capacidade:
            print("Alerta: nível baixo!")

        if self.nivel_atual > 0.9 * self.capacidade:
            print("Alerta: tanque quase cheio!")


# Cadastro do tanque
nome = input("Nome do tanque: ")

capacidade_input = input("Capacidade (500L): ")

if capacidade_input.strip() == "":
    capacidade = 500.0
else:
    capacidade = float(capacidade_input)

tanque = Tanque(nome, capacidade)

print("\nTanque foi cadastrado com sucesso!")

# Simulação de atualização em tempo real
while True:
    entrada = input("\nDigite o nível atual (ou 'sair'): ")

    if entrada.lower() == "sair":
        break

    nivel = float(entrada)
    tanque.atualizar_nivel(nivel)
    tanque.exibir()
