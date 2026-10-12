import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox
from statistics import mean, pstdev

from medicao import criar_tabela_medicoes, Tanque

# ===============================================================
# CONFIGURAÇÕES
# ===============================================================
BANCO = "tanques.db"
INTERVALO_MS = 2000

# Parâmetros de alertas e anomalias (ajuste conforme a simulação)
LIMITE_NIVEL_CRITICO_PCT = 0.20     # nível <= 20% da capacidade
LIMITE_NIVEL_ALTO_PCT = 0.95        # nível >= 95% da capacidade
LIMITE_QUEDA_VAZAMENTO_PCT = 0.05   # queda >= 5% da capacidade por medição
MEDICOES_VAZAMENTO = 3              # 3 medições seguidas = 2 quedas
LIMITE_CONSUMO_KWH = 3.5            # consumo acima disso é anormal

JANELA_ANALISE = 20                 # quantas medições anteriores comparar
MIN_HISTORICO = 5                   # mínimo de medições para a análise estatística
LIMITE_Z = 3.0                      # desvios padrão para considerar anômalo

# Posições na tupla da medição: (id, data_hora, nivel, consumo_energia, status)
NIVEL = 2
CONSUMO = 3

# Textos
ALERTA_NIVEL_CRITICO = "Nível de água crítico"
ALERTA_NIVEL_ALTO = "Nível de água muito alto"
ALERTA_VAZAMENTO = "Possível vazamento"
ALERTA_CONSUMO = "Consumo de energia acima do limite"
ANOMALIA_CONSUMO = "Consumo muito acima do padrão recente"
ANOMALIA_QUEDA = "Queda de nível muito acima do padrão recente"

NORMAL = "Normal"
ANOMALA = "Anômala"

# ===============================================================
# ESTADO
# ===============================================================
tanque = None
consumo_total = 0.0
ligado = False
job = None  # id do agendamento do after(), para poder cancelar

criar_tabela_medicoes()


# ===============================================================
# BANCO DE DADOS
# ===============================================================
def buscar_ultimas(nome, limite):
    """Últimas 'limite' medições do tanque, em ordem cronológica."""
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


def buscar_historico(nome):
    """Todas as medições do tanque, em ordem cronológica."""
    conexao = sqlite3.connect(BANCO)
    try:
        cursor = conexao.cursor()
        cursor.execute(
            """
            SELECT id, data_hora, nivel, consumo_energia, status
            FROM medicoes
            WHERE tanque_nome = ?
            ORDER BY id
            """,
            (nome,),
        )
        dados = cursor.fetchall()
    finally:
        conexao.close()
    return dados


def apagar_medicoes(nome):
    conexao = sqlite3.connect(BANCO)
    try:
        cursor = conexao.cursor()
        cursor.execute("DELETE FROM medicoes WHERE tanque_nome = ?", (nome,))
        conexao.commit()
    finally:
        conexao.close()


# ===============================================================
# LÓGICA DE ALERTAS E ANOMALIAS
# ===============================================================
def verificar_alertas(medicoes, capacidade):
    """Regras fixas. Retorna lista de textos de alerta."""
    if not medicoes:
        return []

    resultado = []
    nivel = medicoes[-1][NIVEL]
    consumo = medicoes[-1][CONSUMO]

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
        if all(q >= limite_queda for q in quedas):
            resultado.append(ALERTA_VAZAMENTO)

    if consumo > LIMITE_CONSUMO_KWH:
        resultado.append(ALERTA_CONSUMO)

    return resultado


def z_score(valor, amostra, desvio_minimo):
    """Quantos desvios padrão 'valor' está acima da média da amostra."""
    desvio = max(pstdev(amostra), desvio_minimo)
    return (valor - mean(amostra)) / desvio


def analisar_anomalias(medicoes, capacidade):
    """
    Análise estatística: compara a última medição com as anteriores.
    Retorna lista de textos de anomalia (vazia se não houver).
    """
    historico = medicoes[:-1][-JANELA_ANALISE:]
    if len(historico) < MIN_HISTORICO:
        return []

    anomalias = []
    atual = medicoes[-1]

    # Consumo de energia
    consumos = [m[CONSUMO] for m in historico]
    if z_score(atual[CONSUMO], consumos, 0.01) > LIMITE_Z:
        anomalias.append(ANOMALIA_CONSUMO)

    # Queda de nível (positivo = nível diminuiu)
    quedas = [
        historico[i][NIVEL] - historico[i + 1][NIVEL]
        for i in range(len(historico) - 1)
    ]
    queda_atual = medicoes[-2][NIVEL] - atual[NIVEL]
    if len(quedas) >= 2:
        # piso de 0,5% da capacidade evita z enorme se o histórico for muito estável
        if z_score(queda_atual, quedas, 0.005 * capacidade) > LIMITE_Z:
            anomalias.append(ANOMALIA_QUEDA)

    return anomalias


def avaliar(medicoes, capacidade):
    """
    Junta alertas e análise estatística.
    Retorna (classificacao, mensagens), com classificacao NORMAL ou ANOMALA.

    Nível crítico/alto são só alertas (estados esperados do tanque).
    Vazamento, consumo acima do limite e anomalias estatísticas
    tornam a medição ANOMALA.
    """
    resultado_alertas = verificar_alertas(medicoes, capacidade)
    anomalias = analisar_anomalias(medicoes, capacidade)

    alertas_anomalos = {ALERTA_VAZAMENTO, ALERTA_CONSUMO}
    anomala = bool(anomalias) or any(a in alertas_anomalos for a in resultado_alertas)

    mensagens = resultado_alertas + [a for a in anomalias if a not in resultado_alertas]
    return (ANOMALA if anomala else NORMAL), mensagens


# ===============================================================
# ALERTAS NA INTERFACE
# ===============================================================
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


# ===============================================================
# MONITORAMENTO
# ===============================================================
def atualizar_interface():
    global consumo_total, job

    job = None

    # Desligado: não faz nova medição
    if tanque is None or not ligado:
        return

    consumo, status = tanque.atualizar_nivel()
    consumo_total += consumo

    percentual = (tanque.nivel_atual / tanque.capacidade) * 100

    nivel_label.config(text=f"Nível: {tanque.nivel_atual:.1f} L")
    percentual_label.config(text=f"Ocupação: {percentual:.1f}%")
    barra["value"] = percentual
    consumo_label.config(text=f"Consumo atual: {consumo:.2f} kWh")
    total_label.config(text=f"Consumo total: {consumo_total:.2f} kWh")
    status_label.config(text="Status: Tanque ligado")
    bomba_label.config(text=f"Bomba: {status}")

    verificar_anomalias()

    job = janela.after(INTERVALO_MS, atualizar_interface)


def ligar_tanque():
    global tanque, consumo_total, ligado

    # Evita dois loops simultâneos
    if ligado:
        return

    # Cria o tanque apenas se ainda não existe
    if tanque is None:
        nome = nome_entry.get().strip()
        capacidade_texto = capacidade_entry.get().strip().replace(",", ".")

        if nome == "":
            messagebox.showwarning("Atenção", "Digite o nome do tanque.")
            return

        try:
            capacidade = float(capacidade_texto)
            if capacidade <= 0:
                raise ValueError
        except ValueError:
            messagebox.showwarning("Atenção", "Digite uma capacidade válida.")
            return

        tanque = Tanque(nome, capacidade)
        consumo_total = 0.0

    ligado = True
    tanque.bomba.ligada = True

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

    if tanque is None:
        return

    # Impede novas medições e cancela o agendamento pendente
    ligado = False
    if job is not None:
        janela.after_cancel(job)
        job = None

    tanque.bomba.ligada = False

    status_label.config(text="Status: Tanque desligado")
    bomba_label.config(text="Bomba: desligada")
    alerta_label.config(text="Tanque desligado.", fg="black")
    classificacao_label.config(text="Classificação: -", fg="black")

    ligar_button.config(state="normal")
    desligar_button.config(state="disabled")
    novo_button.config(state="normal")

    mensagem.config(text="Tanque desligado. Histórico mantido.", fg="red")


def novo_tanque():
    """Permite monitorar outro tanque sem reiniciar o programa."""
    global tanque, consumo_total

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
    total_label.config(text="Consumo total: -")
    status_label.config(text="Status: -")
    bomba_label.config(text="Bomba: -")
    classificacao_label.config(text="Classificação: -", fg="black")
    alerta_label.config(text="Nenhum alerta.", fg="black")

    novo_button.config(state="disabled")
    mensagem.config(text="Informe os dados do novo tanque.", fg="black")


# ===============================================================
# HISTÓRICO
# ===============================================================
def consultar_historico():
    nome = tanque.nome if tanque is not None else nome_entry.get().strip()

    if nome == "":
        mensagem.config(text="Digite o nome do tanque.", fg="red")
        return

    medicoes = buscar_historico(nome)

    for item in tabela.get_children():
        tabela.delete(item)

    if not medicoes:
        mensagem.config(text=f"Nenhuma medição encontrada para '{nome}'.", fg="red")
        return

    for m in medicoes:
        tabela.insert(
            "",
            "end",
            values=(nome, f"{m[2]:.1f} L", f"{m[3]:.2f} kWh", m[4], m[1]),
        )

    mensagem.config(text=f"{len(medicoes)} medição(ões) encontrada(s).", fg="green")


def limpar_historico():
    nome = tanque.nome if tanque is not None else nome_entry.get().strip()

    if nome == "":
        mensagem.config(text="Digite o nome do tanque.", fg="red")
        return

    if ligado:
        messagebox.showwarning(
            "Atenção", "Desligue o tanque antes de limpar o histórico."
        )
        return

    if not messagebox.askyesno(
        "Confirmar", f"Apagar o histórico do tanque '{nome}'?"
    ):
        return

    apagar_medicoes(nome)

    for item in tabela.get_children():
        tabela.delete(item)

    mensagem.config(text=f"Histórico de '{nome}' apagado.", fg="green")


def ao_fechar():
    if job is not None:
        janela.after_cancel(job)
    janela.destroy()


# ===============================================================
# JANELA
# ===============================================================
janela = tk.Tk()
janela.title("Monitoramento do Tanque")
janela.geometry("1250x690")
janela.protocol("WM_DELETE_WINDOW", ao_fechar)

tk.Label(janela, text="Monitoramento do Tanque", font=("Arial", 18)).pack(pady=5)

corpo = tk.Frame(janela)
corpo.pack(fill="both", expand=True, padx=10, pady=5)

# Monitoramento à esquerda e histórico à direita
frame_monitor = tk.Frame(corpo)
frame_monitor.pack(side="left", fill="y", padx=(0, 15))

frame_historico = tk.Frame(corpo)
frame_historico.pack(side="right", fill="both", expand=True)

# ---------------------------------------------------------------
# Coluna da esquerda: Monitoramento
# ---------------------------------------------------------------
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

barra = ttk.Progressbar(frame_monitor, length=400, mode="determinate", maximum=100)
barra.pack(pady=4)

consumo_label = tk.Label(frame_monitor, text="Consumo atual: -", font=("Arial", 12))
consumo_label.pack(pady=1)

total_label = tk.Label(frame_monitor, text="Consumo total: -", font=("Arial", 12))
total_label.pack(pady=1)

status_label = tk.Label(frame_monitor, text="Status: -", font=("Arial", 12))
status_label.pack(pady=1)

bomba_label = tk.Label(frame_monitor, text="Bomba: -", font=("Arial", 12))
bomba_label.pack(pady=1)

frame_controle = tk.Frame(frame_monitor)
frame_controle.pack(pady=6)

ligar_button = tk.Button(frame_controle, text="Ligar tanque", command=ligar_tanque)
ligar_button.pack(side="left", padx=5)

desligar_button = tk.Button(
    frame_controle, text="Desligar tanque", command=desligar_tanque, state="disabled"
)
desligar_button.pack(side="left", padx=5)

novo_button = tk.Button(
    frame_controle, text="Novo tanque", command=novo_tanque, state="disabled"
)
novo_button.pack(side="left", padx=5)

tk.Label(frame_monitor, text="Alertas e anomalias", font=("Arial", 14)).pack(pady=4)

classificacao_label = tk.Label(
    frame_monitor, text="Classificação: -", font=("Arial", 12, "bold")
)
classificacao_label.pack()

alerta_label = tk.Label(frame_monitor, text="Nenhum alerta.", font=("Arial", 12))
alerta_label.pack(pady=5)

# ---------------------------------------------------------------
# Mensagem (fica embaixo, visível o tempo todo)
# ---------------------------------------------------------------
mensagem = tk.Label(janela, text="", font=("Arial", 11))
mensagem.pack(side="bottom", pady=5, before=corpo)

# ---------------------------------------------------------------
# Coluna da direita: Histórico
# ---------------------------------------------------------------
tk.Label(frame_historico, text="Histórico de Medições", font=("Arial", 14)).pack(pady=(10, 0))

frame_botoes = tk.Frame(frame_historico)
frame_botoes.pack(pady=10)

tk.Button(frame_botoes, text="Consultar histórico", command=consultar_historico).pack(
    side="left", padx=5
)
tk.Button(frame_botoes, text="Limpar", command=limpar_historico).pack(
    side="left", padx=5
)

frame_tabela = tk.Frame(frame_historico)
frame_tabela.pack(padx=20, pady=10, fill="both", expand=True)

colunas = ("tanque", "nivel", "consumo", "status", "data_hora")
cabecalhos = {
    "tanque": ("Tanque", 120),
    "nivel": ("Nível", 100),
    "consumo": ("Consumo", 120),
    "status": ("Status", 150),
    "data_hora": ("Data/Hora", 180),
}

tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=15)
for col, (texto, largura) in cabecalhos.items():
    tabela.heading(col, text=texto)
    tabela.column(col, width=largura)

tabela.pack(side="left", fill="both", expand=True)

scroll = ttk.Scrollbar(frame_tabela, orient="vertical", command=tabela.yview)
scroll.pack(side="right", fill="y")
tabela.configure(yscrollcommand=scroll.set)

janela.mainloop()