/*
   CONTRATO DE EXTRACAO - BOLETOS RECEBIDOS

   Esta consulta e um contrato para a versao operacional local, que deve ficar
   em local/operacional/relatorios_recebidos/sql/. Nao substitua campos ou
   relacionamentos por semelhanca de nome: valide-os no ambiente autorizado.

   Tokens obrigatorios, cada um uma unica vez:
     {{CRC_CPG}}
     {{DATA_INICIO}}
     {{DATA_FIM_EXCLUSIVO}}
     {{CARTEIRAS}}

   Colunas obrigatorias na saida, com estes aliases:
     TITULO_MOVIMENTO_ID, CARTEIRA, FANTASIA, CNPJ_CPF, CLIENTE, CONJUNTO,
     SIT_DOC, DESC_SIT_DOC, NUMERO_BOLETO, NOSSO_NUMERO, DATA_REMISSAO,
     PONTEIRO, DATA_VENCIMENTO, VALOR_ORIGINAL, DATA_BAIXA, VALOR_BAIXA,
     ATUALIZADO_EM_ORIGEM.

   A consulta operacional deve ser somente leitura e retornar uma linha por
   titulo/baixa. O sincronizador substitui os tokens por parametros ODBC.
*/

-- A definicao concreta permanece local ate que tabelas, carteiras e CRC_CPG
-- de recebimento sejam homologados para cada ambiente.
