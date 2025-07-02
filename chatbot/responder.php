
<?php
$pergunta = $_POST['pergunta'] ?? '';

if (!$pergunta) {
    echo json_encode(["erro" => "Pergunta não recebida"]);
    exit;
}

$payload = json_encode(["pergunta" => $pergunta]);

$ch = curl_init('http://127.0.0.1:5000/responder');
curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
curl_setopt($ch, CURLOPT_POST, true);
curl_setopt($ch, CURLOPT_POSTFIELDS, $payload);
curl_setopt($ch, CURLOPT_HTTPHEADER, [
    'Content-Type: application/json',
    'Content-Length: ' . strlen($payload)
]);

$resposta = curl_exec($ch);
curl_close($ch);

echo $resposta;
