# Roteiro de trabalho no VS Code

## Preparação local

1. Abra esta pasta no VS Code.
2. Copie `config/ambientes.example.json` para `config/ambientes.local.json`.
3. Preencha servidores, banco e demais parâmetros somente no arquivo local.
4. Mantenha os scripts produtivos em `local/operacional/` até existir autorização para um repositório privado.

## Ordem de execução

1. Mapa técnico e inventário de contas.
2. Diagnóstico de Sit.Doc.
3. Validação contra extrato.
4. Matriz numérica para Power BI.
5. Consulta formatada para SSMS ou Excel.

## Power BI

Evite `FORMAT()` na consulta usada pelo Power BI. A função retorna texto e dificulta soma, filtro e relacionamento. Deixe a base como `decimal` e aplique a moeda brasileira no próprio Power BI.

## Publicação

Antes de cada envio ao GitHub, confira:

```powershell
git status
git diff --check
```

O envio público deve conter somente documentação, modelos genéricos e configurações sem dados reais.
