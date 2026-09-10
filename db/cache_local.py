from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any


CAMPOS_ORIGEM = (
    "TITULO_MOVIMENTO_ID", "CARTEIRA", "FANTASIA", "CNPJ_CPF", "CLIENTE", "CONJUNTO",
    "SIT_DOC", "DESC_SIT_DOC", "NUMERO_BOLETO", "NOSSO_NUMERO", "DATA_REMISSAO",
    "PONTEIRO", "DATA_VENCIMENTO", "VALOR_ORIGINAL", "DATA_BAIXA", "VALOR_BAIXA",
    "ATUALIZADO_EM_ORIGEM",
)


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor.isoformat(sep=" ")
    return str(valor)


class CacheLocal:
    def __init__(self, caminho: Path):
        caminho.parent.mkdir(parents=True, exist_ok=True)
        self.conexao = sqlite3.connect(caminho)
        self.conexao.row_factory = sqlite3.Row
        self._criar_estrutura()

    def close(self) -> None:
        self.conexao.close()

    def _criar_estrutura(self) -> None:
        self.conexao.executescript(
            """
            CREATE TABLE IF NOT EXISTS titulos_movimento (
                unidade TEXT NOT NULL,
                titulo_movimento_id TEXT NOT NULL,
                carteira TEXT,
                FANTASIA TEXT, CNPJ_CPF TEXT, CLIENTE TEXT, CONJUNTO TEXT,
                SIT_DOC TEXT, DESC_SIT_DOC TEXT, NUMERO_BOLETO TEXT,
                NOSSO_NUMERO TEXT, DATA_REMISSAO TEXT, PONTEIRO TEXT,
                DATA_VENCIMENTO TEXT, VALOR_ORIGINAL TEXT, DATA_BAIXA TEXT,
                VALOR_BAIXA TEXT, CRC_CPG TEXT NOT NULL,
                atualizado_em_origem TEXT NOT NULL, atualizado_em_cache TEXT NOT NULL,
                PRIMARY KEY (unidade, titulo_movimento_id)
            );
            CREATE INDEX IF NOT EXISTS ix_titulos_data_unidade
                ON titulos_movimento (DATA_BAIXA, unidade);
            CREATE INDEX IF NOT EXISTS ix_titulos_cnpj
                ON titulos_movimento (CNPJ_CPF);
            CREATE TABLE IF NOT EXISTS sync_estado (
                unidade TEXT PRIMARY KEY,
                marcador TEXT,
                titulo_movimento_id TEXT,
                ultima_sincronizacao TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sync_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ocorrido_em TEXT NOT NULL,
                unidade TEXT NOT NULL,
                status TEXT NOT NULL,
                registros INTEGER NOT NULL DEFAULT 0,
                detalhe TEXT
            );
            """
        )
        self.conexao.commit()

    def estado(self, unidade: str) -> dict[str, str] | None:
        linha = self.conexao.execute("SELECT * FROM sync_estado WHERE unidade = ?", (unidade,)).fetchone()
        return dict(linha) if linha else None

    def registrar_log(self, unidade: str, status: str, registros: int = 0, detalhe: str | None = None) -> None:
        self.conexao.execute(
            "INSERT INTO sync_log (ocorrido_em, unidade, status, registros, detalhe) VALUES (?, ?, ?, ?, ?)",
            (datetime.now().isoformat(sep=" "), unidade, status, registros, detalhe),
        )
        self.conexao.commit()

    def atualizar(self, unidade: str, crc_cpg: str, linhas: list[dict[str, Any]], marcador: str | None,
                  titulo_movimento_id: str | None) -> None:
        faltantes = [campo for campo in CAMPOS_ORIGEM if any(campo not in linha for linha in linhas)]
        if faltantes:
            raise ValueError(f"Consulta de extracao sem aliases obrigatorios: {', '.join(sorted(set(faltantes)))}")

        agora = datetime.now().isoformat(sep=" ")
        comando = """
            INSERT INTO titulos_movimento (
                unidade, titulo_movimento_id, carteira, FANTASIA, CNPJ_CPF, CLIENTE, CONJUNTO,
                SIT_DOC, DESC_SIT_DOC, NUMERO_BOLETO, NOSSO_NUMERO, DATA_REMISSAO, PONTEIRO,
                DATA_VENCIMENTO, VALOR_ORIGINAL, DATA_BAIXA, VALOR_BAIXA, CRC_CPG,
                atualizado_em_origem, atualizado_em_cache
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(unidade, titulo_movimento_id) DO UPDATE SET
                carteira=excluded.carteira, FANTASIA=excluded.FANTASIA, CNPJ_CPF=excluded.CNPJ_CPF,
                CLIENTE=excluded.CLIENTE, CONJUNTO=excluded.CONJUNTO, SIT_DOC=excluded.SIT_DOC,
                DESC_SIT_DOC=excluded.DESC_SIT_DOC, NUMERO_BOLETO=excluded.NUMERO_BOLETO,
                NOSSO_NUMERO=excluded.NOSSO_NUMERO, DATA_REMISSAO=excluded.DATA_REMISSAO,
                PONTEIRO=excluded.PONTEIRO, DATA_VENCIMENTO=excluded.DATA_VENCIMENTO,
                VALOR_ORIGINAL=excluded.VALOR_ORIGINAL, DATA_BAIXA=excluded.DATA_BAIXA,
                VALOR_BAIXA=excluded.VALOR_BAIXA, CRC_CPG=excluded.CRC_CPG,
                atualizado_em_origem=excluded.atualizado_em_origem,
                atualizado_em_cache=excluded.atualizado_em_cache
        """
        valores = []
        for linha in linhas:
            valores.append((unidade, *[_texto(linha[campo]) for campo in CAMPOS_ORIGEM[:-1]], crc_cpg,
                            _texto(linha["ATUALIZADO_EM_ORIGEM"]), agora))
        with self.conexao:
            if valores:
                self.conexao.executemany(comando, valores)
            self.conexao.execute(
                """
                INSERT INTO sync_estado (unidade, marcador, titulo_movimento_id, ultima_sincronizacao)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(unidade) DO UPDATE SET
                    marcador=excluded.marcador,
                    titulo_movimento_id=excluded.titulo_movimento_id,
                    ultima_sincronizacao=excluded.ultima_sincronizacao
                """,
                (unidade, marcador, titulo_movimento_id, agora),
            )
            self.conexao.execute(
                "INSERT INTO sync_log (ocorrido_em, unidade, status, registros) VALUES (?, ?, 'sucesso', ?)",
                (agora, unidade, len(valores)),
            )

    def ultima_sincronizacao(self) -> datetime | None:
        linha = self.conexao.execute("SELECT MAX(ultima_sincronizacao) AS valor FROM sync_estado").fetchone()
        return datetime.fromisoformat(linha["valor"]) if linha and linha["valor"] else None

    def consultar_recebidos(self, crc_cpg: str, inicio: str, fim_exclusivo: str, bancos: list[str], cnpj_cpf: str | None,
                            carteiras: dict[str, list[str]], unidades: list[str] | None) -> list[sqlite3.Row]:
        codigos = [codigo for banco in bancos for codigo in carteiras[banco.casefold()]]
        filtros = ["CRC_CPG = ?", "DATA_BAIXA >= ?", "DATA_BAIXA < ?", f"carteira IN ({','.join('?' for _ in codigos)})"]
        parametros: list[Any] = [crc_cpg, inicio, fim_exclusivo, *codigos]
        if cnpj_cpf:
            filtros.append("CNPJ_CPF = ?")
            parametros.append(cnpj_cpf)
        if unidades:
            filtros.append(f"unidade IN ({','.join('?' for _ in unidades)})")
            parametros.extend(unidades)
        sql = "SELECT * FROM titulos_movimento WHERE " + " AND ".join(filtros) + " ORDER BY DATA_BAIXA, FANTASIA"
        return self.conexao.execute(sql, parametros).fetchall()
