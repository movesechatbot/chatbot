# Este arquivo é criado porque precisamos gerar embeddings (representação numérica das palavras)
# Usar os embedding para um chatbot simples como esse é recomendável pois as pessoas podem fazer as mesmas perguntas
# com conjunto de letras e palavras diferentes, porém, a ordem dos fatores não altera o resultado.
# Dito isso, usando o modelo "all-MiniLM-L6-v2" para ler os embeddings, ele procura a pergunta FAQ
# mais parecida com a feita pelo usuário, para gerar uma unica resposta pré-programada no JSON. 


from sentence_transformers import SentenceTransformer
import json

# Modelo leve e gratuito: all-MiniLM-L6-v2
modelo = SentenceTransformer('all-MiniLM-L6-v2')

# Aqui um vetor chamado "faq" referente as perguntas-base, que será transformado em JSON.
faq = [
    {
        "pergunta": "Como agendar?",
        "resposta": "Você pode agendar serviços acessando a aba de agendamento no menu principal."
    },
    {
        "pergunta": "Posso remarcar um agendamento?",
        "resposta": "Sim, você pode remarcar até 24h antes do horário marcado."
    },
    {
        "pergunta": "O PawFolio atende gatos?",
        "resposta": "Sim, atendemos tanto cães quanto gatos de todos os portes."
    },
    {
        "pergunta": "Como cancelar um agendamento?",
        "resposta": "Clique em 'Meus Agendamentos' e selecione a opção 'Cancelar'."
    },
    {
        "pergunta": "O que é o Pawfolio? O que vocês fazem? O que são vocês?",
        "resposta": "O Pawfolio é um sistema/fórum que atua como uma grande rede de conexão entre petshop's, assim, oferecendo serviços em nosso site, para qualquer um acessar!"
    },
    {
        "pergunta": "Preciso cadastrar meu pet?",
        "resposta": "Para que o agendamento seja 100% via nosso site, é orientado o cadastro do seu pet para melhor planejamento, tanto do petshop, quanto seu e nós da PawFolio."
    },
    {
        "pergunta": "Pagamento via site?",
        "resposta": "O pagamento não é feito via site, essa é uma função que ainda está em desenvolvimento!, mas você pode entrar em contato com o petshop na qual escolheu contratar o serviço!"
    },
    {
        "pergunta": "Porque eu devo cadastrar o meu animal?",
        "resposta": "Você deve cadastrar seu pet pois petshop acessa as credenciais do seu animal para ter um melhor planejamento quando for atendê-lo."
    },
    {
        "pergunta": "Do you take care of cats?",
        "resposta": "Yes, petshop's serve both dogs and cats of all sizes."
    },
    {
        "pergunta": "Can i pay via website?",
        "resposta": "Payment is not made via the website, this is a function that is still under development!, but you can contact the pet shop where you chose to hire the service!"
    },
    {
        "pergunta": "Quanto custa? Qual o valor?",
        "resposta": "O PawFolio oferece serviços de outros petshop's e não vendemos. Confira os petshop's e escolha os devidos serviços e confira os preços."
    },
    {
        "pergunta": "Quero falar com uma pessoa",
        "resposta": "Sou uma I.A pronta para responder suas dúvidas, caso queira um ser-humano, vá direto para o petshop que deseja ser atendido e peça que a devida equipe atenda-o!"
    },
    {
        "pergunta": "Why do i need to register my pet?",
        "resposta": "In order for scheduling to be 100% via our website, we recommend registering your pet for better planning, both for the pet shop, for you and for us at PawFolio."
    }
]

# Gera os embeddings
for item in faq:
    embedding = modelo.encode(item["pergunta"]).tolist()  # converte para lista nativa do Python
    item["embedding"] = embedding

# Salva no JSON, UTF-8
with open("base_faq.json", "w", encoding="utf-8") as f:
    json.dump(faq, f, ensure_ascii=False, indent=2)

print("base_faq.json gerado com sucesso!")
