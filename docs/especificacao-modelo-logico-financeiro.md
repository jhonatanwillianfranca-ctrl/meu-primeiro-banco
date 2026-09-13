# Especificação viva — modelo lógico financeiro

**Versão:** 0.2  
**Atualizada em:** 13/09/2026  
**Estado:** migration SQLite m001 aplicada no cache técnico local em 13/09/2026; validada por testes automatizados

## Objetivo e limites

Esta especificação orienta a evolução do MEU-PRIMEIRO-BANCO para cobrir, de forma integrada, contas a pagar, contas a receber, fluxo de caixa e conciliação bancária.

Ela é uma especificação viva: deve ser revisada a cada bloco de trabalho quando houver nova evidência, alteração de regra ou ajuste de escopo. Não é schema físico, migration, autorização de conexão, nem regra definitiva do ERP DON.

Nesta etapa, foi criada a migration versionada `db/migrations/m001_nucleo_financeiro.py` e seu executor explícito `db/migrar_nucleo_financeiro.py`. Ela exige que o caminho do SQLite seja informado por `--database` e não lê configurações locais.

## Registro de aplicação local

- **Data:** 13/09/2026.
- **Arquivo SQLite:** `local/cache/meu_primeiro_banco.db`.
- **Migration aplicada:** `001_nucleo_financeiro`.
- **Resultado:** as 11 tabelas financeiras, índices, constraints e o controle técnico `schema_migrations` foram criados no arquivo.
- **Staging técnico:** `titulos_movimento`, `sync_estado` e `sync_log` estavam ausentes porque o arquivo era novo; nenhuma dessas estruturas foi criada, alterada ou removida por esta migration.
- **Validação:** suíte automatizada executada contra o arquivo persistente em modo somente leitura após a aplicação.
- **Limite preservado:** nenhuma conexão SQL Server, arquivo de credencial ou material da engenharia reversa DON foi utilizado.

## Decisões aprovadas

1. Clientes e fornecedores serão representados por um cadastro único de pessoa, identificado por tipo ou papel.
2. O fluxo de caixa será derivado de parcelas, liquidações e previsões manuais. Não haverá tabela de saldo duplicado.
3. Baixa financeira e conciliação bancária são eventos distintos e obrigatoriamente separados.
4. SQLite terá dois papéis: cache técnico da sincronização e base local para consultas e relatórios financeiros.
5. Uma eventual implementação em SQL Server deverá ocorrer somente em ambiente e banco autorizados; ela não autoriza alteração no ERP DON ou em produção.

## Entidades lógicas

| Entidade | Linha representa | Campos-chave lógicos | Relações principais |
| --- | --- | --- | --- |
| Empresa | Uma empresa do escopo financeiro | id, código de origem, razão social, nome fantasia, ativa | Possui contas, títulos, conciliações e previsões. |
| Pessoa | Uma contraparte financeira | id, tipo de pessoa, papéis, nome, documento, ativa | Pode ser cliente, fornecedor ou ambos; vincula títulos. |
| Conta financeira | Uma conta bancária, caixa ou outro meio autorizado | id, empresa, tipo, instituição, identificação mascarada, ativa | Possui movimentações bancárias. |
| Categoria financeira | Uma classificação gerencial de entrada ou saída | id, código, descrição, natureza, ativa | Classifica título ou previsão manual. |
| Título financeiro | Um direito ou obrigação original | id, empresa, pessoa, categoria, natureza, documento, emissão, competência, valor original, situação | Tem uma ou mais parcelas. |
| Parcela financeira | Uma obrigação ou recebimento com vencimento próprio | id, título, número, vencimento, valor previsto, situação | Tem zero ou mais liquidações. |
| Liquidação financeira | Uma baixa, parcial ou total, registrada no processo financeiro | id, parcela, data, principal, juros, desconto, estorno, origem | Pode ser vinculada à conciliação bancária. |
| Movimentação bancária | Uma linha de extrato ou evento bancário identificado | id, conta financeira, data, valor, descrição, identificador externo, origem | Pode conciliar uma ou mais liquidações. |
| Conciliação bancária | Um processo auditável de vínculo entre banco e financeiro | id, empresa, data, situação, responsável | Agrupa itens de conciliação. |
| Item de conciliação | Uma alocação de valor conciliado | id, conciliação, movimentação bancária, liquidação financeira, valor conciliado | Resolve pagamentos agrupados, parciais ou divididos. |
| Previsão manual de fluxo | Uma previsão sem título de origem | id, empresa, conta financeira opcional, categoria, data prevista, valor, natureza, situação | Complementa o fluxo projetado sem duplicar realizado. |

## Regras de significado

### Títulos, parcelas e liquidações

- `natureza` do título deve distinguir, no mínimo, `PAGAR` e `RECEBER`.
- Um título pode ter várias parcelas; cada parcela pertence a um único título.
- O saldo na data-base deve ser reconstruído a partir do valor previsto e das liquidações válidas até aquela data. Uma baixa posterior não quita retroativamente uma posição histórica.
- Liquidações parciais, juros, descontos e estornos devem permanecer identificáveis; não devem ser escondidos no valor original.

### Caixa, competência e conciliação

- Emissão, competência, vencimento, liquidação e movimento bancário são datas distintas.
- A liquidação comprova um evento financeiro registrado. Ela não comprova sozinha que o banco movimentou o valor.
- A conciliação confirma o vínculo entre movimentação bancária e liquidação por meio do item de conciliação.
- Uma movimentação bancária pode atender várias liquidações; uma liquidação pode ser conciliada em mais de uma movimentação quando a regra operacional permitir. O valor conciliado deve manter a trilha de alocação.
- Fluxo de caixa projetado considera parcelas abertas e previsões manuais aprovadas. Fluxo realizado considera movimentos bancários segundo a regra de conciliação/classificação aprovada.
- Não somar uma previsão manual que represente parcela já existente; esse é um risco explícito de dupla contagem.

## Relação com as estruturas atuais

O schema atual em `db/cache_local.py` é técnico e permanece separado do núcleo lógico proposto.

| Estrutura atual | Uso atual confirmado | Relação possível com o modelo lógico | Limite atual |
| --- | --- | --- | --- |
| `titulos_movimento` | Cache de extração de recebimentos por unidade, carteira, cliente, vencimento e baixa | Fonte de origem para título, parcela e liquidação | Não é o núcleo financeiro; a extração atual não confirma cobertura de contas a pagar. |
| `TITULO_MOVIMENTO_ID` | Identificador vindo da origem | Referência externa do título | Exige regra de unicidade por empresa/unidade antes de ser chave de integração. |
| `CLIENTE` e `CNPJ_CPF` | Dados de contraparte da extração | Pessoa | Não prova que toda contraparte seja cliente. |
| `CARTEIRA` | Campo da origem e filtro de sincronização | Referência de origem | Não deve ser assumida como conta financeira sem homologação. |
| `DATA_BAIXA` e `VALOR_BAIXA` | Dados de baixa da origem | Liquidação financeira | Não representam conciliação bancária confirmada. |
| `sync_estado` e `sync_log` | Controle técnico da sincronização | Nenhuma entidade financeira | Devem permanecer como controle técnico. |

As regras existentes em `docs/regras-de-negocio.md` continuam aplicáveis apenas ao relatório de títulos pagos e às condições já documentadas. Elas não definem, por si só, o novo núcleo financeiro completo.

## Diretriz de implementação futura

### SQLite local

Manter duas camadas separadas:

1. **Staging técnico:** `titulos_movimento`, `sync_estado` e `sync_log`.
2. **Núcleo financeiro:** entidades lógicas desta especificação, alimentadas por transformação rastreável e com referência à origem, data de carga e regra aplicada.

Valores monetários não devem usar ponto flutuante. A representação física será decidida antes da implementação, preservando moeda, escala e arredondamento explícitos.

### SQL Server futuro

Se houver necessidade de um banco SQL Server para o núcleo financeiro, ele deverá reproduzir o mesmo modelo lógico em banco/ambiente autorizado e separado das fontes do ERP, salvo autorização expressa em sentido diferente.

Antes dessa etapa, devem ser definidos: chave técnica, estratégia de valor monetário, constraints, índices, auditoria, permissões e processo de carga. Nenhuma dessas decisões está implementada neste documento.

## Governança e validação futura

- Toda carga deve registrar sistema de origem, identificador externo, data/hora de carga e regra aplicada.
- Toda regra de classificação deve diferenciar fato confirmado, inferência e pendência de homologação.
- Relatórios devem declarar a data que define cada indicador e não tratar fluxo gerencial como demonstração contábil formal.
- A validação deve cobrir unicidade, duplicidade após relacionamentos, isolamento por empresa, nulos, estornos, liquidações parciais e reconciliação com fonte independente quando disponível.

## Backlog futuro — não implementar nesta etapa

### Contas vencidas por empresa e data

Construir relatório de contas vencidas por empresa e data, hoje referido como vindo do "Gerenciador" do ERP DON.

Pré-requisitos obrigatórios:

1. Confirmar na documentação de engenharia reversa DON qual campo e tabela representam efetivamente o vencimento.
2. Obter ambiente de leitura homologado e autorizado.
3. Aplicar filtro explícito de empresa em toda consulta desse relatório; nunca assumir uma empresa por padrão, pois TDE-SQL01 é multiempresa.

Até esses pré-requisitos serem satisfeitos, não há campo, consulta nem regra de atraso homologada para esse relatório.

### Menu de relatórios

Há uma direção futura para um menu de relatórios no sistema MEU-PRIMEIRO-BANCO, semelhante ao de um ERP. Ele será construído incrementalmente, relatório por relatório, conforme definição e priorização do usuário.

Não há desenho de interface, estrutura de menu, tecnologia de front-end ou lista definitiva de relatórios nesta etapa.

## Próxima revisão

Antes da primeira implementação física, revisar esta especificação com a decisão de escopo do primeiro bloco, a fonte autorizada, o nível de detalhe, a empresa/período aplicáveis e as regras de validação necessárias.
