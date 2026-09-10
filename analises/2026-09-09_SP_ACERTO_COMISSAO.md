# Análise manual — dbo.SP_ACERTO_COMISSAO

**Data:** 09/09/2026  
**Classificação:** interpretação técnica a partir de fonte preservada; não homologada em tela e não executada em servidor.

## Evidência examinada

- Fonte: `documentacao/fontes/dbo.SP_ACERTO_COMISSAO__83e792c41234.txt`.
- Tipo: stored procedure.
- Registros tratados: `AC`, `AD` e `AP`.
- Ambientes catalogados: VIA-SQL, TDE-SQL01 e STC-MSSQL.

## Engenharia reversa confirmada

A procedure abre transação e processa acertos de comissão para autorizações CEMIG, débito e COPASA. Valida usuário, tipo de acerto, participante do acerto e operação de pagamento ou cancelamento.

Para cada autorização encontrada, grava o cabeçalho em `ACERTO_COMISSAO`, grava detalhes em `ACERTO_COMISSAO_DETALHE`, atualiza flags de pagamento de comissão nas tabelas de autorização e chama `SP_REGISTRA_LOG`. O cálculo/identificação de parâmetros também consulta `PROCURAPARAMETROTELEMARKETING`.

## Regra prática — interpretação sustentada pela fonte

O procedimento formaliza o acerto de comissão: transforma autorizações elegíveis em um registro de acerto, registra os detalhes por mensageiro ou operador e marca a autorização como paga ou desfeita.

A operação é transacional e só confirma quando há detalhes processados. O log preserva o usuário e os valores antigos/novos dos indicadores de pagamento.

## Limites e riscos técnicos observados

1. Usa `@@IDENTITY`, que pode retornar identidade gerada por outro gatilho; `SCOPE_IDENTITY()` seria mais específico.
2. Não há `TRY/CATCH` explícito para garantir tratamento uniforme de erros e rollback.
3. O processamento é cursorizado e linha a linha.
4. `@CODIGO_EMPRESA` aparece principalmente no logging e não necessariamente restringe todas as autorizações processadas.
5. Flags nulos podem escapar de comparações com `<>`.
6. A mesma lógica é repetida para três fontes de autorização, aumentando risco de divergência entre ramos.

## O que falta confirmar

- Parâmetros completos e regras de permissão da tela de acerto.
- Quando o acerto é considerado pagamento e quando é cancelamento.
- Relação entre o tipo de participante e as tabelas de mensageiro/operador.
- Critérios de reprocessamento e reversão autorizada.

## Próxima análise vinculada

`dbo.SP_CALCULA_COMISSAO_MENSAGEIRO`: cálculo da comissão que antecede ou alimenta o acerto.
