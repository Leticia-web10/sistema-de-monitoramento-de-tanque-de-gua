import sqlite3


def criar_tabela_medicoes():
    """Cria a tabela 'medicoes' no banco, caso ainda não exista."""
    conexao = sqlite3.connect("tanques.db")
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanque_nome TEXT NOT NULL,
            nivel REAL NOT NULL,
            data_hora TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conexao.commit()
    conexao.close()


def salvar_medicao(tanque_nome, nivel):
    """Salva uma medição (nível + data/hora automática) no banco."""
    conexao = sqlite3.connect("tanques.db")
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO medicoes (tanque_nome, nivel) VALUES (?, ?)",
        (tanque_nome, nivel)
    )
    conexao.commit()
    conexao.close()


class Tanque:
    def __init__(self, nome, capacidade):
        self.nome = nome
        self.capacidade = capacidade
        self.nivel_atual = 0

    def atualizar_nivel(self, novo_nivel):
        """Atualiza o nível quando há uma nova medição e salva no histórico."""
        self.nivel_atual = novo_nivel
        salvar_medicao(self.nome, novo_nivel)

    def exibir(self):
        """Exibe o nível atual do tanque."""
        percentual = (self.nivel_atual / self.capacidade) * 100
        print(f"\nTanque: {self.nome}")
        print(f"Nível atual: {self.nivel_atual} L de {self.capacidade} L ({percentual:.1f}%)")


# Programa principal
criar_tabela_medicoes()

nome = input("Nome do tanque: ")
capacidade = float(input("Capacidade (L): "))
tanque = Tanque(nome, capacidade)

print("\nTanque pronto para monitoramento.")

# Simulação de visualização em tempo real: a cada nova medição informada,
# o nível é atualizado, salvo no histórico e exibido na tela.
while True:
    entrada = input("\nDigite o novo nível em L (ou 'sair' para encerrar): ")

    if entrada.lower() == "sair":
        break

    novo_nivel = float(entrada)
    tanque.atualizar_nivel(novo_nivel)
    tanque.exibir()