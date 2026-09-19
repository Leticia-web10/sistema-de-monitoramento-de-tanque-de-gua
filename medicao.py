import sqlite3
import random
import time

def criar_tabela_medicoes():
    conexao = sqlite3.connect("tanques.db")
    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS medicoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tanque_nome TEXT NOT NULL,
            nivel REAL NOT NULL,
            consumo_energia REAL,
            status TEXT,
            data_hora TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conexao.commit()
    conexao.close()


def salvar_medicao(tanque_nome, nivel, consumo_energia, status):
    """Salva uma medição completa (nível, consumo, status, data/hora) no banco."""
    conexao = sqlite3.connect("tanques.db")
    cursor = conexao.cursor()
    cursor.execute(
        """INSERT INTO medicoes (tanque_nome, nivel, consumo_energia, status)
           VALUES (?, ?, ?, ?)""",
        (tanque_nome, nivel, consumo_energia, status)
    )
    conexao.commit()
    conexao.close()


class Bomba:
    def __init__(self):
        self.ligada = False

    def ligar(self):
        """Liga a bomba para reabastecer o tanque; consome mais energia."""
        self.ligada = True
        return round(random.uniform(2.5, 3.5), 2)

    def desligar(self):
        """Bomba em repouso; consumo mínimo de energia."""
        self.ligada = False
        return round(random.uniform(0.0, 0.3), 2)


class Tanque:
    def __init__(self, nome, capacidade):
        self.nome = nome
        self.capacidade = capacidade
        self.nivel_atual = capacidade
        self.bomba = Bomba()

    def atualizar_nivel(self):
        """Simula uma nova medição: o nível cai com o consumo de água e,
        se ficar muito baixo, a bomba liga para reabastecer o tanque."""
        self.nivel_atual -= random.randint(5, 20)

        if self.nivel_atual < 0.2 * self.capacidade:
            self.nivel_atual = self.capacidade
            consumo = self.bomba.ligar()
            status = "Bomba Ligada"
        else:
            consumo = self.bomba.desligar()
            status = "Normal"

        salvar_medicao(self.nome, self.nivel_atual, consumo, status)
        return consumo, status

    def exibir(self, consumo, status):
        """Exibe o nível atual do tanque em tempo real."""
        percentual = (self.nivel_atual / self.capacidade) * 100
        print(f"\nTanque: {self.nome}")
        print(f"Nível atual: {self.nivel_atual} L de {self.capacidade} L ({percentual:.1f}%)")
        print(f"Consumo de energia: {consumo} kWh | Status: {status}")


# Programa principal
if __name__ == "__main__":
    criar_tabela_medicoes()

    nome = input("Nome do tanque: ")
    capacidade = float(input("Capacidade (L): "))
    tanque = Tanque(nome, capacidade)

    print("\nTanque pronto para monitoramento em tempo real.")
    print("Simulando novas medições a cada 2 segundos \n")

    try:
        while True:
            consumo, status = tanque.atualizar_nivel()
            tanque.exibir(consumo, status)
            time.sleep(2)
    except KeyboardInterrupt:
        print("\n\nMonitoramento encerrado.")