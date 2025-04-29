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
