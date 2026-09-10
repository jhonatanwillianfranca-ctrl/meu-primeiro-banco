from __future__ import annotations

import json
from pathlib import Path
from typing import Any


RAIZ_PROJETO = Path(__file__).resolve().parents[1]
CONFIG_DIR = RAIZ_PROJETO / "config"


class ErroConfiguracao(RuntimeError):
    """Indica configuracao local ausente, incompleta ou nao homologada."""


def caminho_no_projeto(valor: str) -> Path:
    caminho = Path(valor)
    return caminho if caminho.is_absolute() else RAIZ_PROJETO / caminho


def ler_json_local(nome: str) -> dict[str, Any]:
    caminho = CONFIG_DIR / nome
    if not caminho.exists():
        exemplo = caminho.with_name(caminho.name.replace(".local.json", ".example.json"))
        raise ErroConfiguracao(
            f"Arquivo local ausente: {caminho}. "
            f"Use {exemplo.name} como modelo, sem publicar dados reais."
        )
    try:
        dados = json.loads(caminho.read_text(encoding="utf-8"))
    except json.JSONDecodeError as erro:
        raise ErroConfiguracao(f"JSON invalido em {caminho}: {erro}") from erro
    if not isinstance(dados, dict):
        raise ErroConfiguracao(f"{caminho} deve conter um objeto JSON.")
    return dados


def carregar_ambientes() -> dict[str, dict[str, Any]]:
    dados = ler_json_local("ambientes.local.json")
    ambientes = dados.get("ambientes")
    if not isinstance(ambientes, list) or not ambientes:
        raise ErroConfiguracao("ambientes.local.json precisa conter uma lista nao vazia em 'ambientes'.")

    resultado: dict[str, dict[str, Any]] = {}
    for ambiente in ambientes:
        if not isinstance(ambiente, dict) or not ambiente.get("nome"):
            raise ErroConfiguracao("Cada ambiente precisa ter ao menos o campo 'nome'.")
        nome = str(ambiente["nome"])
        if nome in resultado:
            raise ErroConfiguracao(f"Ambiente duplicado: {nome}.")
        resultado[nome] = ambiente
    return resultado


def carregar_carteiras_entrada(bancos: list[str]) -> dict[str, list[str]]:
    dados = ler_json_local("carteiras.local.json")
    resultado: dict[str, list[str]] = {}
    for banco in bancos:
        bloco = dados.get(banco.casefold())
        entrada = bloco.get("entrada") if isinstance(bloco, dict) else None
        carteiras = entrada.get("carteiras") if isinstance(entrada, dict) else None
        if not isinstance(carteiras, list) or not carteiras:
            raise ErroConfiguracao(
                f"Defina ao menos uma carteira homologada em '{banco}.entrada.carteiras'."
            )
        resultado[banco.casefold()] = [str(carteira) for carteira in carteiras]
    return resultado


def carregar_recebidos() -> dict[str, Any]:
    dados = ler_json_local("recebidos.local.json")
    crc_cpg = str(dados.get("crc_cpg_recebimento", "")).strip()
    if not crc_cpg or "CONFIRMAR" in crc_cpg.upper():
        raise ErroConfiguracao("Informe o CRC_CPG de recebimento ja homologado em recebidos.local.json.")
    if not dados.get("data_inicial_sincronizacao"):
        raise ErroConfiguracao("Informe data_inicial_sincronizacao em recebidos.local.json.")
    return dados


def carregar_sync() -> dict[str, Any]:
    dados = ler_json_local("sync.local.json")
    obrigatorios = ("intervalo_segundos", "cache_path", "consulta_extracao_path", "unidades")
    ausentes = [campo for campo in obrigatorios if not dados.get(campo)]
    if ausentes:
        raise ErroConfiguracao(f"Campos obrigatorios ausentes em sync.local.json: {', '.join(ausentes)}.")
    if not isinstance(dados["unidades"], list) or not dados["unidades"]:
        raise ErroConfiguracao("'unidades' deve ser uma lista nao vazia.")
    return dados


def ler_consulta_operacional(caminho: Path) -> str:
    if not caminho.exists():
        raise ErroConfiguracao(f"Consulta operacional ausente: {caminho}.")
    consulta = caminho.read_text(encoding="utf-8")
    obrigatorios = ("{{CRC_CPG}}", "{{DATA_INICIO}}", "{{DATA_FIM_EXCLUSIVO}}", "{{CARTEIRAS}}")
    for token in obrigatorios:
        if consulta.count(token) != 1:
            raise ErroConfiguracao(f"A consulta deve conter o token {token} exatamente uma vez.")
    return consulta
