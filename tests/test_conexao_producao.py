import unittest

from db.configuracao import ErroConfiguracao
from db.conexao_producao import executar_leitura, validar_consulta_somente_leitura


class CursorFalso:
    description = [("codigo",), ("nome",)]

    def __init__(self):
        self.comandos = []
        self.fechado = False

    def execute(self, sql, parametros=None):
        self.comandos.append((sql, parametros))

    def fetchall(self):
        return [(1, "Recebimento")]

    def close(self):
        self.fechado = True


class ConexaoFalsa:
    def __init__(self):
        self.cursor_falso = CursorFalso()
        self.rollback_chamado = False

    def cursor(self):
        return self.cursor_falso

    def rollback(self):
        self.rollback_chamado = True


class ValidacaoConsultaSomenteLeituraTest(unittest.TestCase):
    def test_aceita_select_com_cte_e_ponto_virgula_final(self):
        validar_consulta_somente_leitura(
            "WITH base AS (SELECT 1 AS codigo) SELECT codigo FROM base;"
        )

    def test_aceita_palavra_proibida_em_texto_comentario_ou_identificador(self):
        validar_consulta_somente_leitura(
            "SELECT 'DELETE' AS texto, [INTO] AS identificador -- UPDATE\nFROM dbo.origem"
        )

    def test_nao_ignora_comando_apos_marcador_de_comentario_dentro_de_texto(self):
        with self.assertRaisesRegex(ErroConfiguracao, "unica instrucao"):
            validar_consulta_somente_leitura("SELECT '-- nao e comentario'; SELECT 2")

    def test_rejeita_select_into(self):
        with self.assertRaisesRegex(ErroConfiguracao, "escrita"):
            validar_consulta_somente_leitura("SELECT codigo INTO destino FROM origem")

    def test_rejeita_mais_de_uma_instrucao(self):
        with self.assertRaisesRegex(ErroConfiguracao, "unica instrucao"):
            validar_consulta_somente_leitura("SELECT 1; SELECT 2")

    def test_rejeita_comando_que_nao_seja_leitura(self):
        with self.assertRaisesRegex(ErroConfiguracao, "iniciar com SELECT ou WITH"):
            validar_consulta_somente_leitura("SET NOCOUNT ON")

    def test_executar_leitura_fecha_cursor_e_rollback(self):
        conexao = ConexaoFalsa()

        resultado = executar_leitura(conexao, "SELECT codigo, nome FROM recebimentos", ["2026-09-12"])

        self.assertEqual(resultado, [{"CODIGO": 1, "NOME": "Recebimento"}])
        self.assertTrue(conexao.rollback_chamado)
        self.assertTrue(conexao.cursor_falso.fechado)
        self.assertEqual(conexao.cursor_falso.comandos[1], ("SELECT codigo, nome FROM recebimentos", ["2026-09-12"]))


if __name__ == "__main__":
    unittest.main()
