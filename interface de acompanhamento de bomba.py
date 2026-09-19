import tkinter as tk
from medicao import criar_tabela_medicoes, Tanque


# Cria a tabela de medições
criar_tabela_medicoes()


# Janela principal
janela = tk.Tk()
janela.title("Monitoramento do Tanque")
janela.geometry("500x450")


# Título
titulo = tk.Label(
    janela,
    text="Monitoramento do Tanque",
    font=("Arial", 20)
)
titulo.pack(pady=20)


# Nome do tanque
nome_label = tk.Label(
    janela,
    text="Nome do tanque:"
)
nome_label.pack()

nome_entry = tk.Entry(janela)
nome_entry.pack(pady=5)


# Capacidade
capacidade_label = tk.Label(
    janela,
    text="Capacidade (L):"
)
capacidade_label.pack()

capacidade_entry = tk.Entry(janela)
capacidade_entry.pack(pady=5)


# Informações do monitoramento
nivel_label = tk.Label(
    janela,
    text="Nível atual: -",
    font=("Arial", 14)
)
nivel_label.pack(pady=10)

percentual_label = tk.Label(
    janela,
    text="Ocupação: -",
    font=("Arial", 14)
)
percentual_label.pack(pady=5)

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


tanque = None
consumo_total = 0


def iniciar_monitoramento():
    global tanque, consumo_total

    nome = nome_entry.get()
    capacidade = float(capacidade_entry.get())

    tanque = Tanque(nome, capacidade)
    consumo_total = 0

    nome_entry.config(state="disabled")
    capacidade_entry.config(state="disabled")
    iniciar_button.config(state="disabled")

    atualizar_interface()


def atualizar_interface():
    global consumo_total

    consumo, status = tanque.atualizar_nivel()

    consumo_total += consumo

    percentual = (tanque.nivel_atual / tanque.capacidade) * 100

    nivel_label.config(
        text=f"Nível atual: {tanque.nivel_atual:.1f} L"
    )

    percentual_label.config(
        text=f"Ocupação: {percentual:.1f}%"
    )

    consumo_label.config(
        text=f"Consumo atual: {consumo:.2f} kWh"
    )

    total_label.config(
        text=f"Consumo total: {consumo_total:.2f} kWh"
    )

    status_label.config(
        text=f"Status da bomba: {status}"
    )

    janela.after(2000, atualizar_interface)


# Botão para iniciar
iniciar_button = tk.Button(
    janela,
    text="Iniciar monitoramento",
    command=iniciar_monitoramento
)
iniciar_button.pack(pady=15)


janela.mainloop()