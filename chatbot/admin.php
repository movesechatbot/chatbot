<?php
ini_set('display_errors', 1);
ini_set('display_startup_errors', 1);
error_reporting(E_ALL);

$faqPath = 'base_faq_raw.json';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {

   // Verifica se a chave 'faq' veio
    if (!isset($_POST['faq'])) {
        http_response_code(400);
        die("Erro 400: Dados de FAQ não enviados.");
    }


   $faq = $_POST['faq'];
   if (!is_array($faq)) {
        http_response_code(400);
        die("Erro 400: Formato inválido, esperado array de perguntas e respostas.");
    }

    $faq_filtrado = array_filter($faq, function($item) {
        return !empty($item['pergunta']) && !empty($item['resposta']) && empty($item['remover']);
    });

    // Tenta salvar JSON "raw"
    $jsonRawPath = 'base_faq_raw.json';
    $json_raw = json_encode(array_values($faq_filtrado), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE);

    if ($json_raw === false) {
        http_response_code(500);
        die("Erro 500: Falha ao converter JSON.");
    }

    $salvo = file_put_contents($jsonRawPath, $json_raw);
    if ($salvo === false) {
        http_response_code(500);
        die("Erro 500: Falha ao salvar arquivo JSON.");
    }
    echo '<script>alert("✅ JSON salvo com sucesso")</script>';
    
    // Tenta executar o script Python
    $comando = "cd dev-utils && python gerar_embedding.py";
    $output = shell_exec($comando . " 2>&1");

    if ($output === null) {
        http_response_code(500);
        die("Erro 500: Não foi possível executar o script Python.");
    }
    echo "<pre>Saída do script Python:\n$output</pre>";

    header("Location: admin.php?salvo=1");
    exit;
}

if (!file_exists($faqPath)) {
    http_response_code(404);
    die("Erro 404: Arquivo '$faqPath' não encontrado.");
}

$faq = json_decode(file_get_contents($faqPath), true);
if ($faq === null) {
    http_response_code(500);
    die("Erro 500: Falha ao ler ou decodificar '$faqPath'.");
}

?>

<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <title>Painel FAQ</title>
  <style>
    form {
      width: 80%;
      margin-top: 86px;
      padding: 20px;
    }
    body { 
      font-family: sans-serif;
      width: 100%; 
      margin: auto;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
    }
    textarea {
       width: 100%; 
       height: 120px; 
       margin-bottom: 20px; 
      }
    input, button { padding: 8px; }
    input {
      width: 30%;
    }
    .faq-item { 
      border: 1px solid #ccc; 
      padding: 10px; 
      margin-bottom: 15px; 
      border-radius: 5px; 
      width: 100%;
    }
  </style>
  <!--BOOTSTRAP CSS-->
  <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    
</head>
<body>
  <?php 
        include 'C:\xampp\htdocs\ProjetoMovese\View\templates\partials\navbar.php';
    ?>
  

  <?php if (isset($_GET['salvo'])) echo '<script>alert("FAQ salvo com sucesso e embeddings atualizados!");</script>' ?>

  <form method="POST">
    <h1>Painel de FAQ – Movese</h1>
    <h3>Adicionar nova pergunta</h3>
      <div class="faq-item">
        <label>Pergunta:</label><br>
        <input type="text" name="faq[<?= count($faq) ?>][pergunta]"><br><br>
        
        <label>Resposta:</label><br>
        <textarea name="faq[<?= count($faq) ?>][resposta]"></textarea><br>
        
        <input type="hidden" name="faq[<?= count($faq) ?>][embedding]" value="">
      </div>
      <button type="submit" class="mb-4">Salvar FAQ + Recalcular Embeddings</button>

      <h3>Suas perguntas:</h3>
      <?php 
      foreach ($faq as $index => $item): ?>
        <div class="faq-item">
          <label>Pergunta:</label><br>
          <input type="text" name="faq[<?= $index ?>][pergunta]" value="<?= htmlspecialchars($item['pergunta']) ?>"><br><br>
          
          <label>Resposta:</label><br>
          <textarea name="faq[<?= $index ?>][resposta]"><?= htmlspecialchars($item['resposta']) ?></textarea><br>

          <input type="hidden" name="faq[<?= $index ?>][embedding]" value="">

          <input type="hidden" name="faq[<?= $index ?>][embedding]" value="">
          <label style="color:red;">
            <input type="checkbox" name="faq[<?= $index ?>][remover]" value="1"> Remover
          </label>
        </div>
    <?php endforeach; ?>
  </form>

  <?php 
        include 'C:\xampp\htdocs\ProjetoMovese\View\templates\partials\footer.php';
  ?>
  <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
</body>
</html>
