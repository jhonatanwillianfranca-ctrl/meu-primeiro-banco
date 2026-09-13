import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from db.migrations.m001_nucleo_financeiro import aplicar


RAIZ = Path(__file__).resolve().parents[1]


def criar_staging_ficticio(conexao: sqlite3.Connection) -> None:
    conexao.executescript(
        """
        CREATE TABLE titulos_movimento (
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
        """
    )
    conexao.executemany(
        "INSERT INTO titulos_movimento VALUES (" + ", ".join("?" for _ in range(20)) + ")",
        [
            (
                "UNIDADE_TESTE",
                "TITULO-100",
                "CARTEIRA-NAO-CONTA",
                "EMPRESA TESTE",
                "12345678000199",
                "CLIENTE TESTE 1",
                None,
                None,
                None,
                "BOL-100",
                None,
                None,
                None,
                "2026-10-10",
                "100,00",
                "2026-09-13",
                "100,00",
                "R",
                "2026-09-13T08:00:00",
                "2026-09-13T08:00:00",
            ),
            (
                "UNIDADE_TESTE",
                "TITULO-250",
                "CARTEIRA-NAO-CONTA",
                "EMPRESA TESTE",
                "98765432100",
                "CLIENTE TESTE 2",
                None,
                None,
                None,
                "BOL-250",
                None,
                None,
                None,
                "2026-10-20",
                "250.00",
                None,
                None,
                "R",
                "2026-09-13T08:00:00",
                "2026-09-13T08:00:00",
            ),
        ],
    )
    conexao.commit()


class CargaNucleoFinanceiroTest(unittest.TestCase):
    def setUp(self):
        self.temporario = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporario.cleanup)
        self.database = Path(self.temporario.name) / "financeiro-ficticio.db"
        self.conexao = sqlite3.connect(self.database)
        self.addCleanup(self.conexao.close)
        self.conexao.execute("PRAGMA foreign_keys = ON")
        aplicar(self.conexao)
        criar_staging_ficticio(self.conexao)

    def _executar_script(self):
        return subprocess.run(
            [
                sys.executable,
                str(RAIZ / "db" / "carregar_nucleo_financeiro.py"),
                "--database",
                str(self.database),
            ],
            cwd=RAIZ,
            check=True,
            text=True,
            capture_output=True,
        )

    def test_carga_eh_idempotente_e_nao_altera_staging(self):
        origem_antes = self.conexao.execute(
            "SELECT * FROM titulos_movimento ORDER BY unidade, titulo_movimento_id"
        ).fetchall()

        primeira = self._executar_script()
        segunda = self._executar_script()

        self.assertIn("2 linha(s)", primeira.stdout)
        self.assertIn("2 linha(s)", segunda.stdout)
        self.assertEqual(self.conexao.execute("SELECT COUNT(*) FROM titulo_financeiro").fetchone()[0], 2)
        self.assertEqual(self.conexao.execute("SELECT COUNT(*) FROM parcela_financeira").fetchone()[0], 2)
        self.assertEqual(self.conexao.execute("SELECT COUNT(*) FROM liquidacao_financeira").fetchone()[0], 1)
        self.assertEqual(
            self.conexao.execute("SELECT * FROM titulos_movimento ORDER BY unidade, titulo_movimento_id").fetchall(),
            origem_antes,
        )

    def test_valores_e_limites_documentados_sao_preservados(self):
        self._executar_script()

        valor_origem = self.conexao.execute(
            "SELECT SUM(CAST(REPLACE(VALOR_ORIGINAL, ',', '.') AS REAL) * 100) FROM titulos_movimento"
        ).fetchone()[0]
        valor_titulos = self.conexao.execute(
            "SELECT SUM(valor_original_centavos) FROM titulo_financeiro"
        ).fetchone()[0]
        self.assertEqual(int(valor_origem), valor_titulos)
        self.assertEqual(
            self.conexao.execute("SELECT SUM(valor_principal_centavos) FROM liquidacao_financeira").fetchone()[0],
            10000,
        )
        self.assertEqual(self.conexao.execute("SELECT COUNT(*) FROM conta_financeira").fetchone()[0], 0)
        self.assertEqual(self.conexao.execute("SELECT COUNT(*) FROM movimentacao_bancaria").fetchone()[0], 0)
        self.assertEqual(self.conexao.execute("SELECT COUNT(*) FROM conciliacao_bancaria").fetchone()[0], 0)
        self.assertEqual(
            self.conexao.execute("SELECT COUNT(*) FROM pessoa WHERE papel_financeiro = 'FORNECEDOR'").fetchone()[0],
            0,
        )
        self.assertEqual(
            self.conexao.execute("SELECT COUNT(*) FROM pessoa WHERE papel_financeiro = 'CLIENTE'").fetchone()[0],
            2,
        )


if __name__ == "__main__":
    unittest.main()
