from __future__ import annotations

import os
import re
from collections.abc import Iterable
from typing import Any

from db.configuracao import ErroConfiguracao


PALAVRAS_PROIBIDAS = re.compile(
    r"\b(INSERT|UPDATE|DELETE|MERGE|DROP|ALTER|CREATE|TRUNCATE|EXEC(?:UTE)?|GRANT|REVOKE|INTO|GO)\b",
    flags=re.IGNORECASE,
)


def _sem_comentarios(sql: str) -> str:
    """Remove comentarios reais sem confundir texto ou identificador com comentario."""
    resultado: list[str] = []
    indice = 0
    while indice < len(sql):
        if sql[indice] in "'\"[":
            abertura = sql[indice]
            fechamento = "]" if abertura == "[" else abertura
            resultado.append(sql[indice])
            indice += 1
            while indice < len(sql):
                resultado.append(sql[indice])
                if sql[indice] == fechamento:
                    indice += 1
                    if indice < len(sql) and sql[indice] == fechamento:
                        resultado.append(sql[indice])
                        indice += 1
                        continue
                    break
                indice += 1
            continue
        if sql.startswith("--", indice):
            fim = sql.find("\n", indice)
            if fim < 0:
                break
            resultado.append("\n")
            indice = fim + 1
            continue
        if sql.startswith("/*", indice):
            fim = sql.find("*/", indice + 2)
            if fim < 0:
                raise ErroConfiguracao("Comentario SQL sem fechamento.")
            indice = fim + 2
            continue
        resultado.append(sql[indice])
        indice += 1
    return "".join(resultado)


def _sem_textos_e_identificadores(sql: str) -> str:
    """Mascara literais e identificadores para a validacao nao gerar falso positivo.

    A funcao nao tenta interpretar T-SQL por completo; ela preserva apenas os
    separadores de instrucao e palavras-chave que importam para a barreira de
    leitura. Aspas duplicadas seguem a regra do SQL Server.
    """
    resultado: list[str] = []
    indice = 0
    while indice < len(sql):
        caractere = sql[indice]
        if caractere in "'\"":
            delimitador = caractere
            resultado.append(" ")
            indice += 1
            while indice < len(sql):
                if sql[indice] == delimitador:
                    indice += 1
                    if indice < len(sql) and sql[indice] == delimitador:
                        indice += 1
                        continue
                    break
                indice += 1
            continue
        if caractere == "[":
            resultado.append(" ")
            indice += 1
            while indice < len(sql):
                if sql[indice] == "]":
                    indice += 1
                    if indice < len(sql) and sql[indice] == "]":
                        indice += 1
                        continue
                    break
                indice += 1
            continue
        resultado.append(caractere)
        indice += 1
    return "".join(resultado)


def validar_consulta_somente_leitura(sql: str) -> None:
    limpa = _sem_comentarios(sql).strip()
    sem_textos = _sem_textos_e_identificadores(limpa)
    instrucoes = [parte.strip() for parte in sem_textos.split(";") if parte.strip()]
    if len(instrucoes) != 1:
        raise ErroConfiguracao("A extracao deve conter exatamente uma unica instrucao SQL.")
    if not re.match(r"^(SELECT|WITH)\b", instrucoes[0], flags=re.IGNORECASE):
        raise ErroConfiguracao("A consulta de extracao deve iniciar com SELECT ou WITH.")
    if PALAVRAS_PROIBIDAS.search(sem_textos):
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
    # A transacao explicita permite encerrar a sessao com ROLLBACK mesmo se o
    # servidor tiver alguma configuracao inesperada. A consulta continua
    # limitada a SELECT/WITH pela validacao central acima.
    return pyodbc.connect(string_conexao(ambiente), autocommit=False, timeout=20)


def executar_leitura(conexao, sql: str, parametros: Iterable[Any]) -> list[dict[str, Any]]:
    validar_consulta_somente_leitura(sql)
    cursor = conexao.cursor()
    try:
        cursor.execute("SET NOCOUNT ON")
        cursor.execute(sql, list(parametros))
        colunas = [coluna[0].upper() for coluna in cursor.description]
        return [dict(zip(colunas, linha, strict=True)) for linha in cursor.fetchall()]
    finally:
        try:
            conexao.rollback()
        finally:
            cursor.close()
