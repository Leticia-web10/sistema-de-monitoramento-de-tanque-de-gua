import sqlite3

class Tanque:
    def __init__(self, nome, capacidade):
        self.nome = nome
        self.capacidade = capacidade

    def salvar(self):
        conexao = sqlite3.connect("tanques.db")
        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO tanques (nome, capacidade)
            VALUES (?, ?)
        """, (self.nome, self.capacidade))

        conexao.commit()
        conexao.close()

        print("Tanque cadastrado com sucesso!")
#teste
nome = input("Nome do tanque: ")
capacidade = float(input("Capacidade (L): "))

tanque = Tanque(nome, capacidade)
tanque.salvar()
