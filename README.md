# Sistema de Monitoramento de Tanque de Água

O projeto consiste no desenvolvimento de um sistema de monitoramento de tanque de água. O objetivo é permitir o acompanhamento do nível de água do tanque, do funcionamento da bomba e do consumo de energia, armazenar as medições realizadas e identificar situações anormais, como níveis críticos, possíveis vazamentos e falhas na bomba.

O sistema realiza uma simulação do funcionamento de um tanque de água e reúne todas as funcionalidades em uma única interface gráfica.

## Funcionalidades

- **Cadastro do tanque:** nome e capacidade em litros.
- **Monitoramento em tempo real:** nível em litros, percentual de ocupação, consumo de energia atual e total e status da bomba, atualizados a cada 2 segundos.
- **Barra de nível:** representação visual do tanque, que muda de cor quando o nível está crítico.
- **Histórico de medições:** consulta das medições salvas no banco, atualizada ao vivo enquanto o tanque está ligado.
- **Gráficos:** variação do nível de água e do consumo de energia, abertos pelo botão "Ver gráficos".
- **Alertas e detecção de anomalias:** cada medição é classificada como Normal ou Anômala, com aviso em destaque e registro dos eventos.
- **Detecção de falhas:** possível vazamento e possível falha na bomba.
- **Controle do tanque:** ligar, desligar e trocar de tanque. Ao desligar, as medições param e o histórico é mantido. Ao ligar um tanque que já tem medições, o nível continua do último valor salvo.
- **Simulação de falhas:** um seletor na tela permite simular vazamento e falha na bomba para demonstrar a detecção.

## Tecnologias

- **Python:** linguagem utilizada no desenvolvimento do sistema.
- **SQLite:** banco de dados utilizado para armazenar as medições (módulo `sqlite3`, já incluído no Python).
- **Tkinter:** interface gráfica (já incluído nas instalações padrão do Python para Windows).
- **Matplotlib:** geração dos gráficos (instalado automaticamente pelo programa).
- **Git e GitHub:** controle de versão e organização do projeto.

## Pré-requisitos

- Python 3.x instalado, com Tkinter (na instalação padrão do Windows já vem marcado).
- Git instalado para clonar o repositório.
- Conexão com a internet na primeira execução, para instalar o matplotlib.

## Instalação e execução

1. Clonar o repositório:

```
git clone https://github.com/Leticia-web10/sistema-de-monitoramento-de-tanque-de-gua.git
```

2. Acessar a pasta do projeto:

```
cd sistema-de-monitoramento-de-tanque-de-gua
```

3. Executar o sistema:

```
python main.py
```

O `main.py` é o ponto de entrada do programa. Ele verifica se as dependências estão instaladas e, se faltar alguma, instala sozinho a partir do `requirements.txt` antes de abrir a interface.

Se preferir instalar as dependências manualmente:

```
pip install -r requirements.txt
```

## Como usar

1. Digite o **nome** e a **capacidade** do tanque (por exemplo, `tanque` e `1000`) e clique em **Ligar**.
2. O sistema passa a fazer uma nova medição a cada 2 segundos, atualizando o nível, a barra, o consumo, o histórico e os alertas.
3. Clique em **Ver gráficos** para abrir os gráficos de nível e consumo.
4. Clique em **Desligar** para pausar as medições. O histórico é mantido e é possível ligar o tanque novamente.
5. Clique em **Novo tanque** (com o tanque desligado) para monitorar outro tanque sem reiniciar o programa.
6. Os botões **Consultar histórico** e **Limpar** atuam sobre o tanque atual. O botão Limpar apaga apenas as medições desse tanque e só funciona com ele desligado.

## Alertas e detecção de anomalias

A cada medição, o sistema avalia as últimas medições do tanque.

| Situação | Regra | Tipo |
| --- | --- | --- |
| Nível crítico | nível até 25% da capacidade | Alerta |
| Nível muito alto | nível a partir de 95% da capacidade | Alerta |
| Possível vazamento | queda de pelo menos 5% da capacidade em duas medições seguidas | Anomalia |
| Consumo acima do limite | mais de 3,5 kWh com a bomba ligada ou mais de 0,3 kWh em repouso | Anomalia |
| Falha na bomba | bomba ligada com menos de 2,0 kWh, ou nível abaixo de 20% sem a bomba ligar | Anomalia |
| Comportamento fora do padrão | consumo ou queda de nível a mais de 3 desvios padrão da média das últimas 20 medições | Anomalia |

A medição é classificada como **Anômala** quando há vazamento, consumo acima do limite, falha na bomba ou comportamento fora do padrão. Nível crítico e nível alto aparecem como alertas, mas não tornam a medição anômala. O consumo é comparado apenas com medições no mesmo estado da bomba, já que reabastecer consome bem mais energia e isso é esperado.

Na interface, a classificação aparece em um banner colorido (verde, amarelo ou vermelho), com a lista dos alertas ativos e um registro com a hora de cada evento.

## Simulação de falhas

Como a simulação normal do tanque não gera problemas por conta própria, a tela tem o campo **Simular falha (demonstração)**, que pode ser alterado com o tanque ligado:

- **Funcionamento normal:** comportamento padrão do `medicao.py`.
- **Vazamento:** o nível cai muito mais rápido a cada medição.
- **Falha na bomba:** abaixo de 20% a bomba "liga", mas consome pouco e não reabastece o tanque.

A detecção leva de 2 a 3 medições (cerca de 4 a 6 segundos) para aparecer.

## Estrutura do projeto

| Arquivo | Descrição |
| --- | --- |
| `main.py` | Ponto de entrada do programa |
| `instalar_dependencias.py` | Verifica e instala as dependências automaticamente |
| `requirements.txt` | Lista de dependências externas (matplotlib) |
| `interface_integrada.py` | Interface integrada: monitoramento, histórico, gráficos, alertas e controle |
| `medicao.py` | Classes `Tanque` e `Bomba`, simulação das medições e gravação no banco |
| `graficos.py`, `barra.py` e demais `interface ... .py` | Interfaces individuais desenvolvidas nas etapas anteriores, mantidas no projeto |

## Banco de dados

O sistema utiliza SQLite para armazenar as medições. O arquivo `tanques.db` e a tabela de medições são criados automaticamente quando necessário.

A tabela de medições armazena:

- identificação da medição;
- nome do tanque;
- nível de água;
- consumo de energia;
- status da bomba;
- data e hora da medição.

## Execução pelo console (opcional)

Também é possível executar apenas a simulação, sem interface gráfica:

```
python medicao.py
```

O programa solicita o nome e a capacidade do tanque e exibe as medições no terminal.

## Controle de versão

O projeto utiliza Git e GitHub para controle de versão. As funcionalidades são desenvolvidas em branches separadas e integradas ao projeto por meio de Pull Requests.


## Autora

Leticia Wang

Engenharia Elétrica — Sistemas e Computação
Universidade do Estado do Rio de Janeiro (UERJ)
