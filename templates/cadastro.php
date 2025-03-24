<?php

include('../Classes/conect.php');// Conexta o BD
include('../Classes/Form.php') // Inclue Form

?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" type="text/css" href="static\CSS\style.css">
    <link rel="icon" type="image/png" href="C:\Users\Oem\Desktop\PawFolio\imgs\logopawfoliomenor.png"/>
    <title>Cadastro do cliente PawFolio</title>
    
    
</head>

    <body>

        
     
        <div class="form_cd">

            <?php
            

            // Passa os atributos do cadastro do cliente para as variaveis tipo POST
            if(isset($_POST['acao']) && $_POST['form'] == 'c_form'){
                $nome = $_POST['name'];
                $email = $_POST['email'];
                $cpf = $_POST['cpf'];
                $senha = $_POST['senhaC'];
                $tel = $_POST['telefone'];
                $end = $_POST['endereco'];
                $DNSC = $_POST['dtnsc'];
                // Verifica se alguns dos campos do formulário de cadastro estão vazios
                if($nome == ''){
                    Form::alert('erro','O nome ficou vazio.');
                }elseif($email == ''){
                    Form::alert('erro','O email está vazio.');
                }elseif($cpf == ''){
                    Form::alert('erro','O CPF está vazio.');
                }elseif($senha == ''){
                    Form::alert('erro', 'A senha está vazia.'); 
                }elseif($tel == ''){
                    Form::alert('erro','O telefone está vazio.');
                }elseif($end == ''){
                    Form::alert('erro','O endereço está vazio.');
                }elseif($DNSC == ''){
                    Form::alert('erro','A data de nascimento está vazia.');
                }
                else{
                    Form::cadastrar($cpf, $nome, $DNSC, $tel, $end, $email, $senha); // Chama a função cadastrar para cadastrar os atributos no BD
                    Form::alert('sucesso','Cadastro de  '.$nome.'  efetuado com sucesso!'); // Mensagem de confirmação
                }
        }
            ?>

            <h1>Cadastre-se</h1>
            <form method="POST">
            <div><input type="text" name="cpf" placeholder="CPF"></div>
            <div><input type="text" name="name" placeholder="Nome"></div>
            <div><input type="date" name="dtnsc" value="Data de nascimento"></div>
            <div><input type="text" name="telefone" placeholder="Telefone"></div>
            <div><input type="text" name="endereco" placeholder="Endereço"></div>
            <div><input type="text" name="email" placeholder="E-mail"></div>
            <div><input type="text" name="senhaC" placeholder="Senha"></div>
            <div><input type="submit" name="acao" value="Cadastrar"></div>
            <div><input type="hidden" name="form" value="c_form"></div>
            <a href="../templates/Login.php">Fazer Login</a>   
            </form>
        </div>    
    </body>

</html>