"""Migration 001: núcleo financeiro separado do staging técnico existente.

Esta migration não lê configuração, não abre conexões externas e só opera sobre
a conexão SQLite recebida pelo chamador.
"""

from __future__ import annotations

import sqlite3


MIGRATION_ID = "001_nucleo_financeiro"

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS empresa (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    codigo_origem TEXT,
    razao_social TEXT NOT NULL,
    nome_fantasia TEXT,
    ativa INTEGER NOT NULL DEFAULT 1 CHECK (ativa IN (0, 1)),
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_empresa_origem_externo
    ON empresa (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE TABLE IF NOT EXISTS pessoa (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    tipo_pessoa TEXT NOT NULL CHECK (tipo_pessoa IN ('FISICA', 'JURIDICA', 'NAO_INFORMADA')),
    papel_financeiro TEXT NOT NULL CHECK (papel_financeiro IN ('CLIENTE', 'FORNECEDOR', 'AMBOS', 'OUTRO')),
    nome TEXT NOT NULL,
    documento TEXT,
    ativa INTEGER NOT NULL DEFAULT 1 CHECK (ativa IN (0, 1)),
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_pessoa_origem_externo
    ON pessoa (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_pessoa_documento ON pessoa (documento);

CREATE TABLE IF NOT EXISTS conta_financeira (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    empresa_id TEXT NOT NULL REFERENCES empresa(id) ON DELETE RESTRICT,
    tipo TEXT NOT NULL CHECK (tipo IN ('BANCARIA', 'CAIXA', 'OUTRA')),
    instituicao TEXT,
    identificacao_mascarada TEXT,
    ativa INTEGER NOT NULL DEFAULT 1 CHECK (ativa IN (0, 1)),
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_conta_financeira_origem_externo
    ON conta_financeira (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_conta_financeira_empresa ON conta_financeira (empresa_id, ativa);

CREATE TABLE IF NOT EXISTS categoria_financeira (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    codigo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    natureza TEXT NOT NULL CHECK (natureza IN ('ENTRADA', 'SAIDA', 'AMBAS')),
    ativa INTEGER NOT NULL DEFAULT 1 CHECK (ativa IN (0, 1)),
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL,
    UNIQUE (origem, codigo)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_categoria_financeira_origem_externo
    ON categoria_financeira (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE TABLE IF NOT EXISTS titulo_financeiro (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    empresa_id TEXT NOT NULL REFERENCES empresa(id) ON DELETE RESTRICT,
    pessoa_id TEXT REFERENCES pessoa(id) ON DELETE RESTRICT,
    categoria_id TEXT REFERENCES categoria_financeira(id) ON DELETE RESTRICT,
    natureza TEXT NOT NULL CHECK (natureza IN ('PAGAR', 'RECEBER')),
    documento TEXT,
    data_emissao TEXT,
    competencia TEXT,
    moeda_codigo TEXT NOT NULL CHECK (length(moeda_codigo) = 3),
    valor_original_centavos INTEGER NOT NULL CHECK (valor_original_centavos >= 0),
    situacao TEXT NOT NULL CHECK (situacao IN ('ABERTO', 'PARCIAL', 'LIQUIDADO', 'CANCELADO')),
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_titulo_financeiro_origem_externo
    ON titulo_financeiro (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_titulo_financeiro_empresa_situacao
    ON titulo_financeiro (empresa_id, natureza, situacao);

CREATE INDEX IF NOT EXISTS ix_titulo_financeiro_pessoa ON titulo_financeiro (pessoa_id);

CREATE TABLE IF NOT EXISTS parcela_financeira (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    titulo_id TEXT NOT NULL REFERENCES titulo_financeiro(id) ON DELETE RESTRICT,
    numero_parcela INTEGER NOT NULL CHECK (numero_parcela > 0),
    data_vencimento TEXT NOT NULL,
    valor_previsto_centavos INTEGER NOT NULL CHECK (valor_previsto_centavos >= 0),
    situacao TEXT NOT NULL CHECK (situacao IN ('ABERTA', 'PARCIAL', 'LIQUIDADA', 'CANCELADA')),
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL,
    UNIQUE (titulo_id, numero_parcela)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_parcela_financeira_origem_externo
    ON parcela_financeira (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_parcela_financeira_vencimento
    ON parcela_financeira (data_vencimento, situacao);

CREATE TABLE IF NOT EXISTS liquidacao_financeira (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    parcela_id TEXT NOT NULL REFERENCES parcela_financeira(id) ON DELETE RESTRICT,
    tipo_evento TEXT NOT NULL CHECK (tipo_evento IN ('BAIXA', 'ESTORNO')),
    data_liquidacao TEXT NOT NULL,
    valor_principal_centavos INTEGER NOT NULL CHECK (valor_principal_centavos >= 0),
    valor_juros_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_juros_centavos >= 0),
    valor_desconto_centavos INTEGER NOT NULL DEFAULT 0 CHECK (valor_desconto_centavos >= 0),
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_liquidacao_financeira_origem_externo
    ON liquidacao_financeira (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_liquidacao_financeira_parcela_data
    ON liquidacao_financeira (parcela_id, data_liquidacao);

CREATE TABLE IF NOT EXISTS movimentacao_bancaria (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    conta_financeira_id TEXT NOT NULL REFERENCES conta_financeira(id) ON DELETE RESTRICT,
    data_movimento TEXT NOT NULL,
    natureza TEXT NOT NULL CHECK (natureza IN ('ENTRADA', 'SAIDA')),
    moeda_codigo TEXT NOT NULL CHECK (length(moeda_codigo) = 3),
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos <> 0),
    descricao TEXT,
    origem_extrato TEXT,
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_movimentacao_bancaria_origem_externo
    ON movimentacao_bancaria (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_movimentacao_bancaria_conta_data
    ON movimentacao_bancaria (conta_financeira_id, data_movimento);

CREATE TABLE IF NOT EXISTS conciliacao_bancaria (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    empresa_id TEXT NOT NULL REFERENCES empresa(id) ON DELETE RESTRICT,
    data_conciliacao TEXT NOT NULL,
    situacao TEXT NOT NULL CHECK (situacao IN ('PENDENTE', 'CONCILIADA', 'CANCELADA')),
    responsavel TEXT,
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_conciliacao_bancaria_origem_externo
    ON conciliacao_bancaria (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_conciliacao_bancaria_empresa_data
    ON conciliacao_bancaria (empresa_id, data_conciliacao, situacao);

CREATE TABLE IF NOT EXISTS conciliacao_item (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    conciliacao_id TEXT NOT NULL REFERENCES conciliacao_bancaria(id) ON DELETE RESTRICT,
    movimentacao_bancaria_id TEXT NOT NULL REFERENCES movimentacao_bancaria(id) ON DELETE RESTRICT,
    liquidacao_financeira_id TEXT NOT NULL REFERENCES liquidacao_financeira(id) ON DELETE RESTRICT,
    valor_conciliado_centavos INTEGER NOT NULL CHECK (valor_conciliado_centavos > 0),
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL,
    UNIQUE (conciliacao_id, movimentacao_bancaria_id, liquidacao_financeira_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_conciliacao_item_origem_externo
    ON conciliacao_item (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_conciliacao_item_movimento
    ON conciliacao_item (movimentacao_bancaria_id);

CREATE INDEX IF NOT EXISTS ix_conciliacao_item_liquidacao
    ON conciliacao_item (liquidacao_financeira_id);

CREATE TABLE IF NOT EXISTS previsao_fluxo_manual (
    id TEXT PRIMARY KEY NOT NULL CHECK (length(trim(id)) > 0),
    empresa_id TEXT NOT NULL REFERENCES empresa(id) ON DELETE RESTRICT,
    conta_financeira_id TEXT REFERENCES conta_financeira(id) ON DELETE RESTRICT,
    categoria_id TEXT NOT NULL REFERENCES categoria_financeira(id) ON DELETE RESTRICT,
    data_prevista TEXT NOT NULL,
    natureza TEXT NOT NULL CHECK (natureza IN ('ENTRADA', 'SAIDA')),
    moeda_codigo TEXT NOT NULL CHECK (length(moeda_codigo) = 3),
    valor_centavos INTEGER NOT NULL CHECK (valor_centavos > 0),
    situacao TEXT NOT NULL CHECK (situacao IN ('PREVISTA', 'REALIZADA', 'CANCELADA')),
    descricao TEXT,
    origem TEXT NOT NULL,
    identificador_externo TEXT,
    data_carga TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    regra_aplicada TEXT NOT NULL
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_previsao_fluxo_manual_origem_externo
    ON previsao_fluxo_manual (origem, identificador_externo)
    WHERE identificador_externo IS NOT NULL;

CREATE INDEX IF NOT EXISTS ix_previsao_fluxo_manual_empresa_data
    ON previsao_fluxo_manual (empresa_id, data_prevista, situacao);
"""


def aplicar(conexao: sqlite3.Connection) -> bool:
    """Aplica a migration uma única vez e retorna se houve alteração."""
    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            id TEXT PRIMARY KEY NOT NULL,
            aplicado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    ja_aplicada = conexao.execute(
        "SELECT 1 FROM schema_migrations WHERE id = ?", (MIGRATION_ID,)
    ).fetchone()
    if ja_aplicada:
        return False

    conexao.executescript(SCHEMA_SQL)
    conexao.execute("INSERT INTO schema_migrations (id) VALUES (?)", (MIGRATION_ID,))
    conexao.commit()
    return True
