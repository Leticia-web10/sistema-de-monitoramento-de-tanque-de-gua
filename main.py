"""
Ponto de entrada do Sistema de Monitoramento de Tanque de Água.

Execute este arquivo para iniciar o programa:

    python main.py

Ele garante que as dependências estejam instaladas e abre a interface
integrada (monitoramento, histórico, gráficos, alertas e controle do tanque).
"""

from instalar_dependencias import garantir_dependencias


def main():
    garantir_dependencias()

    # Importa só depois de garantir as dependências (o matplotlib é usado lá)
    import interface_integrada

    interface_integrada.iniciar()


if __name__ == "__main__":
    main()