
import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from statistics import mean, pstdev
from pathlib import Path
import subprocess
import sys

from medicao import criar_tabela_medicoes, Tanque


BANCO = "tanques.db"
INTERVALO_MS = 2000
MAX_LINHAS_HISTORICO = 500

LIMITE_NIVEL_CRITICO_PCT = 0.25
LIMITE_NIVEL_ALTO_PCT = 0.95
LIMITE_QUEDA_VAZAMENTO_PCT = 0.05
MEDICOES_VAZAMENTO = 3
STATUS_BOMBA_LIGADA = "Bomba Ligada"
LIMITE_CONSUMO_BOMBA_KWH = 3.5
LIMITE_CONSUMO_REPOUSO_KWH = 0.3

JANELA_ANALISE = 20
MIN_HISTORICO = 5
LIMITE_Z = 3.0
DESVIO_MINIMO_CONSUMO_KWH = 0.1

# Formato das linhas consultadas: (id, data_hora, nivel, consumo_energia, status)
NIVEL = 2
CONSUMO = 3
STATUS = 4

ALERTA_NIVEL_CRITICO = "Nível de água crítico"
ALERTA_NIVEL_ALTO = "Nível de água muito alto"
ALERTA_VAZAMENTO = "Possível vazamento"
ALERTA_CONSUMO = "Consumo de energia acima do limite"
ANOMALIA_CONSUMO = "Consumo muito acima do padrão recente"
ANOMALIA_QUEDA = "Queda de nível muito acima do padrão recente"
NORMAL = "Normal"
ANOMALA = "Anômala"

# Estado da aplicação
tanque = None
consumo_total = 0.0
ligado = False
job = None
historico_nome = None
processo_graficos = None


criar_tabela_medicoes()


# ----------------------------------------------------------------------
# Banco de dados
# ----------------------------------------------------------------------
def buscar_ultimas(nome, limite):
    """Retorna as últimas medições em ordem cronológica."""
    if not nome:
        return []

    conexao = sqlite3.connect(BANCO)
    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT id, data_hora, nivel, consumo_energia, status
            FROM medicoes
            WHERE tanque_nome = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (nome, limite),
        )
        dados = cursor.fetchall()
    finally:
        conexao.close()
    return dados[::-1]


def contar_medicoes(nome):
    if not nome:
        return 0
    conexao = sqlite3.connect(BANCO)
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM medicoes WHERE tanque_nome = ?", (nome,)
        )
        resultado = cursor.fetchone()
        return resultado[0] if resultado else 0
    finally:
        conexao.close()


def apagar_medicoes(nome):
    conexao = sqlite3.connect(BANCO)
    try:
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM medicoes WHERE tanque_nome = ?", (nome,))
        conexao.commit()
    finally:
        conexao.close()


# ----------------------------------------------------------------------
# Alertas e detecção de anomalias
# ----------------------------------------------------------------------
def verificar_alertas(medicoes, capacidade):
    """Aplica regras fixas e retorna os textos dos alertas encontrados."""
    if not medicoes or capacidade <= 0:
        return []

    resultado = []
    atual = medicoes[-1]
    nivel = atual[NIVEL]
    consumo = atual[CONSUMO] or 0.0
    status = atual[STATUS]

    if nivel <= LIMITE_NIVEL_CRITICO_PCT * capacidade:
        resultado.append(ALERTA_NIVEL_CRITICO)
    if nivel >= LIMITE_NIVEL_ALTO_PCT * capacidade:
        resultado.append(ALERTA_NIVEL_ALTO)

    if len(medicoes) >= MEDICOES_VAZAMENTO:
        ultimas = medicoes[-MEDICOES_VAZAMENTO:]
        limite_queda = LIMITE_QUEDA_VAZAMENTO_PCT * capacidade
        quedas = [
            ultimas[i][NIVEL] - ultimas[i + 1][NIVEL]
            for i in range(len(ultimas) - 1)
        ]
        if all(queda >= limite_queda for queda in quedas):
            resultado.append(ALERTA_VAZAMENTO)

    limite_consumo = (
        LIMITE_CONSUMO_BOMBA_KWH
        if status == STATUS_BOMBA_LIGADA
        else LIMITE_CONSUMO_REPOUSO_KWH
    )
    if consumo > limite_consumo:
        resultado.append(ALERTA_CONSUMO)

    return resultado


def z_score(valor, amostra, desvio_minimo):
    if not amostra:
        return 0.0
    desvio = max(pstdev(amostra), desvio_minimo)
    return (valor - mean(amostra)) / desvio


def analisar_anomalias(medicoes, capacidade):
    """Compara a medição atual com até 20 medições anteriores."""
    if len(medicoes) < 2 or capacidade <= 0:
        return []

    historico = medicoes[:-1][-JANELA_ANALISE:]
    if len(historico) < MIN_HISTORICO:
        return []

    atual = medicoes[-1]
    anomalias = []

    # Compara consumo apenas com medições do mesmo estado da bomba.
    consumos = [
        m[CONSUMO] for m in historico
        if m[STATUS] == atual[STATUS] and m[CONSUMO] is not None
    ]
    if (
        len(consumos) >= MIN_HISTORICO
        and z_score(atual[CONSUMO] or 0.0, consumos, DESVIO_MINIMO_CONSUMO_KWH) > LIMITE_Z
    ):
        anomalias.append(ANOMALIA_CONSUMO)

    # Queda positiva significa redução do nível; subida normalmente indica reabastecimento.
    quedas = [
        historico[i][NIVEL] - historico[i + 1][NIVEL]
        for i in range(len(historico) - 1)
    ]
    quedas = [queda for queda in quedas if queda >= 0]
    queda_atual = medicoes[-2][NIVEL] - atual[NIVEL]

    if len(quedas) >= 2 and z_score(
        queda_atual, quedas, 0.005 * capacidade
    ) > LIMITE_Z:
        anomalias.append(ANOMALIA_QUEDA)

    return anomalias


def avaliar(medicoes, capacidade):
    alertas = verificar_alertas(medicoes, capacidade)
    anomalias = analisar_anomalias(medicoes, capacidade)
    alertas_que_classificam_como_anomalia = {ALERTA_VAZAMENTO, ALERTA_CONSUMO}
    anomala = bool(anomalias) or any(
        alerta in alertas_que_classificam_como_anomalia for alerta in alertas
    )
    mensagens = alertas + [item for item in anomalias if item not in alertas]
    return (ANOMALA if anomala else NORMAL), mensagens


def verificar_anomalias():
    if tanque is None:
        return

    medicoes = buscar_ultimas(tanque.nome, JANELA_ANALISE + 1)
    if not medicoes:
        classificacao_label.config(text="Classificação: -", fg="black")
        alerta_label.config(text="Nenhuma medição disponível.", fg="black")
        return

    classificacao, mensagens = avaliar(medicoes, tanque.capacidade)
    if classificacao == ANOMALA:
        classificacao_label.config(text="Classificação: Anômala", fg="red")
    else:
        classificacao_label.config(text="Classificação: Normal", fg="green")

    if mensagens:
        alerta_label.config(text="ALERTA:\n" + "\n".join(mensagens), fg="red")
    else:
        alerta_label.config(text="Nenhum alerta.", fg="black")


# ----------------------------------------------------------------------
# Monitoramento e controle do tanque
# ----------------------------------------------------------------------
def atualizar_interface():
    global consumo_total, job
    job = None

    if tanque is None or not ligado:
        return

    consumo, status = tanque.atualizar_nivel()
    consumo_total += consumo
    percentual = (tanque.nivel_atual / tanque.capacidade) * 100 if tanque.capacidade else 0

    nivel_label.config(text=f"Nível: {tanque.nivel_atual:.1f} L")
    percentual_label.config(text=f"Ocupação: {percentual:.1f}%")
    barra["value"] = max(0, min(100, percentual))
    consumo_label.config(text=f"Consumo atual: {consumo:.2f} kWh")
    total_label.config(text=f"Consumo total da sessão: {consumo_total:.2f} kWh")
    status_label.config(text="Status: Tanque ligado")
    bomba_label.config(text=f"Bomba: {status}")

    adicionar_ao_historico()
    verificar_anomalias()
    job = janela.after(INTERVALO_MS, atualizar_interface)


def ligar_tanque():
    global tanque, consumo_total, ligado
    if ligado:
        return

    if tanque is None:
        nome = nome_entry.get().strip()
        capacidade_texto = capacidade_entry.get().strip().replace(",", ".")
        if not nome:
            messagebox.showwarning("Atenção", "Digite o nome do tanque.")
            return
        try:
            capacidade = float(capacidade_texto)
            if capacidade <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Atenção", "Digite uma capacidade válida maior que zero.")
            return

        tanque = Tanque(nome, capacidade)
        consumo_total = 0.0

    ligado = True
    consultar_historico()
    nome_entry.config(state="disabled")
    capacidade_entry.config(state="disabled")
    ligar_button.config(state="disabled")
    desligar_button.config(state="normal")
    novo_button.config(state="disabled")
    status_label.config(text="Status: Tanque ligado")
    mensagem.config(text="Tanque ligado.", fg="green")
    atualizar_interface()


def desligar_tanque():
    global ligado, job
    if tanque is None or not ligado:
        return

    ligado = False
    if job is not None:
        try:
            janela.after_cancel(job)
        except tk.TclError:
            pass
        job = None

    tanque.bomba.ligada = False
    status_label.config(text="Status: Tanque desligado")
    bomba_label.config(text="Bomba: desligada")
    alerta_label.config(text="Tanque desligado. Histórico preservado.", fg="black")
    classificacao_label.config(text="Classificação: -", fg="black")
    ligar_button.config(state="normal")
    desligar_button.config(state="disabled")
    novo_button.config(state="normal")
    mensagem.config(text="Tanque desligado. Histórico mantido.", fg="red")


def novo_tanque():
    global tanque, consumo_total, historico_nome
    if ligado:
        return

    tanque = None
    consumo_total = 0.0
    nome_entry.config(state="normal")
    capacidade_entry.config(state="normal")
    nome_entry.delete(0, tk.END)
    capacidade_entry.delete(0, tk.END)
    nivel_label.config(text="Nível: -")
    percentual_label.config(text="Ocupação: -")
    barra["value"] = 0
    consumo_label.config(text="Consumo atual: -")
    total_label.config(text="Consumo total da sessão: -")
    status_label.config(text="Status: -")
    bomba_label.config(text="Bomba: -")
    classificacao_label.config(text="Classificação: -", fg="black")
    alerta_label.config(text="Nenhum alerta.", fg="black")
    novo_button.config(state="disabled")
    for item in tabela.get_children():
        tabela.delete(item)
    historico_nome = None
    mensagem.config(text="Informe os dados do novo tanque.", fg="black")


# ----------------------------------------------------------------------
# Histórico
# ----------------------------------------------------------------------
def nome_atual():
    return tanque.nome if tanque is not None else nome_entry.get().strip()


def consultar_historico():
    global historico_nome
    nome = nome_atual()
    if not nome:
        mensagem.config(text="Digite o nome do tanque.", fg="red")
        return

    medicoes = buscar_ultimas(nome, MAX_LINHAS_HISTORICO)
    for item in tabela.get_children():
        tabela.delete(item)
    historico_nome = nome

    for medicao in medicoes:
        tabela.insert(
            "", "end",
            values=(nome, f"{medicao[2]:.1f} L", f"{(medicao[3] or 0):.2f} kWh", medicao[4], medicao[1]),
        )

    linhas = tabela.get_children()
    if linhas:
        tabela.see(linhas[-1])

    total = contar_medicoes(nome)
    if medicoes:
        mensagem.config(
            text=f"Mostrando as últimas {len(medicoes)} de {total} medição(ões).",
            fg="green",
        )
    else:
        mensagem.config(text=f"Nenhuma medição encontrada para '{nome}'.", fg="red")


def adicionar_ao_historico():
    if tanque is None or historico_nome != tanque.nome:
        return

    ultima = buscar_ultimas(tanque.nome, 1)
    if not ultima:
        return

    medicao = ultima[0]
    no_fim = tabela.yview()[1] >= 0.99
    tabela.insert(
        "", "end",
        values=(tanque.nome, f"{medicao[2]:.1f} L", f"{(medicao[3] or 0):.2f} kWh", medicao[4], medicao[1]),
    )
    linhas = tabela.get_children()
    if len(linhas) > MAX_LINHAS_HISTORICO:
        tabela.delete(linhas[0])
    if no_fim:
        linhas = tabela.get_children()
        if linhas:
            tabela.see(linhas[-1])


def limpar_historico():
    nome = tanque.nome if tanque is not None else nome_entry.get().strip()
    if not nome:
        mensagem.config(text="Digite o nome do tanque.", fg="red")
        return
    if ligado:
        messagebox.showwarning("Atenção", "Desligue o tanque antes de limpar o histórico.")
        return
    if not messagebox.askyesno("Confirmar", f"Apagar o histórico do tanque '{nome}'? Esta ação não pode ser desfeita."):
        return

    apagar_medicoes(nome)
    for item in tabela.get_children():
        tabela.delete(item)
    mensagem.config(text=f"Histórico de '{nome}' apagado.", fg="green")


# ----------------------------------------------------------------------
# Gráficos
# ----------------------------------------------------------------------
def abrir_graficos():
    """Abre o graficos.py existente sem duplicar ou alterar sua implementação."""
    global processo_graficos

    nome = nome_atual()
    if not nome:
        messagebox.showwarning("Atenção", "Digite o nome do tanque.")
        return

    arquivo_graficos = Path(__file__).resolve().with_name("graficos.py")
    if not arquivo_graficos.exists():
        messagebox.showerror(
            "Arquivo não encontrado",
            "Não encontrei graficos.py na mesma pasta deste arquivo."
        )
        return

    # O graficos.py fornecido possui sua própria janela e campo para o nome.
    # Abrimos o arquivo existente em outro processo, sem copiar seu código aqui.
    try:
        processo_graficos = subprocess.Popen(
            [sys.executable, str(arquivo_graficos)],
            cwd=str(arquivo_graficos.parent)
        )
        mensagem.config(
            text="Janela de gráficos aberta. Digite nela o nome do tanque.",
            fg="green"
        )
    except OSError as erro:
        messagebox.showerror(
            "Erro ao abrir gráficos",
            f"Não foi possível abrir graficos.py: {erro}"
        )


# ----------------------------------------------------------------------
# Interface gráfica
# ----------------------------------------------------------------------
janela = tk.Tk()
janela.title("Monitoramento do Tanque")
janela.geometry("1250x720")
janela.protocol("WM_DELETE_WINDOW", janela.destroy)

tk.Label(janela, text="Monitoramento do Tanque", font=("Arial", 18, "bold")).pack(pady=5)
corpo = tk.Frame(janela)
corpo.pack(fill="both", expand=True, padx=10, pady=5)

frame_monitor = tk.Frame(corpo)
frame_monitor.pack(side="left", fill="y", padx=(0, 15))
frame_historico = tk.Frame(corpo)
frame_historico.pack(side="right", fill="both", expand=True)

tk.Label(frame_monitor, text="Nome do tanque:").pack(pady=(10, 0))
nome_entry = tk.Entry(frame_monitor, width=30)
nome_entry.pack(pady=5)
tk.Label(frame_monitor, text="Capacidade (L):").pack()
capacidade_entry = tk.Entry(frame_monitor, width=30)
capacidade_entry.pack(pady=5)

nivel_label = tk.Label(frame_monitor, text="Nível: -", font=("Arial", 12))
nivel_label.pack(pady=1)
percentual_label = tk.Label(frame_monitor, text="Ocupação: -", font=("Arial", 12))
percentual_label.pack(pady=1)
barra = ttk.Progressbar(frame_monitor, length=300, mode="determinate", maximum=100)
barra.pack(pady=4)
consumo_label = tk.Label(frame_monitor, text="Consumo atual: -", font=("Arial", 12))
consumo_label.pack(pady=1)
total_label = tk.Label(frame_monitor, text="Consumo total da sessão: -", font=("Arial", 12))
total_label.pack(pady=1)
status_label = tk.Label(frame_monitor, text="Status: -", font=("Arial", 12))
status_label.pack(pady=1)
bomba_label = tk.Label(frame_monitor, text="Bomba: -", font=("Arial", 12))
bomba_label.pack(pady=1)

frame_controle = tk.Frame(frame_monitor)
frame_controle.pack(pady=6)
ligar_button = tk.Button(frame_controle, text="Ligar tanque", command=ligar_tanque)
ligar_button.pack(side="left", padx=3)
desligar_button = tk.Button(frame_controle, text="Desligar tanque", command=desligar_tanque, state="disabled")
desligar_button.pack(side="left", padx=3)
novo_button = tk.Button(frame_controle, text="Novo tanque", command=novo_tanque, state="disabled")
novo_button.pack(side="left", padx=3)

tk.Label(frame_monitor, text="Alertas e anomalias", font=("Arial", 14, "bold")).pack(pady=4)
classificacao_label = tk.Label(frame_monitor, text="Classificação: -", font=("Arial", 12, "bold"))
classificacao_label.pack()
alerta_label = tk.Label(frame_monitor, text="Nenhum alerta.", font=("Arial", 11), justify="left", wraplength=300)
alerta_label.pack(pady=5)
mensagem = tk.Label(janela, text="", font=("Arial", 11))
mensagem.pack(side="bottom", pady=5, before=corpo)

# Tabela do histórico
tk.Label(frame_historico, text="Histórico de Medições", font=("Arial", 14, "bold")).pack(pady=(10, 0))
frame_botoes = tk.Frame(frame_historico)
frame_botoes.pack(pady=10)
tk.Button(frame_botoes, text="Consultar histórico", command=consultar_historico).pack(side="left", padx=5)
tk.Button(frame_botoes, text="Limpar histórico", command=limpar_historico).pack(side="left", padx=5)
tk.Button(frame_botoes, text="Ver gráficos", command=abrir_graficos).pack(side="left", padx=5)

frame_tabela = tk.Frame(frame_historico)
frame_tabela.pack(padx=10, pady=10, fill="both", expand=True)
colunas = ("tanque", "nivel", "consumo", "status", "data_hora")
cabecalhos = {
    "tanque": ("Tanque", 120),
    "nivel": ("Nível", 90),
    "consumo": ("Consumo", 100),
    "status": ("Status", 130),
    "data_hora": ("Data/Hora", 160),
}
tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=15)
for coluna, (texto, largura) in cabecalhos.items():
    tabela.heading(coluna, text=texto)
    tabela.column(coluna, width=largura, anchor="center")
tabela.pack(side="left", fill="both", expand=True)
scroll = ttk.Scrollbar(frame_tabela, orient="vertical", command=tabela.yview)
scroll.pack(side="right", fill="y")
tabela.configure(yscrollcommand=scroll.set)

if __name__ == "__main__":
    janela.mainloop()

