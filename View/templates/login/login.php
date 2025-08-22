<?php

session_start(); // Inicia a sessão no começo do arquivo

include('../../../Models/conect.php'); // Conecta ao banco de dados

// Verifica se os campos Usuario e senha foram enviados
if(isset($_POST['user']) && isset($_POST['senha'])){
    if(strlen($_POST['user']) == 0){
        echo 'O campo Usuário está vazio, preencha-o';
    } else if(strlen($_POST['senha']) == 0){
        echo 'O campo senha está vazio, preencha-o';
    } else { 
        $user = $connect->real_escape_string($_POST['user']);
        $senha = $connect->real_escape_string($_POST['senha']);

        // Consulta segura com prepared statement para evitar SQL Injection
        $sql_code = "SELECT * FROM cliente WHERE nomeCliente = ? AND senha = ?";
        $stmt = $connect->prepare($sql_code);
        $stmt->bind_param("ss", $user, $senha);
        $stmt->execute();
        $result = $stmt->get_result();

        if($result->num_rows == 1){
            $usuario = $result->fetch_assoc();
            
            $_SESSION['user'] = $usuario['nomeCliente']; // Armazena o usuário na sessão
            header("Location: ../index.php"); // Redireciona para a página inicial
            exit();
        } else {
            echo 'Falha em logar! Usuário ou senha incorretos.';
        }
    }
}

?>

<!DOCTYPE html>
<html>
    <head>
        <meta charset="UTF-8">
        <meta http-equiv="X-UA-Compatible" content="IE=edge">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" type="text/css" href="../../static/CSS/subheader.css">
        <link rel="stylesheet" type="text/css" href="../../static/CSS/login.css">
        <link rel="icon" type="image/png" href="../../static/imgs/logoMovesemenor.png"/>
        <title>Entrar em sua conta</title>
    </head>
    <header>
            <img src="../../static/imgs/logoMovesemenor.png" alt="logo" />
    </header>
    <body>
    
        <div class="form_login">
            <form action = "" method="POST">
                <h1 style="color: white;">Seja bem-vindo!</h1>
                <span>Faça login para acessar a página inicial.</span>
                    <div class="whiteline"></div>
                        <div><input type="text" name="user" placeholder="Seu nome"></div>
                        <div><input type="password" name="senha" placeholder="Senha"></div>
                        <div><input type="submit" name="Confirmar" value="Confirmar"></div>
                        <div><input type="hidden" name="form" value="L_form"></div> 
                    <div class="whiteline"></div>
                <p class="cta">Não tem uma conta?</p>
                <a href="../register/teladecadastro.php">Cadastre-se</a>
            </form>


        </div>
    </body>

</html>

