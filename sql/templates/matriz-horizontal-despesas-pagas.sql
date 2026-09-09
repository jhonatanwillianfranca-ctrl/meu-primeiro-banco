/*
   MODELO PÚBLICO — MATRIZ HORIZONTAL DE DESPESAS PAGAS
   Preencha empresa, período e Sit.Doc somente na configuração local.
   Esta consulta deve ser validada em ambiente autorizado antes de produção.
*/

USE [SEU_BANCO];
GO

DECLARE @DataInicial date = '20260101';
DECLARE @DataFinalExclusiva date = '20270101';
DECLARE @CodigoEmpresa int = 0;

DECLARE @SitDocsPagamento TABLE
(
    CodigoSitDoc int NOT NULL PRIMARY KEY
);

/* Exemplo: inserir somente Sit.Doc de saída já homologado.
INSERT INTO @SitDocsPagamento (CodigoSitDoc)
VALUES (0);
*/

;WITH BaseTitulosPagos AS
(
    SELECT
        T.CNPJ_CPF AS Documento,
        C.NOME AS RazaoSocial,
        B.DATA_LANCAMENTO AS DataBaixa,
        CAST(B.VALOR_BAIXA AS decimal(15,2)) AS ValorBaixado
    FROM dbo.TITULO_MOVIMENTO AS T
    INNER JOIN dbo.TITREFBAIXA AS R
        ON R.PONTEIRO = T.PONTEIRO
    INNER JOIN dbo.TITULO_MOVIMENTO AS B
        ON B.ID_TITULO_MOVIMENTO = R.IDBAIXA
    INNER JOIN @SitDocsPagamento AS SD
        ON SD.CodigoSitDoc = B.CODIGO_SITUACAO_DOCUMENTO
    LEFT JOIN dbo.CATALOGO AS C
        ON C.PESSOA = T.PESSOA
       AND C.CNPJ_CPF = T.CNPJ_CPF
    INNER JOIN dbo.APLICACAO_RECURSO_FINANCEIRO AS A
        ON A.CODIGO_EMPRESA = T.CODIGO_EMPRESA
       AND A.CODIGO = T.CODIGO_APLICACAO_RECURSO_FIN
    INNER JOIN dbo.GRUPO_APLIC_REC_FINANCEIRO AS G
        ON G.CODIGO_EMPRESA = A.CODIGO_EMPRESA
       AND G.CODIGO = A.CODIGO_GRUPO
    WHERE T.CODIGO_EMPRESA = @CodigoEmpresa
      AND T.HISTORICO = 1
      AND T.CRC_CPG = 'P'
      AND G.TIPO IN (1, 2, 3)
      AND B.DATA_LANCAMENTO >= @DataInicial
      AND B.DATA_LANCAMENTO < @DataFinalExclusiva
      AND COALESCE(B.VALOR_BAIXA, 0) <> 0
)
SELECT
    MAX(RazaoSocial) AS RazaoSocial,
    Documento,
    SUM(CASE WHEN MONTH(DataBaixa) = 1 THEN ValorBaixado ELSE 0 END) AS Jan,
    SUM(CASE WHEN MONTH(DataBaixa) = 2 THEN ValorBaixado ELSE 0 END) AS Fev,
    SUM(CASE WHEN MONTH(DataBaixa) = 3 THEN ValorBaixado ELSE 0 END) AS Mar,
    SUM(CASE WHEN MONTH(DataBaixa) = 4 THEN ValorBaixado ELSE 0 END) AS Abr,
    SUM(CASE WHEN MONTH(DataBaixa) = 5 THEN ValorBaixado ELSE 0 END) AS Mai,
    SUM(CASE WHEN MONTH(DataBaixa) = 6 THEN ValorBaixado ELSE 0 END) AS Jun,
    SUM(CASE WHEN MONTH(DataBaixa) = 7 THEN ValorBaixado ELSE 0 END) AS Jul,
    SUM(CASE WHEN MONTH(DataBaixa) = 8 THEN ValorBaixado ELSE 0 END) AS Ago,
    SUM(CASE WHEN MONTH(DataBaixa) = 9 THEN ValorBaixado ELSE 0 END) AS Set,
    SUM(CASE WHEN MONTH(DataBaixa) = 10 THEN ValorBaixado ELSE 0 END) AS Out,
    SUM(CASE WHEN MONTH(DataBaixa) = 11 THEN ValorBaixado ELSE 0 END) AS Nov,
    SUM(CASE WHEN MONTH(DataBaixa) = 12 THEN ValorBaixado ELSE 0 END) AS Dez,
    SUM(ValorBaixado) AS TotalAno
FROM BaseTitulosPagos
GROUP BY Documento
ORDER BY MAX(RazaoSocial), Documento;
