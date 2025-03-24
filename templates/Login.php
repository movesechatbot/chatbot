<?php

include('../Classes/conect.php'); // Conecta o BD

// Verifica se os campos Usuario e senha estão vazios
if(isset($_POST['user']) || isset($_POST['senha'])){
    if(strlen($_POST['user'])== 0){
         echo 'O campo Usuário está vazio, preencha-o';
     } else if(strlen($_POST['senha']) == 0){
        echo 'O campo senha está vazio, preencha-o';
     } else{ 
        //Se não estão vazios, então ele verifica os campos e se forem válidos, seu login é efetuado.
        $user = $connect->real_escape_string($_POST['user']);
        $senha = $connect->real_escape_string($_POST['senha']);

        $sql_code = "SELECT * FROM cliente  WHERE nomeCliente = '$user' AND senha = '$senha'";
        $sql_query = $connect->query($sql_code) or die("Falha na execução do código SQL: ". $connect->error);

        $quantidade = $sql_query->num_rows;

        if($quantidade == 1){
            $usuario = $sql_query->fetch_assoc();
            if(!isset($_SESSION)) {
                session_start();
            }

            $_SESSION['user'] = $usuario['nomeCliente'];
            header("Location: index.php"); // Caso tudo esteja de acordo com o Login, logo após fazê-lo você é redirecionado para a tela Index.php
            
        } else {
            echo 'Falha em logar! E-mail ou senha incorretos.';
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
        <link rel="stylesheet" type="text/css" href="../static/CSS/sub-header.css">
        <link rel="icon" type="image/png" href="C:\Users\Oem\Desktop\PawFolio\imgs\logopawfoliomenor.png"/>
        <title>Entrar em sua conta</title>
    </head>
    <header>
            <img src="../static/imgs/logopawfoliomenor.png" alt="logo" />
    </header>
    <body>
    
        <div class="form_login">
            <form action = "" method="POST">
                <p>Seja bem-vindo!</p>
                <span>Faça login para acessar a página inicial.</span>
                    <div class="whiteline"></div>
                        <div><input type="text" name="user" placeholder="Seu nome"></div>
                        <div><input type="password" name="senha" placeholder="Senha"></div>
                        <div><input type="submit" name="Confirmar" value="Confirmar"></div>
                        <div><input type="hidden" name="form" value="L_form"></div> 
                    <div class="whiteline"></div>
                <p class="cta">Não tem uma conta?</p>
                <a href="../templates/cadastro.php">Cadastre-se</a>
            </form>


        </div>
    </body>

</html>

