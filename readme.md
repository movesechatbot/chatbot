<h1> PawFolio - Trabalho de Faculdade </h1>

## Diagramas

### Diagrama de Classes

```
class Cliente {
  id: int
  nome: string
  email: string
  senha: string
  cadastrarPet(): void
  agendarServico(): void
}
class Pet {
  id: int
  nome: string
  comportamento: string
  raca: string
  diferencial: string
}
class Petshop {
  id: int
  nome: string
  email: string
  senha: string
  cadastrarServico(): void
}
class Servico {
  id: int
  nome: string
  descricao: string
  preco: float
}
class Agendamento {
  id: int
  dataHora: datetime
  confirmarAgendamento(): void
}
Cliente "1" -- "" Pet : possui
Pet "" -- "1" Cliente : pertence
Pet "" -- "" Servico : solicita
Petshop "1" -- "" Servico : oferece
Cliente "1" -- "" Agendamento : faz
Servico "" -- "" Agendamento : está associado
```

### Diagrama de Casos de Uso

```
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
```

## Disciplinas e Integrações

### 🧠 1. Inglês 1 – Prompt para IA
- Área de FAQ com IA simulando ambiente bilíngue.
- Prompts em inglês para interação automatizada.

### 📊 2. Estatística Aplicada – Indicadores
- Página de dashboard com:
  - Gráfico de acessos
  - Serviços mais acessados
  - Taxa de retorno de usuários

### ☁️ 3. Computação em Nuvem – Arduino Cloud + ESP32
- Protótipo teórico de sensores integrados (temperatura, movimento).

### 🤖 4. IA e Aprendizado de Máquina
- Recomendação de serviços baseada em histórico ou tipo de pet.

### 📱 5. Multiplataforma e BI
- Relatórios com Google Data Studio / Power BI / PHP.
- Armazenamento de dados para análise.

### 🧩 6. Padrões de Projeto – MVC
- Código organizado em Model, View, Controller.
- Singleton aplicado à conexão com o banco.

---

## ✅ Como configurar o projeto

1. **Pré-requisitos**
   - PHP 8+
   - MySQL/MariaDB
   - Servidor local (ex: XAMPP, WAMP, Laragon)

2. **Clone o repositório**
   ```bash
   git clone https://github.com/TheoTavora/ProjetoPawFolio.git
   ```

3. **Configure o banco de dados**
   - Importe o arquivo `.sql` atualizado (conforme o diagrama de classes).
   - Ou crie o banco com base no modelo acima usando MySQL Workbench.

4. **Configure o arquivo `config.php`**
   - Ajuste as variáveis de conexão com o banco:
     ```php
     $dbHost = 'localhost';
     $dbUsername = 'root';
     $dbPassword = '';
     $dbName = 'pawfolio';
     ```

5. **Execute o projeto**
   - Coloque os arquivos na pasta `htdocs` (ou equivalente).
   - Acesse no navegador: `http://localhost/ProjetoPawFolio`

6. **(Opcional) Instalar dependências**
   - Se houver bibliotecas externas, instale-as conforme instruções internas (ex: Chart.js, etc).

---