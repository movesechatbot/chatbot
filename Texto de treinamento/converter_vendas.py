import json

def contar_indentacao(linha):
    return len(linha) - len(linha.lstrip(' '))

def detectar_tipo(texto):
    if texto.startswith("*") and texto.endswith("*"):
        return "fala"
    elif texto.lower().startswith(("caso", "cliente", "lead", "se ", "quando ", "usuário ")):
        return "condicao"
    elif texto.startswith("###"):
        return "titulo"
    else:
        return "instrucao"

def parse_vendas_txt(caminho_entrada, caminho_saida):
    with open(caminho_entrada, "r", encoding="utf-8") as f:
        linhas = [linha.rstrip() for linha in f if linha.strip()]

    raiz = []
    pilha = [(0, raiz)]

    texto_acumulado = ""
    indent_anterior = None

    for linha in linhas:
        indent = contar_indentacao(linha)
        texto = linha.strip()

        if indent_anterior is not None and indent == indent_anterior:
            texto_acumulado += "\n" + texto
            continue

        if texto_acumulado:
            tipo = detectar_tipo(texto_acumulado)
            nodo = {
                "tipo": tipo,
                "texto": texto_acumulado.strip("* "),
                "filhos": []
            }

            while pilha and indent_anterior <= pilha[-1][0]:
                pilha.pop()

            if not pilha:
                pilha.append((0, raiz))

            pilha[-1][1].append(nodo)
            pilha.append((indent_anterior, nodo["filhos"]))
            texto_acumulado = ""

        texto_acumulado = texto
        indent_anterior = indent

    if texto_acumulado:
        tipo = detectar_tipo(texto_acumulado)
        nodo = {
            "tipo": tipo,
            "texto": texto_acumulado.strip("* "),
            "filhos": []
        }

        while pilha and indent_anterior <= pilha[-1][0]:
            pilha.pop()

        if not pilha:
            pilha.append((0, raiz))

        pilha[-1][1].append(nodo)

    with open(caminho_saida, "w", encoding="utf-8") as f:
        json.dump(raiz, f, indent=2, ensure_ascii=False)

    print(f"✅ JSON gerado com sucesso: {caminho_saida}")


# Execução
if __name__ == "__main__":
    parse_vendas_txt("vendas.txt", "playbook_diagramado.json")
