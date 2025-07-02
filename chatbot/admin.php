<?php
$faqPath = 'base_faq.json';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $faq = json_decode($_POST['faq'], true);

    // Remove entradas vazias (sem pergunta ou resposta)
    $faq_filtrado = array_filter($faq, function($item) {
        return !empty($item['pergunta']) && !empty($item['resposta']);
    });

    file_put_contents('base_faq_raw.json', json_encode(array_values($faq_filtrado), JSON_PRETTY_PRINT | JSON_UNESCAPED_UNICODE));

    // Regerar embeddings com Python
    shell_exec("python gerar_embeddings.py");

    header("Location: admin.php?salvo=1");
    exit;
}


$faq = json_decode(file_get_contents($faqPath), true);
?>

<!DOCTYPE html>
<html lang="pt-br">
<head>
  <meta charset="UTF-8">
  <title>Painel FAQ – PawFolio</title>
  <style>
    body { font-family: sans-serif; padding: 30px; max-width: 800px; margin: auto; }
    textarea { width: 100%; height: 120px; margin-bottom: 20px; }
    input, button { padding: 8px; }
    .faq-item { border: 1px solid #ccc; padding: 10px; margin-bottom: 15px; border-radius: 5px; }
  </style>
</head>
<body>
  <h1>Painel de FAQ – PawFolio</h1>

  <?php if (isset($_GET['salvo'])) echo "<p><b>FAQ salvo com sucesso e embeddings atualizados!</b></p>"; ?>

  <form method="POST">
    <?php foreach ($faq as $index => $item): ?>
      <div class="faq-item">
        <label>Pergunta:</label><br>
        <input type="text" name="faq[<?= $index ?>][pergunta]" value="<?= htmlspecialchars($item['pergunta']) ?>"><br><br>
        
        <label>Resposta:</label><br>
        <textarea name="faq[<?= $index ?>][resposta]"><?= htmlspecialchars($item['resposta']) ?></textarea><br>

        <input type="hidden" name="faq[<?= $index ?>][embedding]" value="">
      </div>
    <?php endforeach; ?>

    <h3>Adicionar nova pergunta</h3>
    <div class="faq-item">
      <label>Pergunta:</label><br>
      <input type="text" name="faq[<?= count($faq) ?>][pergunta]"><br><br>
      
      <label>Resposta:</label><br>
      <textarea name="faq[<?= count($faq) ?>][resposta]"></textarea><br>
      
      <input type="hidden" name="faq[<?= count($faq) ?>][embedding]" value="">
    </div>

    <button type="submit">Salvar FAQ + Recalcular Embeddings</button>
  </form>
</body>
</html>
