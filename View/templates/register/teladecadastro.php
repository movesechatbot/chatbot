<?php

include('../../../Models/conect.php');// Conexta o BD
include('../../../Controllers/ClienteController.php') // Inclue Cadastrar o Cliente

?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <link rel="stylesheet" href="../../static/CSS/subheader.css">
    <link rel="stylesheet" href="../../static/CSS/cadastro.css">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="icon" type="image/png" href="../../static/imgs/logoMovesemenor.png"/>

    <title>Cadastro do cliente Movese</title>
    
</head>
    <body>
    <?php 
    include '../partials/navbar.php'; 
    ?>
        <div class="form_cd">

    <?php
    if (isset($_POST['acao']) && $_POST['form'] === 'c_form') {
        // Sanitização básica dos inputs
        $nome   = trim($_POST['name'] ?? '');
        $email  = trim($_POST['email'] ?? '');
        $cpf    = trim($_POST['cpf'] ?? '');
        $senha  = trim($_POST['senhaC'] ?? '');
        $tel    = trim($_POST['telefone'] ?? '');
        $end    = trim($_POST['endereco'] ?? '');
        $DNSC   = trim($_POST['dtnsc'] ?? '');

        // Lista de campos obrigatórios
        $camposObrigatorios = [
            'nome'  => $nome,
            'email' => $email,
            'cpf'   => $cpf,
            'senha' => $senha,
            'telefone' => $tel,
            'endereco' => $end,
            'data de nascimento' => $DNSC
        ];

        // Validação
        foreach ($camposObrigatorios as $campo => $valor) {
            if (empty($valor)) {
                ClienteController::alert('erro', "O campo {$campo} está vazio.");
                return;
            }
        }

        // Chamada ao controller
        ClienteController::cadastrar($cpf, $nome, $DNSC, $tel, $end, $email, $senha);
        ClienteController::alert('sucesso', "Cadastro de {$nome} efetuado com sucesso!");
    }
    ?>

            <form method="POST">
            <h1 style="color: white;">Cadastre-se</h1>
                    <div><input type="text" name="cpf" placeholder="CPF"></div>
                    <div><input type="text" name="name" placeholder="Nome"></div>
                    <div><input type="date" name="dtnsc" value="Data de nascimento"></div>
                    <div><input type="text" name="telefone" placeholder="Telefone"></div>
                    <div><input type="text" name="endereco" placeholder="Endereço"></div>
                    <div><input type="text" name="email" placeholder="E-mail"></div>
                    <div><input type="text" name="senhaC" placeholder="Senha"></div>
                    <div><input type="submit" name="acao" value="Cadastrar" class="submit-button"></div>
                    <div><input type="hidden" name="form" value="c_form"></div>
                <div class="whiteline"></div>
                <p>Já tem uma conta?</p>    
                <a href="../login/Login.php">Fazer Login</a>   
            </form>
        </div>
<?php 
    include '../partials/footer.php'; 
?>
    </body>

</html>