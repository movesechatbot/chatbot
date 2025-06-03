function enviarPergunta(pergunta) {
  document.getElementById("chat-log").innerHTML += `<div><strong>Você:</strong> ${pergunta}</div>`;
  
  fetch("controllers/ChatbotController.php", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: `mensagem=${encodeURIComponent(pergunta)}`
  })
  .then(resp => resp.text())
  .then(resposta => {
    document.getElementById("chat-log").innerHTML += `<div><strong>Bot:</strong> ${resposta}</div>`;
  });
}