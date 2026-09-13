"""Carga local do staging titulos_movimento para o núcleo financeiro.

Não abre conexão externa, não lê configurações ou credenciais e nunca altera o
staging técnico. A origem é tratada como recebimentos: CLIENTE só pode gerar
uma pessoa com papel CLIENTE, CARTEIRA não gera conta financeira e DATA_BAIXA
gera baixa financeira, nunca conciliação bancária.
"""

from __future__ import annotations

import argparse
import hashlib
import sqlite3
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from db.cache_local import CAMPOS_ORIGEM


ORIGEM_STAGING = "titulos_movimento"
MOEDA_PADRAO = "BRL"


class ErroCargaFinanceira(RuntimeError):
    """Indica staging ausente ou dado incompatível com a carga local."""


@dataclass(frozen=True)
class ResultadoCarga:
    linhas_lidas: int
    titulos_processados: int
    parcelas_processadas: int
    liquidacoes_processadas: int


def _id_deterministico(tipo: str, *partes: object) -> str:
    texto = "|".join(str(parte).strip() for parte in partes)
    resumo = hashlib.sha256(texto.encode("utf-8")).hexdigest()[:24]
    return f"{tipo}-{resumo}"


def _texto(valor: Any) -> str | None:
    if valor is None:
        return None
    texto = str(valor).strip()
    return texto or None


def _centavos(valor: Any, campo: str) -> int | None:
    texto = _texto(valor)
    if texto is None:
        return None
    texto = texto.replace("R$", "").replace(" ", "")
    if "," in texto:
        texto = texto.replace(".", "").replace(",", ".")
    try:
        decimal = Decimal(texto)
    except InvalidOperation as erro:
        raise ErroCargaFinanceira(f"Valor inválido em {campo}: {valor!r}") from erro
    return int((decimal * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _tipo_pessoa(documento: str | None) -> str:
    digitos = "".join(caractere for caractere in documento or "" if caractere.isdigit())
    if len(digitos) == 11:
        return "FISICA"
    if len(digitos) == 14:
        return "JURIDICA"
    return "NAO_INFORMADA"


def _upsert_por_id(conexao: sqlite3.Connection, tabela: str, valores: dict[str, Any]) -> None:
    colunas = list(valores)
    atualizacoes = ", ".join(f"{coluna} = excluded.{coluna}" for coluna in colunas if coluna != "id")
    sql = (
        f"INSERT INTO {tabela} ({', '.join(colunas)}) VALUES ({', '.join('?' for _ in colunas)}) "
        f"ON CONFLICT(id) DO UPDATE SET {atualizacoes}"
    )
    try:
        conexao.execute(sql, [valores[coluna] for coluna in colunas])
    except sqlite3.IntegrityError as erro:
        raise ErroCargaFinanceira(
            f"Não foi possível carregar {tabela} com identificador externo "
            f"{valores.get('identificador_externo')!r}: {erro}"
        ) from erro


def _validar_staging(conexao: sqlite3.Connection) -> None:
    tabelas = {linha[0] for linha in conexao.execute("SELECT name FROM sqlite_master")}
    if "titulos_movimento" not in tabelas:
        raise ErroCargaFinanceira("Staging titulos_movimento não existe neste SQLite.")
    colunas = {linha[1].upper() for linha in conexao.execute("PRAGMA table_info(titulos_movimento)")}
    faltantes = set(CAMPOS_ORIGEM) - colunas
    if faltantes:
        raise ErroCargaFinanceira(
            "Staging titulos_movimento sem colunas obrigatórias: " + ", ".join(sorted(faltantes))
        )


def carregar_nucleo_financeiro(conexao: sqlite3.Connection) -> ResultadoCarga:
    """Lê o staging e grava somente entidades do núcleo financeiro."""
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    _validar_staging(conexao)
    linhas = conexao.execute("SELECT * FROM titulos_movimento ORDER BY unidade, titulo_movimento_id").fetchall()
    carregado_em = datetime.now(timezone.utc).isoformat(timespec="seconds")
    liquidacoes = 0

    with conexao:
        for linha in linhas:
            unidade = _texto(linha["unidade"])
            titulo_externo = _texto(linha["TITULO_MOVIMENTO_ID"])
            if not unidade or not titulo_externo:
                raise ErroCargaFinanceira("Cada linha do staging exige unidade e TITULO_MOVIMENTO_ID.")

            empresa_id = _id_deterministico("empresa", ORIGEM_STAGING, unidade)
            _upsert_por_id(
                conexao,
                "empresa",
                {
                    "id": empresa_id,
                    "codigo_origem": unidade,
                    "razao_social": _texto(linha["FANTASIA"]) or unidade,
                    "nome_fantasia": _texto(linha["FANTASIA"]),
                    "ativa": 1,
                    "origem": ORIGEM_STAGING,
                    "identificador_externo": unidade,
                    "data_carga": carregado_em,
                    "regra_aplicada": "unidade como referência de empresa; homologação cadastral pendente",
                },
            )

            cliente = _texto(linha["CLIENTE"])
            documento = _texto(linha["CNPJ_CPF"])
            pessoa_id: str | None = None
            if cliente:
                pessoa_id = _id_deterministico("pessoa", ORIGEM_STAGING, unidade, documento or cliente)
                _upsert_por_id(
                    conexao,
                    "pessoa",
                    {
                        "id": pessoa_id,
                        "tipo_pessoa": _tipo_pessoa(documento),
                        "papel_financeiro": "CLIENTE",
                        "nome": cliente,
                        "documento": documento,
                        "ativa": 1,
                        "origem": ORIGEM_STAGING,
                        "identificador_externo": documento or f"{unidade}:{cliente}",
                        "data_carga": carregado_em,
                        "regra_aplicada": "CLIENTE como contraparte cliente; fornecedor não é inferido",
                    },
                )

            valor_original = _centavos(linha["VALOR_ORIGINAL"], "VALOR_ORIGINAL")
            if valor_original is None or valor_original < 0:
                raise ErroCargaFinanceira(f"VALOR_ORIGINAL obrigatório e não negativo para {titulo_externo!r}.")
            valor_baixa = _centavos(linha["VALOR_BAIXA"], "VALOR_BAIXA")
            data_baixa = _texto(linha["DATA_BAIXA"])
            tem_baixa = bool(data_baixa and valor_baixa not in (None, 0))
            situacao_titulo = "LIQUIDADO" if tem_baixa and valor_baixa >= valor_original else "PARCIAL" if tem_baixa else "ABERTO"

            titulo_id = _id_deterministico("titulo", ORIGEM_STAGING, unidade, titulo_externo)
            _upsert_por_id(
                conexao,
                "titulo_financeiro",
                {
                    "id": titulo_id,
                    "empresa_id": empresa_id,
                    "pessoa_id": pessoa_id,
                    "categoria_id": None,
                    "natureza": "RECEBER",
                    "documento": _texto(linha["NUMERO_BOLETO"]) or _texto(linha["NOSSO_NUMERO"]),
                    "data_emissao": None,
                    "competencia": None,
                    "moeda_codigo": MOEDA_PADRAO,
                    "valor_original_centavos": valor_original,
                    "situacao": situacao_titulo,
                    "origem": ORIGEM_STAGING,
                    "identificador_externo": titulo_externo,
                    "data_carga": carregado_em,
                    "regra_aplicada": "título recebido; carteira e categoria não são inferidas",
                },
            )

            parcela_id = _id_deterministico("parcela", ORIGEM_STAGING, unidade, titulo_externo)
            _upsert_por_id(
                conexao,
                "parcela_financeira",
                {
                    "id": parcela_id,
                    "titulo_id": titulo_id,
                    "numero_parcela": 1,
                    "data_vencimento": _texto(linha["DATA_VENCIMENTO"]) or _texto(linha["DATA_REMISSAO"]) or "1900-01-01",
                    "valor_previsto_centavos": valor_original,
                    "situacao": "LIQUIDADA" if situacao_titulo == "LIQUIDADO" else "PARCIAL" if situacao_titulo == "PARCIAL" else "ABERTA",
                    "origem": ORIGEM_STAGING,
                    "identificador_externo": titulo_externo,
                    "data_carga": carregado_em,
                    "regra_aplicada": "uma parcela por título; parcelamento de origem não informado",
                },
            )

            if tem_baixa:
                liquidacoes += 1
                _upsert_por_id(
                    conexao,
                    "liquidacao_financeira",
                    {
                        "id": _id_deterministico("liquidacao", ORIGEM_STAGING, unidade, titulo_externo),
                        "parcela_id": parcela_id,
                        "tipo_evento": "BAIXA",
                        "data_liquidacao": data_baixa,
                        "valor_principal_centavos": valor_baixa,
                        "valor_juros_centavos": 0,
                        "valor_desconto_centavos": 0,
                        "origem": ORIGEM_STAGING,
                        "identificador_externo": titulo_externo,
                        "data_carga": carregado_em,
                        "regra_aplicada": "DATA_BAIXA e VALOR_BAIXA como baixa; conciliação bancária não é inferida",
                    },
                )

    return ResultadoCarga(len(linhas), len(linhas), len(linhas), liquidacoes)


def main() -> None:
    parser = argparse.ArgumentParser(description="Carrega o núcleo financeiro a partir de titulos_movimento local.")
    parser.add_argument("--database", required=True, type=Path, help="SQLite existente com staging técnico.")
    args = parser.parse_args()
    if not args.database.is_file():
        parser.error(f"SQLite não encontrado: {args.database}")

    conexao = sqlite3.connect(args.database)
    try:
        resultado = carregar_nucleo_financeiro(conexao)
    finally:
        conexao.close()
    print(
        "Carga concluída: "
        f"{resultado.linhas_lidas} linha(s), {resultado.titulos_processados} título(s), "
        f"{resultado.parcelas_processadas} parcela(s), {resultado.liquidacoes_processadas} liquidação(ões)."
    )


if __name__ == "__main__":
    main()
