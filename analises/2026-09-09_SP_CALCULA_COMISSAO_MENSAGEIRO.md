# Análise manual — dbo.SP_CALCULA_COMISSAO_MENSAGEIRO

**Data:** 09/09/2026  
**Classificação:** interpretação técnica a partir de fonte preservada; não homologada em tela e não executada em servidor.

## Evidência examinada

- Fonte: `documentacao/fontes/dbo.SP_CALCULA_COMISSAO_MENSAGEIRO__a5865cd95814.txt`.
- Tipo: stored procedure.
- Ambientes catalogados: VIA-SQL, TDE-SQL01 e STC-MSSQL.

## Engenharia reversa confirmada

A procedure calcula comissão por intervalo de datas, podendo restringir o processamento a um mensageiro. Limpa o controle de processamento, calcula proporções de recebimento, localiza a faixa em `FAIXA_COMISSAO_MENSAGEIRO`, seleciona recibos elegíveis e grava o resultado em `RECIBO_DOACAO`.

Também usa `MENSAGEIRO_MOVIMENTO`, `PROCESSAMENTO_COMISSAO`, `USUARIO` e a tabela persistente `tmp_calculo_comissao`, além de registrar log e consultar parâmetros de telemarketing.

## Regra prática — interpretação sustentada pela fonte

O procedimento atribui ao mensageiro uma comissão proporcional ao recebimento e à faixa percentual cadastrada. Para cada recibo elegível, atualiza o valor da comissão, a data e a observação de processamento.

A trigger de faixa de comissão documentada anteriormente protege os intervalos usados por esta procedure.

## Limites e riscos técnicos observados

1. `TRUNCATE TABLE PROCESSAMENTO_COMISSAO` torna o estado compartilhado entre execuções potencialmente concorrentes.
2. `tmp_calculo_comissao` é uma tabela persistente e pode sofrer colisão entre execuções simultâneas.
3. O denominador do percentual não repete todos os filtros aplicados ao numerador, podendo distorcer a proporção.
4. Pode haver divisão por zero quando nenhum recebimento elegível permanece.
5. Ausência de faixa correspondente pode deixar alíquota nula.
6. O intervalo `BETWEEN` depende das horas informadas nas datas inicial e final.

## O que falta confirmar

- Fórmula empresarial oficial da comissão.
- Natureza dos tipos de recebimento e status elegíveis.
- Se a procedure pode ser executada simultaneamente por usuários.
- Como o sistema reverte comissão calculada incorretamente.

## Próxima análise vinculada

Concluir o grupo fiscal com auditoria do plano de saúde e dos invalidadores de cálculo.
