# Declaração de uso de Inteligência Artificial

Este projeto foi desenvolvido com apoio de uma ferramenta de IA assistente de
programação — **Claude (Anthropic)** — usada em modo de pair-programming, sempre
sob revisão e decisão final humana.

## Como a IA foi utilizada

- **Discussão de arquitetura e trade-offs:** explorar opções (estratégia de
  atualização, granularidade, tratamento de unidades marinhas) antes de decidir.
- **Scaffolding e configuração:** estruturas de teste, ferramentas de qualidade
  (ruff, mypy, pytest), workflow de CI e hook de pre-commit.
- **Testes:** geração da suíte de testes unitários do tratamento.
- **Documentação:** redação e revisão de textos e notas de decisão.
- **Revisão de código:** lint, checagem de tipos e sugestões de simplificação.

## Supervisão humana

Todas as decisões de design, a lógica central de negócio e a revisão final do
código e dos textos foram feitas pelo autor. As sugestões da IA foram avaliadas,
ajustadas e aplicadas manualmente — nada foi incorporado sem entendimento e
aprovação.
