from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import Any

from db.configuracao import ErroConfiguracao


PALAVRAS_PROIBIDAS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|EXEC(?:UTE)?|GRANT|REVOKE)\b",
    flags=re.IGNORECASE,
)


def _sem_comentarios(sql: str) -> str:
    sql = re.sub(r"/\*.*?\*/", "", sql, flags=re.DOTALL)
    return re.sub(r"--[^\r\n]*", "", sql)


def validar_consulta_somente_leitura(sql: str) -> None:
    limpa = _sem_comentarios(sql).strip()
    if not re.match(r"^(SELECT|WITH)\b", limpa, flags=re.IGNORECASE):
        raise ErroConfiguracao("A consulta de extracao deve iniciar com SELECT ou WITH.")
    if PALAVRAS_PROIBIDAS.search(limpa):
        raise ErroConfiguracao("A consulta de extracao contem comando de escrita ou administracao.")


def _valor_secreto(ambiente: dict[str, Any], campo: str) -> str | None:
    direto = ambiente.get(campo)
    if direto:
        return str(direto)
    variavel = ambiente.get(f"{campo}_env")
    return os.getenv(str(variavel)) if variavel else None


def string_conexao(ambiente: dict[str, Any]) -> str:
    if ambiente.get("connection_string"):
        return str(ambiente["connection_string"])

    servidor = ambiente.get("servidor")
    banco = ambiente.get("banco")
    if not servidor or not banco:
        raise ErroConfiguracao("Cada ambiente precisa de servidor e banco, ou de connection_string local.")

    driver = str(ambiente.get("odbc_driver", "ODBC Driver 17 for SQL Server"))
    autenticacao = str(ambiente.get("autenticacao", "")).casefold()
    base = f"DRIVER={{{driver}}};SERVER={servidor};DATABASE={banco};"
    if autenticacao in {"windows", "integrada", "integrated", "trusted_connection"}:
        return base + "Trusted_Connection=yes;"

    usuario = _valor_secreto(ambiente, "usuario")
    senha = _valor_secreto(ambiente, "senha")
    if not usuario or not senha:
        raise ErroConfiguracao(
            "Autenticacao SQL requer usuario/senha no ambiente local ou referencias usuario_env/senha_env."
        )
    return base + f"UID={usuario};PWD={senha};"


def abrir_conexao(ambiente: dict[str, Any]):
    try:
        import pyodbc
    except ImportError as erro:
        raise ErroConfiguracao("Instale pyodbc no ambiente Python antes de sincronizar.") from erro
    return pyodbc.connect(string_conexao(ambiente), autocommit=True, timeout=20)


def executar_leitura(conexao, sql: str, parametros: Iterable[Any]) -> list[dict[str, Any]]:
    validar_consulta_somente_leitura(sql)
    cursor = conexao.cursor()
    cursor.execute("SET NOCOUNT ON")
    cursor.execute(sql, list(parametros))
    colunas = [coluna[0].upper() for coluna in cursor.description]
    return [dict(zip(colunas, linha, strict=True)) for linha in cursor.fetchall()]
