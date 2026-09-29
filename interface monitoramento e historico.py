import tkinter as tk
import sqlite3
from tkinter import ttk
from medicao import criar_tabela_medicoes, Tanque

# BANCO DE DADOS

criar_tabela_medicoes()

# VARIÁVEIS DO MONITORAMENTO
tanque = None
consumo_total = 0

# CONSULTAR HISTÓRICO
def consultar_historico():
    nome_tanque = nome_entry.get().strip()

    # Limpa a tabela antes da nova consulta
    for item in tabela.get_children():
        tabela.delete(item)

    if nome_tanque == "":
        mensagem.config(text="Digite o nome do tanque.")
        return

    conexao = sqlite3.connect("tanques.db")
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT tanque_nome, nivel, consumo_energia, status, data_hora
        FROM medicoes
        WHERE tanque_nome = ?
        ORDER BY id DESC
    """, (nome_tanque,))

    medicoes = cursor.fetchall()

    conexao.close()

    if not medicoes:
        mensagem.config(
            text=f"Nenhuma medição encontrada para o tanque '{nome_tanque}'."
        )
        return

    mensagem.config(
        text=f"{len(medicoes)} medição(ões) encontrada(s)."
    )

    for medicao in medicoes:

        tanque_nome, nivel, consumo, status, data_hora = medicao

        tabela.insert(
            "",
            tk.END,
            values=(
                tanque_nome,
                f"{nivel:.1f} L",
                f"{consumo:.2f} kWh",
                status,
                data_hora
            )
        )
# LIMPAR HISTÓRICO

def limpar_historico():

    for item in tabela.get_children():
        tabela.delete(item)

    mensagem.config(text="")

# INICIAR MONITORAMENTO

def iniciar_monitoramento():

    global tanque, consumo_total

    nome = nome_entry.get().strip()

    if nome == "":
        status_label.config(
            text="Digite o nome do tanque."
        )
        return

    try:
        capacidade = float(capacidade_entry.get())

    except ValueError:
        status_label.config(
            text="Digite uma capacidade válida."
        )
        return

    if capacidade <= 0:
        status_label.config(
            text="A capacidade deve ser maior que zero."
        )
        return

    tanque = Tanque(nome, capacidade)

    consumo_total = 0

    nome_entry.config(
        state="disabled"
    )

    capacidade_entry.config(
        state="disabled"
    )

    iniciar_button.config(
        state="disabled"
    )

    atualizar_interface()


# ATUALIZAR INTERFACE

def atualizar_interface():

    global consumo_total

    if tanque is None:
        return

    # Realiza uma nova medição
    consumo, status = tanque.atualizar_nivel()

    # Soma o consumo
    consumo_total += consumo

    # Calcula o percentual de ocupação
    percentual = (
        tanque.nivel_atual / tanque.capacidade
    ) * 100

    # Atualiza o nível
    nivel_label.config(
        text=f"Nível atual: {tanque.nivel_atual:.1f} L"
    )

    # Atualiza o percentual
    percentual_label.config(
        text=f"Ocupação: {percentual:.1f}%"
    )

    # Atualiza a barra de progresso
    barra["value"] = percentual

    # Atualiza o consumo atual
    consumo_label.config(
        text=f"Consumo atual: {consumo:.2f} kWh"
    )

    # Atualiza o consumo total
    total_label.config(
        text=f"Consumo total: {consumo_total:.2f} kWh"
    )

    # Atualiza o status da bomba
    status_label.config(
        text=f"Status da bomba: {status}"
    )

    # Nova medição após 2 segundos
    janela.after(
        2000,
        atualizar_interface
    )

# JANELA PRINCIPAL


janela = tk.Tk()

janela.title("Monitoramento do Tanque")
janela.geometry("950x750")

# TÍTULO
titulo = tk.Label(
    janela,
    text="Monitoramento do Tanque",
    font=("Arial", 20)
)

titulo.pack(pady=20)

# NOME DO TANQUE

nome_label = tk.Label(
    janela,
    text="Nome do tanque:"
)

nome_label.pack()

nome_entry = tk.Entry(
    janela,
    width=30
)

nome_entry.pack(pady=5)

# CAPACIDADE
capacidade_label = tk.Label(
    janela,
    text="Capacidade (L):"
)

capacidade_label.pack()

capacidade_entry = tk.Entry(
    janela,
    width=30
)

capacidade_entry.pack(pady=5)


# ==========================================================
# INFORMAÇÕES DO MONITORAMENTO
# ==========================================================

nivel_label = tk.Label(
    janela,
    text="Nível atual: -",
    font=("Arial", 14)
)

nivel_label.pack(pady=8)


percentual_label = tk.Label(
    janela,
    text="Ocupação: -",
    font=("Arial", 14)
)

percentual_label.pack(pady=5)


# ==========================================================
# BARRA DE PROGRESSO
# ==========================================================

barra = ttk.Progressbar(
    janela,
    orient="horizontal",
    length=400,
    mode="determinate"
)

barra.pack(pady=10)


# ==========================================================
# CONSUMO E STATUS DA BOMBA
# ==========================================================

consumo_label = tk.Label(
    janela,
    text="Consumo atual: -",
    font=("Arial", 14)
)

consumo_label.pack(pady=5)


total_label = tk.Label(
    janela,
    text="Consumo total: -",
    font=("Arial", 14)
)

total_label.pack(pady=5)


status_label = tk.Label(
    janela,
    text="Status da bomba: -",
    font=("Arial", 14)
)

status_label.pack(pady=5)


# ==========================================================
# BOTÃO INICIAR
# ==========================================================

iniciar_button = tk.Button(
    janela,
    text="Iniciar monitoramento",
    command=iniciar_monitoramento
)

iniciar_button.pack(pady=15)

# HISTÓRICO
historico_titulo = tk.Label(
    janela,
    text="Histórico de Medições",
    font=("Arial", 16)
)

historico_titulo.pack(pady=10)


# Botões do histórico
frame_botoes = tk.Frame(janela)

frame_botoes.pack(pady=5)


botao_consultar = tk.Button(
    frame_botoes,
    text="Consultar histórico",
    command=consultar_historico
)

botao_consultar.pack(
    side="left",
    padx=5
)


botao_limpar = tk.Button(
    frame_botoes,
    text="Limpar",
    command=limpar_historico
)

botao_limpar.pack(
    side="left",
    padx=5
)


# Mensagem
mensagem = tk.Label(
    janela,
    text="",
    font=("Arial", 11)
)

mensagem.pack(pady=5)

# TABELA DO HISTÓRICO
frame_tabela = tk.Frame(janela)

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
    show="headings"
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
    width=130
)

tabela.column(
    "data_hora",
    width=180
)


# Barra de rolagem
barra_rolagem = ttk.Scrollbar(
    frame_tabela,
    orient="vertical",
    command=tabela.yview
)

tabela.configure(
    yscrollcommand=barra_rolagem.set
)


tabela.pack(
    side="left",
    fill="both",
    expand=True
)

barra_rolagem.pack(
    side="right",
    fill="y"
)

# INICIAR JANELA

janela.mainloop()