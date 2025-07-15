# 🐾 PawFolio – Sistema de Agendamento para Petshops

Projeto acadêmico desenvolvido como integração prática entre diversas disciplinas do curso, unindo desenvolvimento web, inteligência artificial e análise de dados.

Inclui uma interface completa para agendamento de serviços, painel de indicadores e um chatbot inteligente de FAQ com IA local.

ATENÇÃO: O NOME DO SISTEMA (PawFolio) NÃO É MEU, APENAS UTILIZANDO PARA FINS ACADÊMICOS.

---

## 📚 Disciplinas e Integrações

### 🧠 1. Inglês 1 – Prompt para IA (concluido)
- Área de FAQ com IA simulando ambiente bilíngue.
- Prompts em inglês para interação automatizada.

### 📊 2. Estatística Aplicada – Indicadores
- Dashboard com:
  - Gráfico de acessos
  - Serviços mais buscados
  - Taxa de retorno de usuários

### ☁️ 3. Computação em Nuvem – Arduino Cloud + ESP32
- Protótipo teórico de sensores integrados para o ambiente petshop.

### 🤖 4. IA e Aprendizado de Máquina
- Recomendação de serviços baseada no tipo de pet.
- Chatbot inteligente de FAQ com IA local e compreensão de paráfrases (detalhado abaixo).

### 📱 5. Multiplataforma e BI
- Relatórios com Google Data Studio / Power BI / PHP.
- Armazenamento em MySQL para análise futura.

### 🧩 6. Padrões de Projeto – MVC
- Estrutura baseada em MVC.
- Singleton aplicado na conexão com banco de dados.

---

## 💬 Chatbot Inteligente com IA Local

O sistema conta com um chatbot de FAQ capaz de entender diferentes formas de perguntar (paráfrases), usando IA local sem depender de APIs externas.

### ⚙️ Como funciona:
- Utiliza o modelo `all-MiniLM-L6-v2` da biblioteca `sentence-transformers`.
- As perguntas do usuário são convertidas em vetores numéricos (embeddings).
- O sistema compara a similaridade com a base existente e retorna a resposta mais próxima.

### 🧪 Tecnologias:
- Python + Flask
- sentence-transformers
- PHP 7+ / MySQL
- HTML/CSS/Sass + Bootstrap

---

## ✅ Como configurar o projeto

1. **Pré-requisitos**
- PHP 8+
- MySQL/MariaDB (XAMPP/LAMPP)
- Python 
- Node.js (para SASS)
- Flask e sentence-transformers:
  ```bash
  pip install flask sentence-transformers
   ```
- Sass: Instale com:
   ```bash
   npm install -g sass
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

### 📎 Autor
Desenvolvido por <a href="https://github.com/TheoTavora">Theo Vitor</a>

### 📝 Licença
Este projeto está licenciado sob a <a href="./LICENSE">Licença MIT.</a>

Projeto acadêmico com código aberto para fins educacionais.
Se você deseja uma versão personalizada para seu negócio (com deploy, segurança, manutenção), entre em contato!


