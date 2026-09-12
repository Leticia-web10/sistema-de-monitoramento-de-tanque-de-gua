import sqlite3


def criar_tabela():
    conexao = sqlite3.connect("tanques.db")
    cursor = conexao.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tanques (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            capacidade REAL NOT NULL,
            nivel_atual REAL NOT NULL
        )
    """)
    conexao.commit()
    conexao.close()


def salvar_tanque(tanque):
    conexao = sqlite3.connect("tanques.db")
    cursor = conexao.cursor()
    cursor.execute(
        "INSERT INTO tanques (nome, capacidade, nivel_atual) VALUES (?, ?, ?)",
        (tanque.nome, tanque.capacidade, tanque.nivel_atual)
    )
    conexao.commit()
    conexao.close()


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

criar_tabela()
salvar_tanque(tanque)

print("\nTanque cadastrado com sucesso!")
tanque.exibir()