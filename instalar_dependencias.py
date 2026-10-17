"""
Verifica e instala automaticamente as dependências do programa.

O sqlite3 e o tkinter já vêm com o Python. A única biblioteca externa
é o matplotlib (usado nos gráficos), listada no requirements.txt.

Uso direto:  python instalar_dependencias.py
(O main.py já chama esta verificação sozinho antes de abrir o programa.)
"""

import importlib
import importlib.util
import subprocess
import sys
from pathlib import Path

# módulo que o programa importa -> pacote que o pip instala
DEPENDENCIAS = {
    "matplotlib": "matplotlib",
}

ARQUIVO_REQUISITOS = Path(__file__).with_name("requirements.txt")


def dependencias_faltando():
    """Pacotes que ainda não estão instalados."""
    return [
        pacote
        for modulo, pacote in DEPENDENCIAS.items()
        if importlib.util.find_spec(modulo) is None
    ]


def garantir_dependencias():
    """Instala o que estiver faltando. Encerra o programa se não conseguir."""
    if importlib.util.find_spec("tkinter") is None:
        print("O Tkinter não está instalado neste Python.")
        print("No Windows, reinstale o Python marcando a opção 'tcl/tk and IDLE'.")
        print("No Linux, instale com: sudo apt install python3-tk")
        sys.exit(1)

    faltando = dependencias_faltando()
    if not faltando:
        return

    print("Instalando dependências:", ", ".join(faltando))

    if ARQUIVO_REQUISITOS.exists():
        comando = [sys.executable, "-m", "pip", "install", "-r", str(ARQUIVO_REQUISITOS)]
    else:
        comando = [sys.executable, "-m", "pip", "install", *faltando]

    try:
        subprocess.check_call(comando)
    except (subprocess.CalledProcessError, OSError):
        print("\nNão foi possível instalar as dependências automaticamente.")
        print("Instale manualmente com:  pip install -r requirements.txt")
        sys.exit(1)

    importlib.invalidate_caches()

    if dependencias_faltando():
        print("A instalação terminou, mas as dependências ainda não foram encontradas.")
        print("Reinicie o programa e tente de novo.")
        sys.exit(1)


if __name__ == "__main__":
    garantir_dependencias()
    print("Todas as dependências estão instaladas.")