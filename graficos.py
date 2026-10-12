import sqlite3
import tkinter as tk
from tkinter import messagebox
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


def buscar_medicoes(nome_tanque):
    conexao = sqlite3.connect("tanques.db")
    cursor = conexao.cursor()

    cursor.execute("""
        SELECT data_hora, nivel, consumo_energia
        FROM medicoes
        WHERE tanque_nome = ?
        ORDER BY id ASC
    """, (nome_tanque,))

    medicoes = cursor.fetchall()
    conexao.close()

    return medicoes


def atualizar_graficos():
    nome_tanque = nome_entry.get().strip()

    if nome_tanque == "":
        mensagem.config(
            text="Digite o nome do tanque.",
            fg="red"
        )
        return

    medicoes = buscar_medicoes(nome_tanque)

    if not medicoes:
        mensagem.config(
            text=f"Nenhuma medição encontrada para o tanque '{nome_tanque}'.",
            fg="red"
        )

        for widget in frame_graficos.winfo_children():
            widget.destroy()

        janela.after(2000, atualizar_graficos)
        return

    mensagem.config(
        text=f"{len(medicoes)} medição(ões) encontrada(s).",
        fg="green"
    )

    datas = [medicao[0] for medicao in medicoes]
    niveis = [medicao[1] for medicao in medicoes]
    consumos = [medicao[2] for medicao in medicoes]

    for widget in frame_graficos.winfo_children():
        widget.destroy()

    figura = Figure(figsize=(9, 7), dpi=100)

    # Gráfico do nível de água
    grafico_nivel = figura.add_subplot(211)

    grafico_nivel.plot(
        datas,
        niveis,
        marker="o"
    )

    grafico_nivel.set_title("Variação do nível de água")
    grafico_nivel.set_ylabel("Nível (L)")
    grafico_nivel.set_xlabel("Data/Hora")
    grafico_nivel.tick_params(
        axis="x",
        rotation=45
    )
    grafico_nivel.grid(True)

    # Gráfico do consumo de energia
    grafico_consumo = figura.add_subplot(212)

    grafico_consumo.plot(
        datas,
        consumos,
        marker="o"
    )

    grafico_consumo.set_title("Variação do consumo de energia")
    grafico_consumo.set_ylabel("Consumo (kWh)")
    grafico_consumo.set_xlabel("Data/Hora")
    grafico_consumo.tick_params(
        axis="x",
        rotation=45
    )
    grafico_consumo.grid(True)

    figura.tight_layout()

    canvas = FigureCanvasTkAgg(
        figura,
        master=frame_graficos
    )

    canvas.draw()

    canvas.get_tk_widget().pack(
        fill="both",
        expand=True
    )

    # Atualiza os gráficos novamente após 2 segundos
    janela.after(2000, atualizar_graficos)


def iniciar_graficos():
    nome_tanque = nome_entry.get().strip()

    if nome_tanque == "":
        messagebox.showwarning(
            "Atenção",
            "Digite o nome do tanque."
        )
        return

    atualizar_graficos()


janela = tk.Tk()

janela.title("Gráficos do Tanque")
janela.geometry("1000x750")


titulo = tk.Label(
    janela,
    text="Gráficos do Tanque",
    font=("Arial", 20)
)

titulo.pack(pady=15)


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


botao_graficos = tk.Button(
    janela,
    text="Gerar gráficos",
    command=iniciar_graficos
)

botao_graficos.pack(pady=10)


mensagem = tk.Label(
    janela,
    text="",
    font=("Arial", 11)
)

mensagem.pack(pady=5)


frame_graficos = tk.Frame(janela)

frame_graficos.pack(
    fill="both",
    expand=True,
    padx=20,
    pady=10
)


janela.mainloop()