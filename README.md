# Sistema de Monitoramento de Tanque de Água

O projeto consiste no desenvolvimento de um sistema de monitoramento de tanque de água. O objetivo é permitir o acompanhamento do nível de água do tanque, do funcionamento da bomba e do consumo de energia, além de armazenar as medições realizadas.

O sistema realiza uma simulação do funcionamento de um tanque de água, permitindo acompanhar as medições e consultar os dados registrados.

## Tecnologias

As seguintes tecnologias são utilizadas no desenvolvimento do projeto:

- **Python:** linguagem utilizada no desenvolvimento do sistema.
- **SQLite:** banco de dados utilizado para armazenar as medições do tanque.
- **Tkinter:** utilizado na implementação das interfaces gráficas do sistema, em instalações padrão do Python para Windows, já está incluído.
- **Git e GitHub:** utilizados para controle de versão e organização do projeto.

## Pré-requisitos

Para executar o projeto, é necessário ter:

- Python 3.x instalado;
- Git instalado para clonar o repositório.

O projeto utiliza SQLite por meio do módulo `sqlite3`, que já faz parte da instalação padrão do Python.

## Instalação

### 1. Clonar o repositório

Abra o terminal e execute:

```bash
git clone https://github.com/Leticia-web10/sistema-de-monitoramento-de-tanque-de-gua.git
```

### 2. Acessar a pasta do projeto

```bash
cd sistema-de-monitoramento-de-tanque-de-gua
```

### 3. Executar o sistema

Para executar o monitoramento do tanque pelo console:

```bash
python medicao.py
```

O programa solicitará o nome do tanque e a capacidade do tanque em litros.

## Como usar

Após executar o sistema, informe:

1. O nome do tanque;
2. A capacidade do tanque em litros.

Depois de iniciar o monitoramento, o sistema realiza novas medições automaticamente.

Durante o monitoramento, o sistema:

- Simula o consumo de água do tanque;
- Atualiza o nível de água;
- Calcula o percentual de ocupação;
- Simula o funcionamento da bomba;
- Registra o consumo de energia;
- Armazena as medições no banco de dados SQLite.

As medições são registradas automaticamente a cada nova atualização.

## Interfaces gráficas

O projeto possui interfaces gráficas desenvolvidas utilizando Tkinter.

### Interface de acompanhamento do consumo da bomba

Para executar a interface:

```bash
python "interface de acompanhamento de bomba.py"
```

A interface permite acompanhar:

- Nível atual do tanque;
- Percentual de ocupação;
- Consumo atual de energia;
- Consumo total de energia;
- Status da bomba.

As informações são atualizadas automaticamente durante o monitoramento.

### Interface de histórico de medições

Para executar a interface de histórico:

```bash
python "interface historico de medicao.py"
```

A interface permite consultar as medições armazenadas no banco de dados.

São apresentados:

- Nome do tanque;
- Nível de água;
- Consumo de energia;
- Status da bomba;
- Data e hora da medição.

Também é possível realizar uma nova consulta e limpar os dados exibidos.

### Barra de progresso

Para executar a interface da barra de progresso:

```bash
python barra.py
```

A barra de progresso representa visualmente o percentual de ocupação do tanque.

A interface apresenta:

- Nível atual em litros;
- Percentual de ocupação;
- Barra de progresso;
- Atualização automática durante o monitoramento.

## Banco de dados

O sistema utiliza SQLite para armazenar as medições realizadas durante o monitoramento.

O banco de dados utilizado pelo projeto é:

```text
tanques.db
```

A tabela de medições armazena informações como:

- Identificação da medição;
- Nome do tanque;
- Nível de água;
- Consumo de energia;
- Status da bomba;
- Data e hora da medição.

O banco de dados e a tabela de medições são criados automaticamente pelo sistema quando necessário.

## Fluxo de funcionamento

O funcionamento do sistema segue, de forma geral, o seguinte fluxo:

1. Informar o nome do tanque;
2. Informar a capacidade do tanque;
3. Iniciar o monitoramento;
4. Realizar novas medições automaticamente;
5. Atualizar o nível de água;
6. Calcular o percentual de ocupação;
7. Verificar o funcionamento da bomba;
8. Registrar o consumo de energia;
9. Armazenar as medições no banco de dados;
10. Consultar as medições por meio da interface de histórico.

## Controle de versão

O projeto utiliza Git e GitHub para controle de versão.

As funcionalidades são desenvolvidas em branches separadas e posteriormente integradas ao projeto por meio de Pull Requests.

## Licença

Este projeto está sob a licença MIT. Consulte o arquivo [LICENSE.md](LICENSE.md) para mais informações.

## Autora

**Leticia Wang**

Engenharia Elétrica — Sistemas e Computação  
Universidade do Estado do Rio de Janeiro (UERJ)


