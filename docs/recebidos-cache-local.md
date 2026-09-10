# Recebidos: cache local e sincronizacao

O servico sincroniza dados de recebimento para um SQLite local. Ele consulta
cada unidade configurada, faz somente insercao ou atualizacao no cache e nunca
remove registros por ausencia na origem.

## Arquivos locais necessarios

1. Copie `config/carteiras.example.json` para `config/carteiras.local.json` e
   informe somente carteiras de entrada homologadas.
2. Copie `config/recebidos.example.json` para `config/recebidos.local.json` e
   informe o `CRC_CPG` confirmado de recebimento.
3. Copie `config/sync.example.json` para `config/sync.local.json` e ajuste
   unidades, intervalo, caminho do cache e consulta local.
4. Crie a consulta de extracao no caminho indicado. Ela deve obedecer ao
   contrato de `sql/templates/boletos_recebidos.sql` e ser somente leitura.

Os arquivos `.local.json`, a consulta operacional e o banco SQLite nao entram
no Git. Nao registre contas, credenciais, CNPJ/CPF ou resultados em arquivos
publicos.

## Operacao

Com o ambiente Python configurado:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-relatorios.txt
.\.venv\Scripts\python.exe -m db.sync_service --uma-vez
.\.venv\Scripts\python.exe -m db.sync_service
```

`--uma-vez` realiza um ciclo. Sem a flag, o servico continua em polling no
intervalo configurado. `--dry-run` valida arquivos, parametros e a consulta,
mas nao abre conexao nem escreve no cache.

O gerador de PDF le apenas o SQLite local. Ele alerta quando a ultima
sincronizacao bem-sucedida ultrapassa o limite configurado.
