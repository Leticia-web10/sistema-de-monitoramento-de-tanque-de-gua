import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from medicao import criar_tabela_medicoes, Tanque


tanque = None
consumo_total = 0
ligado = False
# BANCO DE DADOS

criar_tabela_medicoes()


def buscar_medicoes(nome):

    conexao = sqlite3.connect("tanques.db")
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT id, data_hora, nivel, consumo_energia, status
        FROM medicoes
        WHERE tanque_nome = ?
        ORDER BY id
    """, (nome,))

    dados = cursor.fetchall()

    conexao.close()

    return dados
# ALERTAS E ANOMALIA

def verificar_anomalias():

    if tanque is None:
        return

    medicoes = buscar_medicoes(tanque.nome)

    if not medicoes:

        classificacao_label.config(
            text="Classificação: -"
        )

        alerta_label.config(
            text="Nenhuma medição disponível."
        )

        return

    ultima = medicoes[-1]

    nivel = ultima[2]
    consumo = ultima[3]

    alertas = []
    anomalias = []

    # Nível crítico
    if nivel <= 0.20 * tanque.capacidade:

        alertas.append(
            "Nível de água crítico"
        )

        anomalias.append(
            "Nível crítico"
        )

    # Possível vazamento
    if len(medicoes) >= 3:

        nivel1 = medicoes[-1][2]
        nivel2 = medicoes[-2][2]
        nivel3 = medicoes[-3][2]

        queda1 = nivel2 - nivel1
        queda2 = nivel3 - nivel2

        if queda1 >= 15 and queda2 >= 15:

            alertas.append(
                "Possível vazamento"
            )

            anomalias.append(
                "Queda anormal do nível"
            )

    # Consumo anormal
    if consumo > 3.5:

        alertas.append(
            "Consumo de energia anormal"
        )

        anomalias.append(
            "Consumo anormal"
        )

    if anomalias:

        classificacao_label.config(
            text="Classificação: Anômala"
        )

        alerta_label.config(
            text="ALERTA:\n" + "\n".join(alertas)
        )

    else:

        classificacao_label.config(
            text="Classificação: Normal"
        )

        alerta_label.config(
            text="Nenhum alerta."
        )

# ATUALIZAR MONITORAMENTO

def atualizar_interface():

    global consumo_total

    # Se estiver desligado, não faz nova medição
    if tanque is None or not ligado:
        return

    consumo, status = tanque.atualizar_nivel()

    consumo_total += consumo

    percentual = (
        tanque.nivel_atual /
        tanque.capacidade
    ) * 100

    nivel_label.config(
        text=f"Nível: {tanque.nivel_atual:.1f} L"
    )

    percentual_label.config(
        text=f"Ocupação: {percentual:.1f}%"
    )

    barra["value"] = percentual

    consumo_label.config(
        text=f"Consumo atual: {consumo:.2f} kWh"
    )

    total_label.config(
        text=f"Consumo total: {consumo_total:.2f} kWh"
    )

    status_label.config(
        text="Status: Tanque ligado"
    )

    verificar_anomalias()

    janela.after(
        2000,
        atualizar_interface
    )
# LIGAR TANQUE

def ligar_tanque():

    global tanque
    global consumo_total
    global ligado

    nome = nome_entry.get().strip()

    capacidade_texto = capacidade_entry.get().strip()

    if nome == "":

        messagebox.showwarning(
            "Atenção",
            "Digite o nome do tanque."
        )

        return

    try:

        capacidade = float(
            capacidade_texto
        )

        if capacidade <= 0:
            raise ValueError

    except ValueError:

        messagebox.showwarning(
            "Atenção",
            "Digite uma capacidade válida."
        )

        return

    # Cria o tanque somente uma vez
    if tanque is None:

        tanque = Tanque(
            nome,
            capacidade
        )

        consumo_total = 0

    # Liga o tanque
    ligado = True

    tanque.bomba.ligada = True

    nome_entry.config(
        state="disabled"
    )

    capacidade_entry.config(
        state="disabled"
    )

    ligar_button.config(
        state="disabled"
    )

    desligar_button.config(
        state="normal"
    )

    status_label.config(
        text="Status: Tanque ligado"
    )

    mensagem.config(
        text="Tanque ligado.",
        fg="green"
    )

    atualizar_interface()

# DESLIGAR TANQUE

def desligar_tanque():

    global ligado

    if tanque is None:
        return

    # Impede novas medições
    ligado = False

    # Desliga a bomba
    tanque.bomba.ligada = False

    status_label.config(
        text="Status: Tanque desligado"
    )

    alerta_label.config(
        text="Tanque desligado."
    )

    classificacao_label.config(
        text="Classificação: -"
    )

    ligar_button.config(
        state="normal"
    )

    desligar_button.config(
        state="disabled"
    )

    mensagem.config(
        text="Tanque desligado.",
        fg="red"
    )

# CONSULTAR HISTÓRICO

def consultar_historico():

    if tanque is not None:
        nome = tanque.nome
    else:
        nome = nome_entry.get().strip()

    if nome == "":

        mensagem.config(
            text="Digite o nome do tanque.",
            fg="red"
        )

        return

    medicoes = buscar_medicoes(nome)

    for item in tabela.get_children():
        tabela.delete(item)

    if not medicoes:

        mensagem.config(
            text=f"Nenhuma medição encontrada para '{nome}'.",
            fg="red"
        )

        return

    for medicao in medicoes:

        tabela.insert(
            "",
            "end",
            values=(
                nome,
                f"{medicao[2]:.1f} L",
                f"{medicao[3]:.2f} kWh",
                medicao[4],
                medicao[1]
            )
        )

    mensagem.config(
        text=f"{len(medicoes)} medição(ões) encontrada(s).",
        fg="green"
    )
# LIMPAR HISTÓRICO

def limpar_historico():

    resposta = messagebox.askyesno(
        "Confirmar",
        "Deseja limpar o histórico?"
    )

    if not resposta:
        return

    conexao = sqlite3.connect(
        "tanques.db"
    )

    cursor = conexao.cursor()

    cursor.execute(
        "DELETE FROM medicoes"
    )

    conexao.commit()

    conexao.close()

    for item in tabela.get_children():
        tabela.delete(item)

    mensagem.config(
        text="Histórico limpo.",
        fg="green"
    )


# =========================
# JANELA
# =========================

janela = tk.Tk()

janela.title(
    "Monitoramento do Tanque"
)

janela.geometry(
    "950x1100"
)

# =========================
# TÍTULO
# =========================

titulo = tk.Label(
    janela,
    text="Monitoramento do Tanque",
    font=("Arial", 20)
)

titulo.pack(
    pady=15
)

# NOME

tk.Label(
    janela,
    text="Nome do tanque:"
).pack()

nome_entry = tk.Entry(
    janela,
    width=30
)

nome_entry.pack(
    pady=5
)


# =========================
# CAPACIDADE
# =========================

tk.Label(
    janela,
    text="Capacidade (L):"
).pack()

capacidade_entry = tk.Entry(
    janela,
    width=30
)

capacidade_entry.pack(
    pady=5
)
# NÍVEL

nivel_label = tk.Label(
    janela,
    text="Nível: -",
    font=("Arial", 14)
)

nivel_label.pack(
    pady=5
)


percentual_label = tk.Label(
    janela,
    text="Ocupação: -",
    font=("Arial", 14)
)

percentual_label.pack(
    pady=5
)


# =========================
# BARRA
# =========================

barra = ttk.Progressbar(
    janela,
    length=400,
    mode="determinate"
)

barra.pack(
    pady=10
)

# CONSUMO

consumo_label = tk.Label(
    janela,
    text="Consumo atual: -",
    font=("Arial", 14)
)

consumo_label.pack(
    pady=5
)


total_label = tk.Label(
    janela,
    text="Consumo total: -",
    font=("Arial", 14)
)

total_label.pack(
    pady=5
)

# STATUS

status_label = tk.Label(
    janela,
    text="Status: -",
    font=("Arial", 14)
)

status_label.pack(
    pady=5
)

# BOTÕES LIGAR/DESLIGAR

frame_controle = tk.Frame(
    janela
)

frame_controle.pack(
    pady=10
)


ligar_button = tk.Button(
    frame_controle,
    text="Ligar tanque",
    command=ligar_tanque
)

ligar_button.pack(
    side="left",
    padx=5
)


desligar_button = tk.Button(
    frame_controle,
    text="Desligar tanque",
    command=desligar_tanque,
    state="disabled"
)

desligar_button.pack(
    side="left",
    padx=5
)

# ALERTAS

tk.Label(
    janela,
    text="Alertas e anomalias",
    font=("Arial", 16)
).pack(
    pady=10
)


classificacao_label = tk.Label(
    janela,
    text="Classificação: -",
    font=("Arial", 12)
)

classificacao_label.pack()


alerta_label = tk.Label(
    janela,
    text="Nenhum alerta.",
    font=("Arial", 12)
)

alerta_label.pack(
    pady=5
)


# =========================
# MENSAGEM
# =========================

mensagem = tk.Label(
    janela,
    text="",
    font=("Arial", 11)
)

mensagem.pack(
    pady=5
)


# =========================
# HISTÓRICO
# =========================

tk.Label(
    janela,
    text="Histórico de Medições",
    font=("Arial", 16)
).pack(
    pady=10
)


frame_botoes = tk.Frame(
    janela
)

frame_botoes.pack(
    pady=5
)


tk.Button(
    frame_botoes,
    text="Consultar histórico",
    command=consultar_historico
).pack(
    side="left",
    padx=5
)


tk.Button(
    frame_botoes,
    text="Limpar",
    command=limpar_historico
).pack(
    side="left",
    padx=5
)


# =========================
# TABELA
# =========================

frame_tabela = tk.Frame(
    janela
)

frame_tabela.pack(
    padx=20,
    pady=10,
    fill="both",
    expand=True
)


colunas = (
    "tanque",
    "nivel",
    "consumo",
    "status",
    "data_hora"
)


tabela = ttk.Treeview(
    frame_tabela,
    columns=colunas,
    show="headings",
    height=10
)

tabela.heading(
    "tanque",
    text="Tanque"
)

tabela.heading(
    "nivel",
    text="Nível"
)

tabela.heading(
    "consumo",
    text="Consumo"
)

tabela.heading(
    "status",
    text="Status"
)

tabela.heading(
    "data_hora",
    text="Data/Hora"
)


tabela.column(
    "tanque",
    width=120
)

tabela.column(
    "nivel",
    width=100
)

tabela.column(
    "consumo",
    width=120
)

tabela.column(
    "status",
    width=150
)

tabela.column(
    "data_hora",
    width=180
)


tabela.pack(
    side="left",
    fill="both",
    expand=True
)
# ROLAGEM
scroll = ttk.Scrollbar(
    frame_tabela,
    orient="vertical",
    command=tabela.yview
)

scroll.pack(
    side="right",
    fill="y"
)

tabela.configure(
    yscrollcommand=scroll.set
)

# INICIAR

janela.mainloop()