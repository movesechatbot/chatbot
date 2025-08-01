<?php
/*

Código para sair da sua sessão

*/

session_start();
session_destroy();

// Verifica se a sessão foi realmente destruída
if (session_status() === PHP_SESSION_NONE) {
    header("Refresh: 1; url=View/templates/index.php"); // Redireciona após 1 segundo
    // boxpopup("Sessão destruida com sucesso, aguarde 5 segundos!");
} else {
    echo "Erro ao destruir a sessão.";
}
exit();

?>