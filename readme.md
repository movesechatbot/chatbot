<h1>PawFolio</h1>

<h3>PawFolio - Trabalho de Faculdade</h3>

<h5>Diagramas:</h5>

class Cliente {
  - id: int
  - nome: string
  - email: string
  - senha: string
  + cadastrarPet(): void
  + agendarServico(): void
}

class Pet {
  - id: int
  - nome: string
  - comportamento: string
  - raca: string
  - diferencial: string
}

class Petshop {
  - id: int
  - nome: string
  - email: string
  - senha: string
  + cadastrarServico(): void
}

class Servico {
  - id: int
  - nome: string
  - descricao: string
  - preco: float
}

class Agendamento {
  - id: int
  - dataHora: datetime
  + confirmarAgendamento(): void
}

Cliente "1" -- "*" Pet : possui
Pet "*" -- "1" Cliente : pertence
Pet "*" -- "*" Servico : solicita
Petshop "1" -- "*" Servico : oferece
Cliente "1" -- "*" Agendamento : faz
Servico "*" -- "*" Agendamento : está associado


// Diagrama de Casos de Uso

actor Cliente
actor Petshop

usecase "Cadastrar Pet" as CP
usecase "Agendar Serviço" as AS
usecase "Cadastrar Serviço" as CS
usecase "Gerenciar Agendamentos" as GA

Cliente -- CP
Cliente -- AS
Petshop -- CS
Petshop -- GA

Projeto PawFolio mais robusto e multidisciplinar.
---

🧠 1. Inglês 1 – Prompt para IA (Valéria Baccili)

No projeto:

Crie uma área de FAQ com IA (pode ser um chatbot ou apenas um formulário inteligente que responde com base em perguntas pré-definidas).

Os prompts podem estar em inglês, simulando um ambiente bilíngue.


No relatório:

> Foi iniciada a elaboração de prompts em inglês para um sistema de assistência automatizada ao usuário, utilizando técnicas de linguagem natural. A proposta é aplicar habilidades de escrita e compreensão do idioma para criar interações mais fluídas com o visitante do site.




---

📊 2. Estatística Aplicada – Indicadores (Jéssica Delgado)

No projeto:

Adicione uma página de dashboard administrativo com:

Gráfico de número de acessos

Serviços mais acessados

Taxa de retorno de usuários



No relatório:

> Foi implementado um painel de indicadores estatísticos com dados de navegação, utilizando gráficos simples (por exemplo, com Chart.js ou Google Charts), permitindo a visualização de informações relevantes como acessos por página e serviços mais procurados.




---

☁️ 3. Computação em Nuvem – Arduino Cloud + ESP32 (Gustavo Gonçalves)

No projeto:

Crie um protótipo teórico (ou apenas descritivo/simulativo) de integração com sensores para monitoramento de pets (ex: temperatura de ambiente do pet shop).


No relatório:

> Foi desenvolvido um protótipo teórico de integração com a Arduino Cloud via ESP32, simulando a captação de temperatura ambiente ou movimento em áreas de pets, com possível visualização em tempo real no site.




---

🤖 4. IA e Aprendizado de Máquina – Machine Learning (Vinicius Marques)

No projeto:

Desenvolva um sistema simples de recomendação de serviços baseado em histórico de uso do usuário.

Ou classifique tipos de pet para serviços ideais (ex: cão grande = banho especial).


No relatório:

> Iniciamos a construção de um modelo simples de machine learning para sugerir serviços com base em interações anteriores dos usuários. Utilizamos lógica condicional baseada em dados simulados para prever preferências e sugerir soluções personalizadas.




---

📱 5. Multiplataforma e BI – Dashboard / Big Data (Isaque Katahira)

No projeto:

Use ferramentas como Google Data Studio, Power BI, ou PHP com gráficos para gerar relatórios.

Armazene dados de usuários para futuras análises.


No relatório:

> A disciplina contribuiu com a análise de dados armazenados no banco do projeto, utilizando conceitos de BI para geração de relatórios e dashboards com estatísticas sobre os serviços e comportamento dos usuários.




---

🧩 6. Padrões de Projeto – MVC e outros (Andre Fávaro)

No projeto:

Organize o código em Model, View e Controller no PHP.

Use Singleton para conexão com banco, por exemplo.


No relatório:

> O projeto foi reestruturado seguindo o padrão de arquitetura MVC, separando responsabilidades entre lógica de controle, interface e banco de dados. Padrões como Singleton também foram aplicados para otimizar conexões com o banco.
