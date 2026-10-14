import random
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from statistics import mean, pstdev
from datetime import datetime

BANCO = "tanques.db"
INTERVALO_MS = 2000
JANELA_ANALISE = 20
MIN_HISTORICO = 5
LIMITE_Z = 3.0
LIMITE_NIVEL_CRITICO = 0.20
LIMITE_NIVEL_ALTO = 0.95
LIMITE_QUEDA_VAZAMENTO = 0.05
MEDICOES_VAZAMENTO = 3
LIMITE_CONSUMO_KWH = 3.5


def conectar():
    return sqlite3.connect(BANCO)


def criar_tabela_medicoes():
    with conectar() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS medicoes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tanque_nome TEXT NOT NULL,
                nivel REAL NOT NULL,
                consumo_energia REAL,
                status TEXT,
                data_hora TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("CREATE INDEX IF NOT EXISTS idx_medicoes_tanque_id ON medicoes(tanque_nome, id)")


def salvar_medicao(tanque_nome, nivel, consumo_energia, status):
    with conectar() as con:
        con.execute(
            "INSERT INTO medicoes (tanque_nome, nivel, consumo_energia, status) VALUES (?, ?, ?, ?)",
            (tanque_nome, float(nivel), float(consumo_energia), status),
        )


def buscar_historico(tanque_nome):
    with conectar() as con:
        return con.execute(
            "SELECT id, data_hora, nivel, consumo_energia, status FROM medicoes "
            "WHERE tanque_nome = ? ORDER BY id ASC", (tanque_nome,)
        ).fetchall()


def buscar_ultimas(tanque_nome, limite=JANELA_ANALISE + 1):
    with conectar() as con:
        rows = con.execute(
            "SELECT id, data_hora, nivel, consumo_energia, status FROM medicoes "
            "WHERE tanque_nome = ? ORDER BY id DESC LIMIT ?", (tanque_nome, limite)
        ).fetchall()
    return list(reversed(rows))


def apagar_medicoes(tanque_nome):
    with conectar() as con:
        con.execute("DELETE FROM medicoes WHERE tanque_nome = ?", (tanque_nome,))


class Bomba:
    def __init__(self):
        self.ligada = False

    def ligar(self):
        self.ligada = True
        return round(random.uniform(2.5, 3.5), 2)

    def desligar(self):
        self.ligada = False
        return round(random.uniform(0.0, 0.3), 2)


class Tanque:
    def __init__(self, nome, capacidade):
        self.nome = nome
        self.capacidade = float(capacidade)
        self.nivel_atual = self.capacidade
        self.bomba = Bomba()

    def atualizar_nivel(self):
        # Simula consumo de água sem deixar o nível negativo.
        self.nivel_atual = max(0.0, self.nivel_atual - random.uniform(5, 20))
        if self.nivel_atual <= LIMITE_NIVEL_CRITICO * self.capacidade:
            # Reabastece depois de registrar o nível crítico observado.
            nivel_medido = self.nivel_atual
            consumo = self.bomba.ligar()
            status = "Bomba Ligada"
            salvar_medicao(self.nome, nivel_medido, consumo, status)
            self.nivel_atual = self.capacidade
            return nivel_medido, consumo, status
        consumo = self.bomba.desligar()
        status = "Normal"
        salvar_medicao(self.nome, self.nivel_atual, consumo, status)
        return self.nivel_atual, consumo, status


def z_score(valor, amostra):
    if len(amostra) < 2:
        return 0.0
    desvio = pstdev(amostra)
    if desvio == 0:
        return 0.0
    return (valor - mean(amostra)) / desvio


def avaliar_medicoes(medicoes, capacidade):
    """Retorna (alertas, anomalias, classificação) para as medições mais recentes."""
    if not medicoes:
        return [], [], "Sem medições"

    atual = medicoes[-1]
    nivel = float(atual[2])
    consumo = float(atual[3] or 0.0)
    percentual = nivel / capacidade if capacidade > 0 else 0
    alertas = []
    anomalias = []

    if percentual <= LIMITE_NIVEL_CRITICO:
        alertas.append("Nível de água crítico (≤ 20%)")
    if percentual >= LIMITE_NIVEL_ALTO:
        alertas.append("Nível de água muito alto (≥ 95%)")
    if consumo > LIMITE_CONSUMO_KWH:
        alertas.append(f"Consumo de energia acima do limite ({consumo:.2f} kWh)")

    # Vazamento: três medições recentes com duas quedas consecutivas acima de 5% da capacidade.
    if len(medicoes) >= MEDICOES_VAZAMENTO:
        ultimas = medicoes[-MEDICOES_VAZAMENTO:]
        quedas = [float(ultimas[i - 1][2]) - float(ultimas[i][2]) for i in range(1, len(ultimas))]
        if len(quedas) == 2 and all(q >= LIMITE_QUEDA_VAZAMENTO * capacidade for q in quedas):
            alertas.append("Possível vazamento: queda consecutiva do nível")

    anteriores = medicoes[-(JANELA_ANALISE + 1):-1]
    if len(anteriores) >= MIN_HISTORICO:
        consumos = [float(m[3] or 0.0) for m in anteriores]
        z_consumo = z_score(consumo, consumos)
        if z_consumo >= LIMITE_Z:
            anomalias.append("Consumo muito acima do padrão recente")

        quedas_anteriores = [float(anteriores[i - 1][2]) - float(anteriores[i][2])
                             for i in range(1, len(anteriores))]
        queda_atual = float(anteriores[-1][2]) - nivel
        if len(quedas_anteriores) >= 2 and z_score(queda_atual, quedas_anteriores) >= LIMITE_Z:
            anomalias.append("Queda de nível muito acima do padrão recente")

    classificacao = "Anômala" if anomalias or any("vazamento" in a.lower() for a in alertas) else "Normal"
    return alertas, anomalias, classificacao


class Aplicacao:
    def __init__(self, janela):
        self.janela = janela
        self.janela.title("Sistema de Monitoramento de Tanque")
        self.janela.geometry("1120x740")
        self.tanque = None
        self.monitorando = False
        self.after_id = None
        self.ultima_medicao = None
        self.construir_interface()
        criar_tabela_medicoes()
        self.janela.protocol("WM_DELETE_WINDOW", self.ao_fechar)

    def construir_interface(self):
        topo = ttk.Frame(self.janela, padding=12)
        topo.pack(fill="x")
        ttk.Label(topo, text="Nome do tanque:").grid(row=0, column=0, sticky="w", padx=4, pady=4)
        self.nome_var = tk.StringVar(value="Tanque 1")
        ttk.Entry(topo, textvariable=self.nome_var, width=22).grid(row=0, column=1, padx=4, pady=4)
        ttk.Label(topo, text="Capacidade (L):").grid(row=0, column=2, sticky="w", padx=4, pady=4)
        self.capacidade_var = tk.StringVar(value="500")
        ttk.Entry(topo, textvariable=self.capacidade_var, width=12).grid(row=0, column=3, padx=4, pady=4)
        self.btn_ligar = ttk.Button(topo, text="Ligar monitoramento", command=self.ligar_tanque)
        self.btn_ligar.grid(row=0, column=4, padx=6)
        self.btn_desligar = ttk.Button(topo, text="Desligar tanque", command=self.desligar_tanque, state="disabled")
        self.btn_desligar.grid(row=0, column=5, padx=6)

        status_frame = ttk.LabelFrame(self.janela, text="Monitoramento em tempo real", padding=12)
        status_frame.pack(fill="x", padx=12, pady=5)
        self.lbl_status = ttk.Label(status_frame, text="Tanque desligado", font=("Arial", 12, "bold"))
        self.lbl_status.pack(anchor="w")
        self.lbl_nivel = ttk.Label(status_frame, text="Nível: --")
        self.lbl_nivel.pack(anchor="w", pady=2)
        self.lbl_consumo = ttk.Label(status_frame, text="Consumo: --")
        self.lbl_consumo.pack(anchor="w", pady=2)
        self.lbl_classificacao = ttk.Label(status_frame, text="Classificação: --")
        self.lbl_classificacao.pack(anchor="w", pady=2)

        meio = ttk.Frame(self.janela, padding=(12, 5))
        meio.pack(fill="both", expand=True)
        esquerda = ttk.LabelFrame(meio, text="Alertas e anomalias", padding=8)
        esquerda.pack(side="left", fill="both", expand=True, padx=(0, 6))
        self.lista_alertas = tk.Listbox(esquerda, height=10, activestyle="none")
        self.lista_alertas.pack(fill="both", expand=True)
        direita = ttk.LabelFrame(meio, text="Histórico de medições", padding=8)
        direita.pack(side="left", fill="both", expand=True, padx=(6, 0))
        colunas = ("data", "nivel", "consumo", "status")
        self.tabela = ttk.Treeview(direita, columns=colunas, show="headings", height=10)
        self.tabela.heading("data", text="Data/hora")
        self.tabela.heading("nivel", text="Nível (L)")
        self.tabela.heading("consumo", text="Energia (kWh)")
        self.tabela.heading("status", text="Status")
        self.tabela.column("data", width=145)
        self.tabela.column("nivel", width=75, anchor="e")
        self.tabela.column("consumo", width=95, anchor="e")
        self.tabela.column("status", width=105)
        scroll = ttk.Scrollbar(direita, orient="vertical", command=self.tabela.yview)
        self.tabela.configure(yscrollcommand=scroll.set)
        self.tabela.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        botoes = ttk.Frame(self.janela, padding=12)
        botoes.pack(fill="x")
        ttk.Button(botoes, text="Consultar histórico", command=self.consultar_historico).pack(side="left", padx=4)
        ttk.Button(botoes, text="Ver gráficos", command=self.mostrar_graficos).pack(side="left", padx=4)
        ttk.Button(botoes, text="Limpar histórico", command=self.limpar_historico).pack(side="left", padx=4)
        ttk.Label(botoes, text="O desligamento não apaga as medições.").pack(side="right", padx=4)

    def ligar_tanque(self):
        if self.monitorando:
            return
        nome = self.nome_var.get().strip()
        try:
            capacidade = float(self.capacidade_var.get())
        except ValueError:
            messagebox.showerror("Entrada inválida", "Informe uma capacidade numérica.")
            return
        if not nome:
            messagebox.showerror("Entrada inválida", "Informe o nome do tanque.")
            return
        if capacidade <= 0:
            messagebox.showerror("Entrada inválida", "A capacidade deve ser maior que zero.")
            return
        self.tanque = Tanque(nome, capacidade)
        self.monitorando = True
        self.btn_ligar.configure(state="disabled")
        self.btn_desligar.configure(state="normal")
        self.nome_var.set(nome)
        self.capacidade_var.set(str(capacidade))
        self.lbl_status.configure(text=f"Tanque {nome} ligado")
        self.atualizar_interface()

    def desligar_tanque(self):
        self.monitorando = False
        if self.after_id is not None:
            self.janela.after_cancel(self.after_id)
            self.after_id = None
        if self.tanque:
            self.tanque.bomba.desligar()
        self.btn_ligar.configure(state="normal")
        self.btn_desligar.configure(state="disabled")
        nome = self.tanque.nome if self.tanque else self.nome_var.get().strip()
        self.lbl_status.configure(text=f"Tanque {nome} desligado — histórico preservado")

    def atualizar_interface(self):
        if not self.monitorando or not self.tanque:
            return
        nivel, consumo, status = self.tanque.atualizar_nivel()
        self.ultima_medicao = (nivel, consumo, status)
        percentual = nivel / self.tanque.capacidade * 100
        self.lbl_status.configure(text=f"Tanque {self.tanque.nome} ligado | Bomba: {status}")
        self.lbl_nivel.configure(text=f"Nível: {nivel:.1f} L de {self.tanque.capacidade:.1f} L ({percentual:.1f}%)")
        self.lbl_consumo.configure(text=f"Consumo de energia: {consumo:.2f} kWh")
        medicoes = buscar_ultimas(self.tanque.nome)
        alertas, anomalias, classificacao = avaliar_medicoes(medicoes, self.tanque.capacidade)
        self.lbl_classificacao.configure(text=f"Classificação: {classificacao}")
        self.lista_alertas.delete(0, tk.END)
        mensagens = alertas + anomalias
        if mensagens:
            for mensagem in mensagens:
                self.lista_alertas.insert(tk.END, "⚠ " + mensagem)
        else:
            self.lista_alertas.insert(tk.END, "Nenhum alerta ou anomalia detectado.")
        self.consultar_historico()
        self.after_id = self.janela.after(INTERVALO_MS, self.atualizar_interface)

    def consultar_historico(self):
        nome = self.tanque.nome if self.tanque else self.nome_var.get().strip()
        if not nome:
            return
        for item in self.tabela.get_children():
            self.tabela.delete(item)
        for _, data_hora, nivel, consumo, status in reversed(buscar_ultimas(nome, 100)):
            self.tabela.insert("", tk.END, values=(data_hora, f"{nivel:.2f}", f"{(consumo or 0):.2f}", status or ""))

    def limpar_historico(self):
        if self.monitorando:
            messagebox.showwarning("Monitoramento ativo", "Desligue o tanque antes de limpar o histórico.")
            return
        nome = self.tanque.nome if self.tanque else self.nome_var.get().strip()
        if not nome:
            messagebox.showwarning("Tanque não informado", "Informe o nome do tanque cujo histórico deseja limpar.")
            return
        if messagebox.askyesno("Confirmar exclusão", f"Deseja apagar permanentemente o histórico do tanque '{nome}'?"):
            apagar_medicoes(nome)
            self.consultar_historico()
            messagebox.showinfo("Histórico", "Histórico apagado.")

    def mostrar_graficos(self):
        nome = self.tanque.nome if self.tanque else self.nome_var.get().strip()
        if not nome:
            messagebox.showwarning("Tanque não informado", "Informe o nome do tanque.")
            return
        dados = buscar_historico(nome)
        if len(dados) < 2:
            messagebox.showinfo("Gráficos", "São necessárias pelo menos duas medições para gerar os gráficos.")
            return
        try:
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("Biblioteca ausente", "Instale o matplotlib com: python -m pip install matplotlib")
            return
        datas = [row[1] for row in dados]
        niveis = [row[2] for row in dados]
        consumos = [row[3] or 0 for row in dados]
        fig, eixos = plt.subplots(2, 1, figsize=(10, 7), sharex=True)
        eixos[0].plot(datas, niveis, marker="o", label="Nível (L)")
        eixos[0].set_ylabel("Nível (L)")
        eixos[0].set_title(f"Histórico do tanque: {nome}")
        eixos[0].grid(True)
        eixos[1].plot(datas, consumos, marker="o", label="Consumo (kWh)")
        eixos[1].set_ylabel("Energia (kWh)")
        eixos[1].set_xlabel("Data/hora")
        eixos[1].grid(True)
        for eixo in eixos:
            eixo.tick_params(axis="x", labelrotation=35)
        fig.tight_layout()
        plt.show()

    def ao_fechar(self):
        if self.monitorando:
            self.desligar_tanque()
        self.janela.destroy()


if __name__ == "__main__":
    criar_tabela_medicoes()
    janela = tk.Tk()
    app = Aplicacao(janela)
    janela.mainloop()
