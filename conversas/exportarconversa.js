// Esse Script serve para exportar as conversas do wpp web no navegador, basta colar no console e executar

(function () {
  const mensagens = document.querySelectorAll("div.message-out, div.message-in");
  const output = [];

  mensagens.forEach(m => {
    const cabecalho = m.querySelector("div.copyable-text")?.getAttribute("data-pre-plain-text")?.trim();
    const spans = m.querySelectorAll("span.selectable-text span");

    const partesTexto = Array.from(spans)
      .map(s => s.innerText.trim())
      .filter(t => t.length > 0);

    if (cabecalho && partesTexto.length > 0) {
      output.push(`${cabecalho} ${partesTexto.join('\n')}`);
    }
  });

  const blob = new Blob([output.join("\n\n")], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "conversa_1.txt";
  link.click();
})();
