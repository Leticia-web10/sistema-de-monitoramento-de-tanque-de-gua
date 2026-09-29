import tkinter as tk
from medicao import criar_tabela_medicoes, Tanque


# Cria a tabela de medições no banco
criar_tabela_medicoes()
# JANELA PRINCIPAL


janela = tk.Tk()

janela.title("Monitoramento do Tanque")
janela.geometry("500x450")


titulo = tk.Label(
    janela,
    text="Monitoramento do Tanque",
    font=("Arial", 20)
)

titulo.pack(pady=20)

# NOME DO TANQUE

nome_label = tk.Label(
    janela,
    text="Nome do tanque"
)

nome_label.pack()


nome_entry = tk.Entry(
    janela
)

nome_entry.pack(pady=5)

# CAPACIDADE

capacidade_label = tk.Label(
    janela,
    text="Capacidade (L):"
)

capacidade_label.pack()


capacidade_entry = tk.Entry(
    janela
)

capacidade_entry.pack(pady=5)

# INFORMAÇÕES DO MONITORAMENTO


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
# VARIÁVEIS DO MONITORAMENTO

tanque = None
consumo_total = 0

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

def atualizar_interface():

    global consumo_total

    if tanque is None:
        return

    # Faz uma nova medição
    consumo, status = tanque.atualizar_nivel()

    # Soma o consumo
    consumo_total += consumo

    # Calcula o percentual do tanque
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

    # Faz uma nova medição depois de 2 segundos
    janela.after(
        2000,
        atualizar_interface
    )

iniciar_button = tk.Button(
    janela,
    text="Iniciar monitoramento",
    command=iniciar_monitoramento
)

iniciar_button.pack(pady=15)

# INICIAR JANELA

janela.mainloop()