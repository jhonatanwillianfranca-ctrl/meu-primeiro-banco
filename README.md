# Integrar bancos SQL e relatórios

Projeto de organização, auditoria e consolidação de relatórios do SQL Server para o ecossistema Garish.

O foco é gerar relatórios confiáveis de títulos pagos, validar carteiras bancárias contra extratos e disponibilizar bases numéricas para Power BI.

## O que este repositório contém

- Regras técnicas e de negócio usadas nas consultas.
- Modelo público e reutilizável de matriz horizontal de despesas pagas.
- Configuração recomendada para VS Code e SQL Server.
- Status do que já foi validado e do que ainda falta executar.

## O que não é publicado

Este repositório é público. Por isso, ele não deve receber:

- Extratos bancários, planilhas de resultado ou dados de fornecedores.
- CPF, CNPJ, valores, números de conta, IPs, senhas ou dados de conexão.
- Mapa técnico completo do banco de dados.
- Scripts operacionais com parâmetros reais.

Os materiais operacionais ficam em `local/operacional/`, que é ignorada pelo Git e continua disponível somente no computador de trabalho.

## Estrutura

```text
config/          Modelos de configuração sem dados reais
docs/            Regras, status e roteiro de trabalho
sql/templates/   Modelos públicos de consultas
local/           Arquivos locais ignorados pelo Git
```

## Começar no VS Code

1. Abra a pasta deste repositório no VS Code.
2. Instale a extensão recomendada `SQL Server (mssql)`.
3. Copie `config/ambientes.example.json` para `config/ambientes.local.json`.
4. Preencha somente o arquivo local com os dados do ambiente autorizado.
5. Execute primeiro os diagnósticos e validações. Só depois use as consultas de produção.

Leia [o roteiro de migração](docs/migracao-vscode.md) antes de conectar ao SQL Server.

## Situação atual

- TAG: relatório de títulos pagos e carteiras principais validados.
- Viavante: matriz criada; Sicoob e Sicredi validados contra extratos.
- STCOOP: pendente de matriz de despesas pagas e validação bancária.
- SEGTRUCK: pendente de início.
- TDE-SQL01: ambiente mapeado, sem relatório produtivo neste projeto.

Detalhes em [status do projeto](docs/status-do-projeto.md).
