# Regras de negócio e lógica SQL

## Títulos pagos

O relatório trabalha com título original e baixa separadamente.

1. O título original é filtrado por `HISTORICO = 1`.
2. A baixa válida é encontrada pela view `TITREFBAIXA`.
3. A baixa contém a data efetiva (`DATA_LANCAMENTO`) e o valor baixado (`VALOR_BAIXA`).
4. Baixas com histórico `1` ou `5` não são consideradas pela view.

O padrão de ligação é:

```sql
TITULO_MOVIMENTO T
INNER JOIN TITREFBAIXA R
    ON R.PONTEIRO = T.PONTEIRO
INNER JOIN TITULO_MOVIMENTO B
    ON B.ID_TITULO_MOVIMENTO = R.IDBAIXA
```

## Despesas elegíveis

Uma baixa entra na matriz de despesas quando o título original atende simultaneamente a estas condições:

```sql
T.HISTORICO = 1
T.CRC_CPG = 'P'
G.TIPO IN (1, 2, 3)
B.VALOR_BAIXA <> 0
```

O filtro por `G.TIPO` evita excluir ou incluir registros pelo texto da descrição. Receitas, recebimentos, abatimentos e transferências não devem ser classificados como despesas apenas pela aparência do histórico.

## CPF/CNPJ

O CPF/CNPJ completo deve ser composto usando o cadastro de endereço quando houver complemento de filial e dígito. A regra de máscara só vale para documentos numéricos de 11 ou 14 posições. Cadastros inválidos permanecem visíveis como estão, pois não devem ser convertidos em um documento falso.

No consolidado, registros sem CPF/CNPJ recebem um identificador baseado na pessoa para não serem somados entre si por engano.

## Consolidação

A matriz horizontal agrupa por CPF/CNPJ e traz uma razão social representativa. Serviço, grupo de despesa, empresa, documento e vencimento pertencem ao relatório detalhado para Power BI, não ao consolidado por fornecedor.

## Períodos

O filtro de data deve ter início inclusivo e término exclusivo:

```sql
DATA_LANCAMENTO >= @DataInicial
AND DATA_LANCAMENTO < @DataFinalExclusiva
```

Esse padrão evita perda de registros por causa do horário no campo `datetime`.

## Carteiras bancárias

Uma carteira entra no relatório somente depois de:

1. localizar a conta no cadastro bancário;
2. identificar o Sit.Doc correspondente;
3. conferir a carteira contra o extrato bancário;
4. registrar o código homologado na configuração local.

Não use texto como `PAGAMENTO`, `RECEBIMENTO` ou nome de banco como regra definitiva de inclusão.
