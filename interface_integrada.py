"""
Sistema de Monitoramento de Tanque de Água - Interface integrada

Reúne em uma única tela:
  - monitoramento do tanque (barra de nível, ocupação, consumo, bomba)
  - alertas e detecção de anomalias e falhas (vazamento, falha na bomba),
    com registro dos eventos
  - seletor para simular falhas e demonstrar a detecção
  - histórico de medições, atualizado enquanto o tanque está ligado
  - gráficos de nível e consumo (botão "Ver gráficos")
  - controle de ligar e desligar o tanque (o histórico é mantido)

As medições são salvas no tanques.db pelo medicao.py a cada atualização.

Para executar o programa use:  python main.py
"""

import random
import sqlite3
import tkinter as tk
from datetime import datetime
from statistics import mean, pstdev
from tkinter import ttk, messagebox

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure

from medicao import criar_tabela_medicoes, salvar_medicao, Tanque

# ===============================================================
# CONFIGURAÇÕES
# ===============================================================
BANCO = "tanques.db"
INTERVALO_MS = 2000
MAX_PONTOS_GRAFICO = 30      # últimas medições mostradas nos gráficos
MAX_LINHAS_HISTORICO = 500   # últimas medições mostradas na tabela
MAX_LINHAS_LOG = 100         # eventos mantidos no registro de alertas

# Parâmetros de alertas e anomalias (ajuste conforme a simulação)
LIMITE_NIVEL_CRITICO_PCT = 0.25     # nível <= 25% (a bomba reabastece abaixo de 20%)
LIMITE_NIVEL_ALTO_PCT = 0.95        # nível >= 95% da capacidade
LIMITE_QUEDA_VAZAMENTO_PCT = 0.05   # queda >= 5% da capacidade por medição
MEDICOES_VAZAMENTO = 3              # 3 medições seguidas = 2 quedas
STATUS_BOMBA_LIGADA = "Bomba Ligada"  # status salvo pelo medicao.py ao reabastecer
STATUS_NORMAL = "Normal"
LIMITE_CONSUMO_BOMBA_KWH = 3.5      # consumo máximo com a bomba ligada
LIMITE_CONSUMO_REPOUSO_KWH = 0.3    # consumo máximo com a bomba em repouso
LIMITE_CONSUMO_BOMBA_MIN_KWH = 2.0  # consumo mínimo esperado com a bomba ligada
LIMITE_FALHA_BOMBA_PCT = 0.20       # abaixo disso a bomba deveria ter ligado

JANELA_ANALISE = 20                 # quantas medições anteriores comparar
MIN_HISTORICO = 5                   # mínimo de medições para a análise estatística
LIMITE_Z = 3.0                      # desvios padrão para considerar anômalo
DESVIO_MINIMO_CONSUMO_KWH = 0.1     # evita falso alarme quando o histórico varia pouco por acaso

# Posições na tupla da medição: (id, data_hora, nivel, consumo_energia, status)
NIVEL = 2
CONSUMO = 3
STATUS = 4

# Textos
ALERTA_NIVEL_CRITICO = "Nível de água crítico"
ALERTA_NIVEL_ALTO = "Nível de água muito alto"
ALERTA_VAZAMENTO = "Possível vazamento"
ALERTA_CONSUMO = "Consumo de energia acima do limite"
ANOMALIA_CONSUMO = "Consumo muito acima do padrão recente"
ANOMALIA_QUEDA = "Queda de nível muito acima do padrão recente"
FALHA_BOMBA_CONSUMO = "Possível falha na bomba: ligada com consumo muito baixo"
FALHA_BOMBA_PARADA = "Possível falha na bomba: nível muito baixo e ela não ligou"

# Falhas que podem ser simuladas (seletor da tela)
FALHA_NENHUMA = "Funcionamento normal"
FALHA_VAZAMENTO = "Vazamento"
FALHA_BOMBA = "Falha na bomba"

NORMAL = "Normal"
ANOMALA = "Anômala"

# Cores e fonte
COR_FUNDO = "#eef2f7"
COR_CARD = "#ffffff"
COR_BORDA = "#d5dde6"
COR_TITULO = "#1f3a5f"
COR_TEXTO = "#1f2933"
COR_TEXTO_SUAVE = "#6b7785"
COR_OK = "#1e9e55"
COR_ALERTA = "#d99100"
COR_ERRO = "#d64545"
COR_AGUA = "#2f8fdd"
COR_VAZIO = "#e3e9f0"
COR_PRIMARIA = "#2f6fb5"
COR_NEUTRA = "#7b8794"
COR_BOTAO_INATIVO = "#c5ccd4"
FONTE = "Segoe UI"

# ===============================================================
# ESTADO
# ===============================================================
tanque = None
consumo_total = 0.0
ligado = False
job = None  # id do agendamento do after(), para poder cancelar
ultimas_mensagens = ()  # alertas mostrados na última medição (evita repetir no registro)
cores_botoes = {}  # cor original de cada botão (para reativar depois de desativar)

# Janela dos gráficos
janela_graficos = None
frame_graficos = None
figura_graficos = None
canvas_graficos = None
job_graficos = None

# Tanque que a tabela de histórico está mostrando (para atualizar ao vivo)
historico_nome = None

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


def contar_medicoes(nome):
    """Quantidade total de medições salvas do tanque."""
    conexao = sqlite3.connect(BANCO)
    try:
        cursor = conexao.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM medicoes WHERE tanque_nome = ?", (nome,)
        )
        total = cursor.fetchone()[0]
    finally:
        conexao.close()
    return total


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
    status = medicoes[-1][STATUS]

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

    if status == STATUS_BOMBA_LIGADA:
        limite_consumo = LIMITE_CONSUMO_BOMBA_KWH
    else:
        limite_consumo = LIMITE_CONSUMO_REPOUSO_KWH

    if consumo > limite_consumo:
        resultado.append(ALERTA_CONSUMO)

    # Falha na bomba: ligada mas sem consumir o esperado...
    if status == STATUS_BOMBA_LIGADA and consumo < LIMITE_CONSUMO_BOMBA_MIN_KWH:
        resultado.append(FALHA_BOMBA_CONSUMO)

    # ...ou nível muito baixo e a bomba não ligou
    if status != STATUS_BOMBA_LIGADA and nivel < LIMITE_FALHA_BOMBA_PCT * capacidade:
        resultado.append(FALHA_BOMBA_PARADA)

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

    # Consumo de energia: compara só com medições no mesmo estado da bomba
    # (reabastecer consome bem mais, e isso é normal)
    consumos = [m[CONSUMO] for m in historico if m[STATUS] == atual[STATUS]]
    if (
        len(consumos) >= MIN_HISTORICO
        and z_score(atual[CONSUMO], consumos, DESVIO_MINIMO_CONSUMO_KWH) > LIMITE_Z
    ):
        anomalias.append(ANOMALIA_CONSUMO)

    # Queda de nível (positivo = nível diminuiu)
    quedas = [
        historico[i][NIVEL] - historico[i + 1][NIVEL]
        for i in range(len(historico) - 1)
    ]
    quedas = [q for q in quedas if q >= 0]  # ignora reabastecimento (nível sobe)
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

    alertas_anomalos = {
        ALERTA_VAZAMENTO,
        ALERTA_CONSUMO,
        FALHA_BOMBA_CONSUMO,
        FALHA_BOMBA_PARADA,
    }
    anomala = bool(anomalias) or any(a in alertas_anomalos for a in resultado_alertas)

    mensagens = resultado_alertas + [a for a in anomalias if a not in resultado_alertas]
    return (ANOMALA if anomala else NORMAL), mensagens


def eh_anomalia(mensagem_alerta):
    """True para mensagens que indicam comportamento anormal (e não só um aviso)."""
    return mensagem_alerta in (
        ALERTA_VAZAMENTO,
        ALERTA_CONSUMO,
        FALHA_BOMBA_CONSUMO,
        FALHA_BOMBA_PARADA,
        ANOMALIA_CONSUMO,
        ANOMALIA_QUEDA,
    )


# ===============================================================
# AJUDANTES DE INTERFACE
# ===============================================================
def nome_atual():
    return tanque.nome if tanque is not None else nome_entry.get().strip()


def ativar_botao(botao, ativo):
    botao.config(
        state="normal" if ativo else "disabled",
        bg=cores_botoes[botao] if ativo else COR_BOTAO_INATIVO,
        cursor="hand2" if ativo else "arrow",
    )


def definir_status(texto, cor):
    status_label.config(text=texto, fg=cor)


def definir_banner(texto, cor):
    banner_label.config(text=texto, bg=cor, fg="white")


def desenhar_tanque(percentual=None):
    """Barra de nível em formato de tanque, com a cor mudando conforme o nível."""
    c = tanque_canvas
    c.delete("all")

    x0, y0, x1, y1 = 16, 12, 96, 212

    c.create_rectangle(x0, y0, x1, y1, fill=COR_VAZIO, outline=COR_TITULO, width=2)

    # Marcas de 25%, 50% e 75%
    for marca in (25, 50, 75):
        y = y1 - (y1 - y0) * marca / 100
        c.create_line(x1 + 2, y, x1 + 9, y, fill=COR_TEXTO_SUAVE)
        c.create_text(x1 + 12, y, text=f"{marca}%", anchor="w",
                      fill=COR_TEXTO_SUAVE, font=(FONTE, 8))

    if percentual is None:
        c.create_text((x0 + x1) / 2, (y0 + y1) / 2, text="--",
                      fill=COR_TEXTO_SUAVE, font=(FONTE, 16, "bold"))
        return

    p = max(0, min(100, percentual))
    topo = y1 - 1 - (y1 - y0 - 2) * p / 100

    if percentual <= LIMITE_NIVEL_CRITICO_PCT * 100:
        cor = COR_ERRO
    else:
        cor = COR_AGUA

    if p > 0:
        c.create_rectangle(x0 + 1, topo, x1 - 1, y1 - 1, fill=cor, outline="")

    meio = (y0 + y1) / 2
    cor_texto = "white" if topo <= meio else COR_TEXTO
    c.create_text((x0 + x1) / 2, meio, text=f"{p:.0f}%",
                  fill=cor_texto, font=(FONTE, 18, "bold"))


def mostrar_nivel():
    """Atualiza nível, ocupação e a barra de nível com os dados do tanque."""
    if tanque is None:
        return

    percentual = (tanque.nivel_atual / tanque.capacidade) * 100

    nivel_label.config(text=f"{tanque.nivel_atual:.1f} L")
    percentual_label.config(text=f"{percentual:.1f}%")
    desenhar_tanque(percentual)


def retomar_nivel_salvo(novo):
    """
    Ao ligar um tanque que já tem medições, continua do último nível salvo
    em vez de voltar para o nível máximo.
    """
    ultima = buscar_ultimas(novo.nome, 1)
    if ultima and 0 < ultima[0][NIVEL] <= novo.capacidade:
        novo.nivel_atual = ultima[0][NIVEL]


def registrar_no_log(classificacao, mensagens):
    """Guarda no registro de alertas só o que apareceu de novo."""
    global ultimas_mensagens

    atuais = tuple(mensagens)
    novos = [m for m in atuais if m not in ultimas_mensagens]
    ultimas_mensagens = atuais

    hora = datetime.now().strftime("%H:%M:%S")

    for texto in novos:
        if eh_anomalia(texto):
            tipo, tag = "Anomalia", "anomalia"
        else:
            tipo, tag = "Alerta", "alerta"
        log_tabela.insert("", 0, values=(hora, tipo, texto), tags=(tag,))

    linhas = log_tabela.get_children()
    for item in linhas[MAX_LINHAS_LOG:]:
        log_tabela.delete(item)


# ===============================================================
# ALERTAS NA INTERFACE
# ===============================================================
def verificar_anomalias():
    if tanque is None:
        return

    medicoes = buscar_ultimas(tanque.nome, JANELA_ANALISE + 1)

    if not medicoes:
        definir_banner("Aguardando medições", COR_NEUTRA)
        alerta_label.config(text="Nenhuma medição disponível.")
        return

    classificacao, mensagens = avaliar(medicoes, tanque.capacidade)

    if classificacao == ANOMALA:
        definir_banner("⚠  ANOMALIA DETECTADA   ·   Classificação: Anômala", COR_ERRO)
    elif mensagens:
        definir_banner("⚠  ALERTA   ·   Classificação: Normal", COR_ALERTA)
    else:
        definir_banner("✔  Operação normal   ·   Classificação: Normal", COR_OK)

    if mensagens:
        alerta_label.config(text="\n".join(f"•  {m}" for m in mensagens))
    else:
        alerta_label.config(text="Nenhum alerta no momento.")

    registrar_no_log(classificacao, mensagens)


# ===============================================================
# SIMULAÇÃO DE FALHAS (para demonstrar a detecção)
# ===============================================================
class TanqueSimulado(Tanque):
    """
    Tanque do medicao.py com opção de simular falhas.

    Sem falha, usa exatamente o comportamento do medicao.py. Com falha:
      - Vazamento: o nível cai muito mais rápido a cada medição.
      - Falha na bomba: abaixo de 20% a bomba "liga" mas consome pouco e
        não reabastece o tanque.
    """

    def __init__(self, nome, capacidade, obter_falha):
        super().__init__(nome, capacidade)
        self.obter_falha = obter_falha  # função que devolve a falha escolhida

    def atualizar_nivel(self):
        falha = self.obter_falha()

        if falha not in (FALHA_VAZAMENTO, FALHA_BOMBA):
            return super().atualizar_nivel()

        self.nivel_atual -= random.randint(5, 20)

        if falha == FALHA_VAZAMENTO:
            self.nivel_atual -= random.uniform(0.06, 0.08) * self.capacidade

        if self.nivel_atual < 0.2 * self.capacidade:
            status = STATUS_BOMBA_LIGADA
            if falha == FALHA_BOMBA:
                self.bomba.ligada = True
                consumo = round(random.uniform(0.2, 1.0), 2)
            else:
                self.nivel_atual = self.capacidade
                consumo = self.bomba.ligar()
        else:
            status = STATUS_NORMAL
            consumo = self.bomba.desligar()

        self.nivel_atual = max(0.0, self.nivel_atual)

        salvar_medicao(self.nome, self.nivel_atual, consumo, status)
        return consumo, status


def mudar_falha(evento=None):
    falha = falha_var.get()
    if falha == FALHA_NENHUMA:
        mensagem.config(text="Simulação: funcionamento normal.", fg=COR_TEXTO_SUAVE)
    else:
        mensagem.config(text=f"Simulando: {falha}.", fg=COR_ALERTA)


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

    mostrar_nivel()
    consumo_label.config(text=f"{consumo:.2f} kWh")
    total_label.config(text=f"{consumo_total:.2f} kWh")
    bomba_label.config(text=status)

    adicionar_ao_historico()
    verificar_anomalias()

    job = janela.after(INTERVALO_MS, atualizar_interface)


def ligar_tanque():
    global tanque, consumo_total, ligado, ultimas_mensagens

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

        novo = TanqueSimulado(nome, capacidade, lambda: falha_var.get())
        retomar_nivel_salvo(novo)
        tanque = novo
        consumo_total = 0.0

    ligado = True
    ultimas_mensagens = ()

    nome_entry.config(state="disabled")
    capacidade_entry.config(state="disabled")
    ativar_botao(ligar_button, False)
    ativar_botao(desligar_button, True)
    ativar_botao(novo_button, False)

    definir_status("●  Tanque ligado", "#7ee2a8")
    mostrar_nivel()
    consultar_historico()

    mensagem.config(text="Tanque ligado.", fg=COR_OK)

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

    definir_status("●  Tanque desligado", "#ff9d9d")
    bomba_label.config(text="Desligada")
    definir_banner("Tanque desligado   ·   Classificação: -", COR_NEUTRA)
    alerta_label.config(text="As medições estão pausadas.")

    ativar_botao(ligar_button, True)
    ativar_botao(desligar_button, False)
    ativar_botao(novo_button, True)

    mensagem.config(text="Tanque desligado. O histórico foi mantido.", fg=COR_ERRO)


def novo_tanque():
    """Permite monitorar outro tanque sem reiniciar o programa."""
    global tanque, consumo_total, historico_nome, ultimas_mensagens

    if ligado:
        return

    tanque = None
    consumo_total = 0.0
    historico_nome = None
    ultimas_mensagens = ()

    nome_entry.config(state="normal")
    capacidade_entry.config(state="normal")
    nome_entry.delete(0, tk.END)
    capacidade_entry.delete(0, tk.END)

    nivel_label.config(text="-")
    percentual_label.config(text="-")
    consumo_label.config(text="-")
    total_label.config(text="-")
    bomba_label.config(text="-")
    desenhar_tanque(None)

    definir_status("●  Aguardando", "#c5ccd4")
    definir_banner("Aguardando medições", COR_NEUTRA)
    alerta_label.config(text="Nenhum alerta no momento.")

    for item in tabela.get_children():
        tabela.delete(item)
    for item in log_tabela.get_children():
        log_tabela.delete(item)
    historico_info.config(text="")

    ativar_botao(novo_button, False)
    mensagem.config(text="Informe os dados do novo tanque.", fg=COR_TEXTO_SUAVE)


# ===============================================================
# HISTÓRICO
# ===============================================================
def linha_do_historico(nome, m):
    """Valores e tags de uma linha da tabela de histórico."""
    valores = (nome, f"{m[NIVEL]:.1f} L", f"{m[CONSUMO]:.2f} kWh", m[STATUS], m[1])
    tags = ("bomba",) if m[STATUS] == STATUS_BOMBA_LIGADA else ()
    return valores, tags


def consultar_historico():
    global historico_nome

    nome = nome_atual()

    if nome == "":
        messagebox.showwarning("Atenção", "Digite o nome do tanque.")
        return

    medicoes = buscar_ultimas(nome, MAX_LINHAS_HISTORICO)

    for item in tabela.get_children():
        tabela.delete(item)

    historico_nome = nome
    agora = datetime.now().strftime("%H:%M:%S")

    if not medicoes:
        if ligado:
            historico_info.config(text="Aguardando as primeiras medições...",
                                  fg=COR_TEXTO_SUAVE)
            return
        historico_info.config(text=f"Nenhuma medição para '{nome}' · {agora}",
                              fg=COR_ERRO)
        mensagem.config(text=f"Nenhuma medição encontrada para '{nome}'.", fg=COR_ERRO)
        return

    for m in medicoes:
        valores, tags = linha_do_historico(nome, m)
        tabela.insert("", "end", values=valores, tags=tags)

    tabela.update_idletasks()
    tabela.yview_moveto(1.0)

    total = contar_medicoes(nome)
    historico_info.config(
        text=f"Últimas {len(medicoes)} de {total} medições · {agora}",
        fg=COR_TEXTO_SUAVE,
    )
    mensagem.config(text=f"Histórico de '{nome}' atualizado.", fg=COR_OK)


def adicionar_ao_historico():
    """Acrescenta a última medição na tabela enquanto o tanque está ligado."""
    if tanque is None or historico_nome != tanque.nome:
        return

    ultima = buscar_ultimas(tanque.nome, 1)
    if not ultima:
        return

    # Só acompanha a última linha se a tabela já estiver rolada até o fim
    tabela.update_idletasks()
    no_fim = tabela.yview()[1] >= 0.99

    valores, tags = linha_do_historico(tanque.nome, ultima[0])
    tabela.insert("", "end", values=valores, tags=tags)

    linhas = tabela.get_children()
    if len(linhas) > MAX_LINHAS_HISTORICO:
        tabela.delete(linhas[0])

    if no_fim:
        tabela.update_idletasks()
        tabela.yview_moveto(1.0)

    historico_info.config(
        text=f"Ao vivo: últimas {len(tabela.get_children())} de "
             f"{contar_medicoes(tanque.nome)} medições · "
             f"{datetime.now().strftime('%H:%M:%S')}",
        fg=COR_OK,
    )


def limpar_historico():
    nome = nome_atual()

    if nome == "":
        messagebox.showwarning("Atenção", "Digite o nome do tanque.")
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

    historico_info.config(text="")
    mensagem.config(text=f"Histórico de '{nome}' apagado.", fg=COR_OK)


# ===============================================================
# GRÁFICOS
# ===============================================================
def atualizar_graficos():
    global job_graficos

    job_graficos = None

    # Cópias locais: se a janela fechar no meio, não quebra
    figura = figura_graficos
    canvas = canvas_graficos

    if janela_graficos is None or figura is None or canvas is None:
        return

    nome = nome_atual()
    medicoes = buscar_ultimas(nome, MAX_PONTOS_GRAFICO)

    # Reaproveita a mesma figura: limpa e desenha de novo (não recria widgets)
    figura.clear()

    if not medicoes:
        figura.text(
            0.5,
            0.5,
            f"Nenhuma medição encontrada para o tanque '{nome}'.",
            ha="center",
            va="center",
            color="red",
            fontsize=12,
        )
    else:
        # Posição da medição (evita juntar medições feitas no mesmo segundo)
        posicoes = list(range(1, len(medicoes) + 1))
        niveis = [m[NIVEL] for m in medicoes]
        consumos = [m[CONSUMO] for m in medicoes]

        # Gráfico do nível de água
        grafico_nivel = figura.add_subplot(211)
        grafico_nivel.plot(posicoes, niveis, marker="o", color=COR_AGUA)
        grafico_nivel.set_title("Variação do nível de água")
        grafico_nivel.set_ylabel("Nível (L)")
        grafico_nivel.tick_params(axis="x", labelbottom=False)
        grafico_nivel.grid(True, alpha=0.4)

        # Gráfico do consumo de energia
        grafico_consumo = figura.add_subplot(212)
        grafico_consumo.plot(posicoes, consumos, marker="o", color=COR_ALERTA)
        grafico_consumo.set_title("Variação do consumo de energia")
        grafico_consumo.set_ylabel("Consumo (kWh)")
        grafico_consumo.tick_params(axis="x", labelbottom=False)
        grafico_consumo.grid(True, alpha=0.4)

        figura.tight_layout()

    canvas.draw()

    # Atualiza os gráficos novamente após 2 segundos
    job_graficos = janela.after(INTERVALO_MS, atualizar_graficos)


def abrir_graficos():
    global janela_graficos, frame_graficos, figura_graficos, canvas_graficos

    if nome_atual() == "":
        messagebox.showwarning("Atenção", "Digite o nome do tanque.")
        return

    # Se a janela já está aberta, só traz para a frente
    if janela_graficos is not None and janela_graficos.winfo_exists():
        janela_graficos.lift()
        return

    janela_graficos = tk.Toplevel(janela)
    janela_graficos.title("Gráficos do Tanque")
    janela_graficos.geometry("900x650")
    janela_graficos.protocol("WM_DELETE_WINDOW", fechar_graficos)

    frame_graficos = tk.Frame(janela_graficos)
    frame_graficos.pack(fill="both", expand=True, padx=10, pady=10)

    # A figura e o canvas são criados uma vez só
    figura_graficos = Figure(figsize=(9, 6), dpi=100)
    canvas_graficos = FigureCanvasTkAgg(figura_graficos, master=frame_graficos)
    canvas_graficos.get_tk_widget().pack(fill="both", expand=True)

    atualizar_graficos()


def fechar_graficos():
    global janela_graficos, frame_graficos, figura_graficos, canvas_graficos
    global job_graficos

    if job_graficos is not None:
        try:
            janela.after_cancel(job_graficos)
        except tk.TclError:
            pass
        job_graficos = None

    # Evita novas atualizações enquanto a janela fecha
    canvas_graficos = None
    figura_graficos = None
    frame_graficos = None

    if janela_graficos is not None:
        try:
            janela_graficos.destroy()
        except tk.TclError:
            pass
        janela_graficos = None


def ao_fechar():
    if job is not None:
        janela.after_cancel(job)
    fechar_graficos()
    janela.destroy()


# ===============================================================
# CONSTRUÇÃO DA JANELA
# ===============================================================
def criar_card(pai, titulo):
    """Cria um cartão branco com borda fina. Retorna (cartão, área de conteúdo)."""
    borda = tk.Frame(pai, bg=COR_BORDA)
    interno = tk.Frame(borda, bg=COR_CARD)
    interno.pack(fill="both", expand=True, padx=1, pady=1)

    tk.Label(
        interno, text=titulo, font=(FONTE, 11, "bold"),
        bg=COR_CARD, fg=COR_TITULO,
    ).pack(anchor="w", padx=14, pady=(10, 4))

    conteudo = tk.Frame(interno, bg=COR_CARD)
    conteudo.pack(fill="both", expand=True, padx=14, pady=(0, 12))
    return borda, conteudo


def criar_botao(pai, texto, comando, cor):
    botao = tk.Button(
        pai, text=texto, command=comando, bg=cor, fg="white",
        activebackground=cor, activeforeground="white",
        disabledforeground="white", relief="flat", bd=0,
        padx=14, pady=6, font=(FONTE, 10, "bold"), cursor="hand2",
    )
    cores_botoes[botao] = cor
    return botao


def criar_entrada(pai):
    return tk.Entry(
        pai, font=(FONTE, 10), relief="flat", bd=0, width=24,
        highlightthickness=1, highlightbackground=COR_BORDA,
        highlightcolor=COR_PRIMARIA,
        disabledbackground="#e9edf2", disabledforeground=COR_TEXTO_SUAVE,
    )


def criar_linha_info(pai, linha, titulo):
    """Linha 'título ..... valor' dentro de um cartão. Retorna o label do valor."""
    tk.Label(
        pai, text=titulo, font=(FONTE, 9), bg=COR_CARD, fg=COR_TEXTO_SUAVE,
    ).grid(row=linha * 2, column=0, sticky="w", pady=(6, 0))
    valor = tk.Label(
        pai, text="-", font=(FONTE, 13, "bold"), bg=COR_CARD, fg=COR_TEXTO,
    )
    valor.grid(row=linha * 2 + 1, column=0, sticky="w")
    return valor


janela = tk.Tk()
janela.title("Monitoramento do Tanque de Água")
# Tamanho ajustado à tela (descontando barra de tarefas e barra de título)
largura = min(1220, janela.winfo_screenwidth() - 20)
altura = min(700, janela.winfo_screenheight() - 110)
janela.geometry(f"{largura}x{altura}")
janela.minsize(1000, 540)
janela.configure(bg=COR_FUNDO)
janela.protocol("WM_DELETE_WINDOW", ao_fechar)

estilo = ttk.Style(janela)
estilo.theme_use("clam")
estilo.configure(
    "Treeview", rowheight=24, font=(FONTE, 9),
    background="white", fieldbackground="white", bordercolor=COR_BORDA,
)
estilo.configure(
    "Treeview.Heading", font=(FONTE, 9, "bold"),
    background=COR_TITULO, foreground="white", relief="flat",
)
estilo.map("Treeview.Heading", background=[("active", COR_TITULO)])

# ---------------------------------------------------------------
# Cabeçalho
# ---------------------------------------------------------------
cabecalho = tk.Frame(janela, bg=COR_TITULO)
cabecalho.pack(fill="x")

tk.Label(
    cabecalho, text="💧  Monitoramento do Tanque de Água",
    font=(FONTE, 17, "bold"), bg=COR_TITULO, fg="white",
).pack(side="left", padx=20, pady=12)

status_label = tk.Label(
    cabecalho, text="●  Aguardando", font=(FONTE, 11, "bold"),
    bg=COR_TITULO, fg="#c5ccd4",
)
status_label.pack(side="right", padx=20)

# ---------------------------------------------------------------
# Mensagem de rodapé (fica sempre visível)
# ---------------------------------------------------------------
mensagem = tk.Label(
    janela, text="", font=(FONTE, 10), bg=COR_FUNDO, fg=COR_TEXTO_SUAVE,
    anchor="w",
)
mensagem.pack(side="bottom", fill="x", padx=18, pady=(0, 6))

# ---------------------------------------------------------------
# Corpo: coluna da esquerda (controle e medições), da direita (alertas e histórico)
# ---------------------------------------------------------------
corpo = tk.Frame(janela, bg=COR_FUNDO)
corpo.pack(fill="both", expand=True, padx=16, pady=(12, 4))
corpo.columnconfigure(1, weight=1)
corpo.rowconfigure(0, weight=1)

coluna_esq = tk.Frame(corpo, bg=COR_FUNDO)
coluna_esq.grid(row=0, column=0, sticky="ns", padx=(0, 12))

coluna_dir = tk.Frame(corpo, bg=COR_FUNDO)
coluna_dir.grid(row=0, column=1, sticky="nsew")

# --- Cartão: Tanque (entrada de dados e controle) ---
card_controle, area_controle = criar_card(coluna_esq, "Tanque")
card_controle.pack(fill="x")

tk.Label(area_controle, text="Nome do tanque", font=(FONTE, 9),
         bg=COR_CARD, fg=COR_TEXTO_SUAVE).pack(anchor="w")
nome_entry = criar_entrada(area_controle)
nome_entry.pack(fill="x", pady=(2, 8))

tk.Label(area_controle, text="Capacidade (L)", font=(FONTE, 9),
         bg=COR_CARD, fg=COR_TEXTO_SUAVE).pack(anchor="w")
capacidade_entry = criar_entrada(area_controle)
capacidade_entry.pack(fill="x", pady=(2, 10))

frame_controle = tk.Frame(area_controle, bg=COR_CARD)
frame_controle.pack(fill="x")

ligar_button = criar_botao(frame_controle, "Ligar", ligar_tanque, COR_OK)
ligar_button.pack(side="left", padx=(0, 6))

desligar_button = criar_botao(frame_controle, "Desligar", desligar_tanque, COR_ERRO)
desligar_button.pack(side="left", padx=(0, 6))
ativar_botao(desligar_button, False)

novo_button = criar_botao(frame_controle, "Novo tanque", novo_tanque, COR_NEUTRA)
novo_button.pack(side="left")
ativar_botao(novo_button, False)

tk.Label(area_controle, text="Simular falha (demonstração)", font=(FONTE, 9),
         bg=COR_CARD, fg=COR_TEXTO_SUAVE).pack(anchor="w", pady=(10, 0))

falha_var = tk.StringVar(value=FALHA_NENHUMA)
falha_combo = ttk.Combobox(
    area_controle, textvariable=falha_var, state="readonly", font=(FONTE, 10),
    values=(FALHA_NENHUMA, FALHA_VAZAMENTO, FALHA_BOMBA),
)
falha_combo.pack(fill="x", pady=(2, 0))
falha_combo.bind("<<ComboboxSelected>>", mudar_falha)

# --- Cartão: Nível e consumo (barra de nível + números) ---
card_medicoes, area_medicoes = criar_card(coluna_esq, "Nível e consumo")
card_medicoes.pack(fill="both", expand=True, pady=(12, 0))

tanque_canvas = tk.Canvas(
    area_medicoes, width=140, height=226, bg=COR_CARD, highlightthickness=0,
)
tanque_canvas.pack(side="left")

area_numeros = tk.Frame(area_medicoes, bg=COR_CARD)
area_numeros.pack(side="left", padx=(8, 0), anchor="n")

nivel_label = criar_linha_info(area_numeros, 0, "Nível atual")
percentual_label = criar_linha_info(area_numeros, 1, "Ocupação")
consumo_label = criar_linha_info(area_numeros, 2, "Consumo atual")
total_label = criar_linha_info(area_numeros, 3, "Consumo total")
bomba_label = criar_linha_info(area_numeros, 4, "Bomba")

desenhar_tanque(None)

# --- Cartão: Alertas e anomalias ---
card_alertas, area_alertas = criar_card(coluna_dir, "Alertas e anomalias")
card_alertas.pack(fill="x")

banner_label = tk.Label(
    area_alertas, text="Aguardando medições", font=(FONTE, 13, "bold"),
    bg=COR_NEUTRA, fg="white", pady=8,
)
banner_label.pack(fill="x")

alerta_label = tk.Label(
    area_alertas, text="Nenhum alerta no momento.", font=(FONTE, 10),
    bg=COR_CARD, fg=COR_TEXTO, justify="left", anchor="nw", height=5,
)
alerta_label.pack(fill="x", pady=(8, 6))

tk.Label(
    area_alertas, text="Registro de alertas", font=(FONTE, 9, "bold"),
    bg=COR_CARD, fg=COR_TEXTO_SUAVE, anchor="w",
).pack(fill="x")

frame_log = tk.Frame(area_alertas, bg=COR_CARD)
frame_log.pack(fill="x", pady=(2, 0))

log_tabela = ttk.Treeview(
    frame_log, columns=("hora", "tipo", "descricao"), show="headings", height=3,
)
log_tabela.heading("hora", text="Hora")
log_tabela.heading("tipo", text="Tipo")
log_tabela.heading("descricao", text="Descrição")
log_tabela.column("hora", width=80, stretch=False)
log_tabela.column("tipo", width=90, stretch=False)
log_tabela.column("descricao", width=400)
log_tabela.tag_configure("anomalia", foreground=COR_ERRO)
log_tabela.tag_configure("alerta", foreground="#a86f00")
log_tabela.pack(side="left", fill="x", expand=True)

log_scroll = ttk.Scrollbar(frame_log, orient="vertical", command=log_tabela.yview)
log_scroll.pack(side="right", fill="y")
log_tabela.configure(yscrollcommand=log_scroll.set)

# --- Cartão: Histórico de medições ---
card_historico, area_historico = criar_card(coluna_dir, "Histórico de medições")
card_historico.pack(fill="both", expand=True, pady=(12, 0))

frame_botoes = tk.Frame(area_historico, bg=COR_CARD)
frame_botoes.pack(fill="x", pady=(0, 8))

criar_botao(frame_botoes, "Consultar histórico", consultar_historico,
            COR_PRIMARIA).pack(side="left", padx=(0, 6))
criar_botao(frame_botoes, "Ver gráficos", abrir_graficos,
            COR_PRIMARIA).pack(side="left", padx=(0, 6))
criar_botao(frame_botoes, "Limpar", limpar_historico,
            COR_NEUTRA).pack(side="left")

historico_info = tk.Label(
    frame_botoes, text="", font=(FONTE, 9), bg=COR_CARD, fg=COR_TEXTO_SUAVE,
)
historico_info.pack(side="left", padx=12)

frame_tabela = tk.Frame(area_historico, bg=COR_CARD)
frame_tabela.pack(fill="both", expand=True)

colunas = ("tanque", "nivel", "consumo", "status", "data_hora")
cabecalhos = {
    "tanque": ("Tanque", 120),
    "nivel": ("Nível", 100),
    "consumo": ("Consumo", 110),
    "status": ("Status", 130),
    "data_hora": ("Data/Hora", 170),
}

# height pequeno: a tabela estica para ocupar o espaço que sobrar na janela
tabela = ttk.Treeview(frame_tabela, columns=colunas, show="headings", height=3)
for col, (texto, largura) in cabecalhos.items():
    tabela.heading(col, text=texto)
    tabela.column(col, width=largura)
tabela.tag_configure("bomba", background="#e3f0fc")

tabela.pack(side="left", fill="both", expand=True)

scroll = ttk.Scrollbar(frame_tabela, orient="vertical", command=tabela.yview)
scroll.pack(side="right", fill="y")
tabela.configure(yscrollcommand=scroll.set)


def iniciar():
    janela.mainloop()


if __name__ == "__main__":
    iniciar()