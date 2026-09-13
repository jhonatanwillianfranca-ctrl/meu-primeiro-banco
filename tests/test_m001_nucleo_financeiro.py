import os
import sqlite3
import unittest
from pathlib import Path

from db.migrations.m001_nucleo_financeiro import MIGRATION_ID, aplicar


TABELAS_FINANCEIRAS = {
    "empresa",
    "pessoa",
    "conta_financeira",
    "categoria_financeira",
    "titulo_financeiro",
    "parcela_financeira",
    "liquidacao_financeira",
    "movimentacao_bancaria",
    "conciliacao_bancaria",
    "conciliacao_item",
    "previsao_fluxo_manual",
}


class MigrationNucleoFinanceiroTest(unittest.TestCase):
    def setUp(self):
        self.conexao = sqlite3.connect(":memory:")
        self.conexao.execute("PRAGMA foreign_keys = ON")

    def tearDown(self):
        self.conexao.close()

    def test_cria_todas_as_tabelas_e_registra_a_versao(self):
        self.assertTrue(aplicar(self.conexao))

        tabelas = {
            linha[0]
            for linha in self.conexao.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
        }
        self.assertTrue(TABELAS_FINANCEIRAS.issubset(tabelas))
        self.assertIn("schema_migrations", tabelas)
        self.assertEqual(
            self.conexao.execute("SELECT id FROM schema_migrations").fetchone()[0], MIGRATION_ID
        )

    def test_mantem_staging_tecnico_inalterado_e_eh_idempotente(self):
        self.conexao.execute(
            "CREATE TABLE titulos_movimento (unidade TEXT NOT NULL, titulo_movimento_id TEXT NOT NULL)"
        )
        self.assertTrue(aplicar(self.conexao))
        self.assertFalse(aplicar(self.conexao))

        colunas_staging = [
            linha[1] for linha in self.conexao.execute("PRAGMA table_info(titulos_movimento)")
        ]
        self.assertEqual(colunas_staging, ["unidade", "titulo_movimento_id"])

    def test_rastreabilidade_e_chave_estrangeira_sao_exigidas(self):
        aplicar(self.conexao)
        with self.assertRaises(sqlite3.IntegrityError):
            self.conexao.execute(
                """
                INSERT INTO conta_financeira (
                    id, empresa_id, tipo, origem, regra_aplicada
                ) VALUES ('conta-1', 'empresa-inexistente', 'BANCARIA', 'MANUAL', 'teste')
                """
            )

        colunas = {
            linha[1]
            for linha in self.conexao.execute("PRAGMA table_info(titulo_financeiro)")
        }
        self.assertTrue({"origem", "identificador_externo", "data_carga", "regra_aplicada"}.issubset(colunas))

    @unittest.skipUnless(
        os.getenv("MEU_PRIMEIRO_BANCO_TEST_DATABASE"),
        "Defina MEU_PRIMEIRO_BANCO_TEST_DATABASE para validar um SQLite persistente em modo leitura.",
    )
    def test_schema_do_arquivo_sqlite_indicado(self):
        caminho = Path(os.environ["MEU_PRIMEIRO_BANCO_TEST_DATABASE"]).resolve()
        self.assertTrue(caminho.is_file(), f"SQLite persistente não encontrado: {caminho}")

        conexao = sqlite3.connect(f"file:{caminho.as_posix()}?mode=ro", uri=True)
        try:
            tabelas = {
                linha[0]
                for linha in conexao.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
            }
            self.assertTrue(TABELAS_FINANCEIRAS.issubset(tabelas))
            self.assertIn(MIGRATION_ID, {linha[0] for linha in conexao.execute("SELECT id FROM schema_migrations")})

            for tabela in TABELAS_FINANCEIRAS:
                colunas = {linha[1] for linha in conexao.execute(f"PRAGMA table_info({tabela})")}
                self.assertTrue(
                    {"origem", "identificador_externo", "data_carga", "regra_aplicada"}.issubset(colunas),
                    f"Rastreabilidade ausente em {tabela}",
                )
                indices = conexao.execute(f"PRAGMA index_list({tabela})").fetchall()
                self.assertTrue(indices, f"Índice ausente em {tabela}")

            sql_titulo = conexao.execute(
                "SELECT sql FROM sqlite_master WHERE type = 'table' AND name = 'titulo_financeiro'"
            ).fetchone()[0]
            self.assertIn("CHECK", sql_titulo.upper())
            self.assertTrue(conexao.execute("PRAGMA foreign_key_list(titulo_financeiro)").fetchall())
        finally:
            conexao.close()


if __name__ == "__main__":
    unittest.main()
