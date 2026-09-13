# Agente Python — Engenharia Reversa DON

Este é o agente Python local para consultar e documentar o ERP DON com a API da OpenAI. Ele é separado do agente do VS Code, mas respeita as mesmas regras essenciais.

## O que ele pode fazer

- Ler, listar e pesquisar somente em `local/operacional/engenharia_reversa_don/`.
- Usar `CONTINUIDADE.md` como ponto de partida obrigatório.
- Produzir uma análise em português, distinguindo fato confirmado, inferência e pendência.
- Quando você autorizar explicitamente, escrever apenas em `analises/`, `CONTINUIDADE.md` e `documentacao/auditorias/`.

## O que ele não pode fazer

- Executar SQL, abrir banco de dados, usar terminal, navegar na internet, criar conexões ou pedir credenciais.
- Ler ou editar arquivos fora do escopo DON.
- Alterar fontes preservadas, metadados, snapshots ou geradores.
- Sobrescrever um arquivo existente sem uma solicitação explícita do modelo e a opção correspondente.

## Configuração única

No terminal integrado do VS Code, na raiz do projeto, execute:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\tools\agente_don\requirements.txt
Copy-Item .\tools\agente_don\.env.example .\tools\agente_don\.env
```

Abra `tools/agente_don/.env` e preencha apenas `OPENAI_API_KEY`. Esse arquivo já é ignorado pelo Git. A assinatura do ChatGPT e os créditos da API são gerenciados separadamente.

## Uso

No terminal do VS Code, você pode abrir uma conversa e escrever normalmente, como em um chat:

```powershell
.\.venv\Scripts\python.exe .\tools\agente_don\agente_don.py --chat
```

Quando aparecer `Você:`, escreva, por exemplo: `Leia a continuidade e diga qual é o próximo bloco pendente.` Para encerrar, digite `sair`.

Também é possível enviar uma pergunta isolada, sempre em modo somente leitura:

```powershell
.\.venv\Scripts\python.exe .\tools\agente_don\agente_don.py "continue a engenharia reversa a partir da continuidade"
```

Depois de revisar a solicitação e quando desejar que ele gere a análise e atualize a continuidade:

```powershell
.\.venv\Scripts\python.exe .\tools\agente_don\agente_don.py "analise somente o próximo bloco indicado e registre o resultado" --permitir-escrita
```

Não use `--permitir-escrita` para testar. O padrão é propositalmente somente leitura.

## Limite importante

Autonomia aqui significa o agente decidir a sequência de leitura e análise **dentro do escopo permitido**. Não significa autorização para consultar bancos, executar comandos ou alterar dados reais.
