from __future__ import annotations

import argparse
import re
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from db.cache_local import CacheLocal
from db.conexao_producao import abrir_conexao, executar_leitura, validar_consulta_somente_leitura
from db.configuracao import (
    ErroConfiguracao,
    caminho_no_projeto,
    carregar_ambientes,
    carregar_carteiras_entrada,
    carregar_recebidos,
    carregar_sync,
    ler_consulta_operacional,
)


TOKENS = ("{{CRC_CPG}}", "{{DATA_INICIO}}", "{{DATA_FIM_EXCLUSIVO}}", "{{CARTEIRAS}}")


def renderizar_consulta(consulta: str, crc_cpg: str, inicio: datetime, fim: datetime,
                         carteiras: list[str]) -> tuple[str, list[Any]]:
    valores: dict[str, tuple[str, list[Any]]] = {
        "{{CRC_CPG}}": ("?", [crc_cpg]),
        "{{DATA_INICIO}}": ("?", [inicio]),
        "{{DATA_FIM_EXCLUSIVO}}": ("?", [fim]),
        "{{CARTEIRAS}}": (", ".join("?" for _ in carteiras), list(carteiras)),
    }
    if not carteiras:
        raise ErroConfiguracao("A sincronizacao exige ao menos uma carteira de entrada homologada.")

    parametros: list[Any] = []
    partes: list[str] = []
    anterior = 0
    padrao = re.compile("|".join(re.escape(token) for token in TOKENS))
    for ocorrencia in padrao.finditer(consulta):
        partes.append(consulta[anterior:ocorrencia.start()])
        substituto, valores_token = valores[ocorrencia.group()]
        partes.append(substituto)
        parametros.extend(valores_token)
        anterior = ocorrencia.end()
    partes.append(consulta[anterior:])
    resultado = "".join(partes)
    if "{{" in resultado or "}}" in resultado:
        raise ErroConfiguracao("A consulta contem token nao reconhecido.")
    validar_consulta_somente_leitura(resultado)
    return resultado, parametros


def _para_datetime(valor: str) -> datetime:
    try:
        return datetime.fromisoformat(valor)
    except ValueError as erro:
        raise ErroConfiguracao(f"Data invalida na configuracao ou no estado local: {valor}.") from erro


def _maior_marcador(linhas: list[dict[str, Any]]) -> tuple[str | None, str | None]:
    if not linhas:
        return None, None
    melhor = max(
        (
            str(linha["ATUALIZADO_EM_ORIGEM"]),
            str(linha["TITULO_MOVIMENTO_ID"]),
        )
        for linha in linhas
    )
    return melhor


def executar_ciclo(dry_run: bool = False, unidades_solicitadas: list[str] | None = None) -> bool:
    sync = carregar_sync()
    recebidos = carregar_recebidos()
    ambientes = carregar_ambientes()
    unidades = unidades_solicitadas or [str(unidade) for unidade in sync["unidades"]]
    desconhecidas = [unidade for unidade in unidades if unidade not in ambientes]
    if desconhecidas:
        raise ErroConfiguracao(f"Unidade(s) sem ambiente correspondente: {', '.join(desconhecidas)}.")

    carteiras_por_banco = carregar_carteiras_entrada(["sicoob", "sicredi"])
    carteiras = [codigo for valores in carteiras_por_banco.values() for codigo in valores]
    consulta = ler_consulta_operacional(caminho_no_projeto(str(sync["consulta_extracao_path"])))
    cache_path = caminho_no_projeto(str(sync["cache_path"]))
    inicio_padrao = _para_datetime(str(recebidos["data_inicial_sincronizacao"]))
    sobreposicao = timedelta(seconds=int(sync.get("sobreposicao_segundos", 300)))

    if dry_run:
        exemplo, parametros = renderizar_consulta(consulta, str(recebidos["crc_cpg_recebimento"]), inicio_padrao,
                                                   datetime.now(), carteiras)
        print(f"Validacao concluida: {len(unidades)} unidade(s), {len(carteiras)} carteira(s), {len(parametros)} parametro(s).")
        print(f"Consulta somente leitura validada: {exemplo.splitlines()[0] if exemplo.splitlines() else 'SELECT'}")
        return True

    cache = CacheLocal(cache_path)
    sucessos = 0
    try:
        for unidade in unidades:
            estado = cache.estado(unidade)
            inicio = inicio_padrao
            if estado and estado.get("marcador"):
                inicio = _para_datetime(estado["marcador"]) - sobreposicao
            fim = datetime.now()
            try:
                sql, parametros = renderizar_consulta(
                    consulta, str(recebidos["crc_cpg_recebimento"]), inicio, fim, carteiras
                )
                conexao = abrir_conexao(ambientes[unidade])
                try:
                    linhas = executar_leitura(conexao, sql, parametros)
                finally:
                    conexao.close()
                marcador, titulo_id = _maior_marcador(linhas)
                if marcador is None and estado:
                    marcador, titulo_id = estado.get("marcador"), estado.get("titulo_movimento_id")
                cache.atualizar(unidade, str(recebidos["crc_cpg_recebimento"]), linhas, marcador, titulo_id)
                print(f"{unidade}: {len(linhas)} registro(s) inserido(s)/atualizado(s).")
                sucessos += 1
            except Exception as erro:  # Cada unidade falha de modo independente.
                cache.registrar_log(unidade, "erro", detalhe=str(erro))
                print(f"{unidade}: falha registrada; sera tentada novamente no proximo ciclo. {erro}", file=sys.stderr)
    finally:
        cache.close()
    return sucessos > 0


def main() -> None:
    parser = argparse.ArgumentParser(description="Sincroniza recebimentos para o cache SQLite local.")
    parser.add_argument("--uma-vez", action="store_true", help="Executa apenas um ciclo de sincronizacao.")
    parser.add_argument("--dry-run", action="store_true", help="Valida configuracao e consulta sem conectar ou gravar.")
    parser.add_argument("--unidade", action="append", dest="unidades", help="Restringe o ciclo a uma unidade configurada.")
    args = parser.parse_args()

    try:
        if args.dry_run:
            executar_ciclo(dry_run=True, unidades_solicitadas=args.unidades)
            return
        if args.uma_vez:
            if not executar_ciclo(unidades_solicitadas=args.unidades):
                raise SystemExit(1)
            return
        intervalo = int(carregar_sync()["intervalo_segundos"])
        while True:
            executar_ciclo(unidades_solicitadas=args.unidades)
            time.sleep(intervalo)
    except ErroConfiguracao as erro:
        print(f"Configuracao pendente: {erro}", file=sys.stderr)
        raise SystemExit(2) from erro


if __name__ == "__main__":
    main()
