"""Executa explicitamente a migration do núcleo financeiro em um SQLite indicado."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.migrations.m001_nucleo_financeiro import aplicar


def main() -> None:
    parser = argparse.ArgumentParser(description="Aplica a migration do núcleo financeiro em um SQLite local.")
    parser.add_argument(
        "--database",
        required=True,
        type=Path,
        help="Caminho explícito do arquivo SQLite local. Nenhuma configuração é lida.",
    )
    args = parser.parse_args()

    args.database.parent.mkdir(parents=True, exist_ok=True)
    conexao = sqlite3.connect(args.database)
    try:
        alterado = aplicar(conexao)
    finally:
        conexao.close()
    print("Migration aplicada." if alterado else "Migration já estava aplicada.")


if __name__ == "__main__":
    main()
