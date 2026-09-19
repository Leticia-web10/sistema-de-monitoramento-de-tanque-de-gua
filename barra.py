import tkinter as tk
from tkinter import ttk
from medicao import Tanque, criar_tabela_medicoes


criar_tabela_medicoes()

janela = tk.Tk()
janela.title("Nível do Tanque")
janela.geometry("500x400")


titulo = tk.Label(
    janela,
    text="Nível do Tanque",
    font=("Arial", 20)
)
titulo.pack(pady=20)


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


nivel_label = tk.Label(
    janela,
    text="Nível: -",
    font=("Arial", 16)
)
nivel_label.pack(pady=15)


barra = ttk.Progressbar(
    janela,
    orient="horizontal",
    length=350,
    mode="determinate"
)
barra.pack(pady=10)


percentual_label = tk.Label(
    janela,
    text="Ocupação: -",
    font=("Arial", 14)
)
percentual_label.pack(pady=10)


tanque = None


def iniciar_monitoramento():
    global tanque

    nome = nome_entry.get().strip()

    if nome == "":
        percentual_label.config(text="Digite o nome do tanque.")
        return

    try:
        capacidade = float(capacidade_entry.get())
    except ValueError:
        percentual_label.config(text="Digite uma capacidade válida.")
        return

    if capacidade <= 0:
        percentual_label.config(text="A capacidade deve ser maior que zero.")
        return

    tanque = Tanque(nome, capacidade)

    nome_entry.config(state="disabled")
    capacidade_entry.config(state="disabled")
    botao.config(state="disabled")

    atualizar_barra()


def atualizar_barra():
    if tanque is None:
        return

    tanque.atualizar_nivel()

    percentual = (tanque.nivel_atual / tanque.capacidade) * 100

    barra["value"] = percentual

    nivel_label.config(
        text=f"Nível: {tanque.nivel_atual:.1f} L"
    )

    percentual_label.config(
        text=f"Ocupação: {percentual:.1f}%"
    )

    janela.after(2000, atualizar_barra)


botao = tk.Button(
    janela,
    text="Iniciar monitoramento",
    command=iniciar_monitoramento
)
botao.pack(pady=15)


janela.mainloop()