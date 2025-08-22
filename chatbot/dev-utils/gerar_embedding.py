# Este arquivo é criado porque precisamos gerar embeddings (representação numérica das palavras)
# Usar os embedding para um chatbot simples como esse é recomendável pois as pessoas podem fazer as mesmas perguntas
# com conjunto de letras e palavras diferentes, porém, a ordem dos fatores não altera o resultado.
# Dito isso, usando o modelo "all-MiniLM-L6-v2" para ler os embeddings, ele procura a pergunta FAQ
# mais parecida com a feita pelo usuário, para gerar uma unica resposta pré-programada no JSON. 


from sentence_transformers import SentenceTransformer
import json
# Aqui um vetor chamado "faq" referente as perguntas-base, que será transformado em JSON.
with open('treinamento_semantico.json', 'r', encoding='utf-8') as f:
    faq = json.load(f)


# Modelo leve e gratuito: all-MiniLM-L6-v2
modelo = SentenceTransformer('all-MiniLM-L6-v2')

# Extrai apenas as perguntas para gerar embeddings
perguntas = [item['pergunta'] for item in faq]

# Gera os embeddings
vetores = modelo.encode(perguntas).tolist()

"""
for item in faq:
    embedding = modelo.encode(item["pergunta"]).tolist()  # converte para lista nativa do Python
    item["embedding"] = embedding
"""
# Junta pergunta, resposta e embedding
faq_completo = []
for i, item in enumerate(faq):
    faq_completo.append({
        "pergunta": item['pergunta'],
        "resposta": item['resposta'],
        "embedding": vetores[i]
    })

# Salva tudo no base_faq.json final
with open('base_faq.json', 'w', encoding='utf-8') as f:
    json.dump(faq_completo, f, ensure_ascii=False, indent=2)

print("base_faq.json gerado com sucesso!")
