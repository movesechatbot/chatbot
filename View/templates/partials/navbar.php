<?php 
include ('C:\xampp\htdocs\ProjetoMovese\config.php');
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--CSS-->
    <link rel="stylesheet" type="text/css" href="<?= STATIC_URL ?>/CSS/indexheader.css" />
    <!--ICON-->
    <link rel="icon" type="image/png" href="../../static/imgs/logoMovesemenor.png"/>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.7.2/css/all.min.css">
    <!--BOOTSTRAP CSS-->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
</head>

<!-- Navegação -->
<nav class="navbar navbar-expand-lg fixed-top">
        <div class="container">
        <a class="navbar-brand d-flex align-items-center" href="<?= index ?>">
            <img src="<?= STATIC_URL ?>/imgs/logoMovesemenor.png" alt="Logo" width="60" height="60" class="me-2">
            <span>Movese</span>
        </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" onclick="trocaNavbarCor()">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto d-flex text-center align-items-center justify-content-center ul-lst">
                    <li class="nav-item"><a class="nav-link" href="<?= index ?>">HOME</a></li>
                    <li class="nav-item"><a class="nav-link" href="#">INICIO</a></li>
                    <li class="nav-item"><a class="nav-link" href="#">AGENDAMENTOS</a></li>
                    <?php 
                    // Validação do usuário para ter acesso a funcionalidade: Logout.
                        $linkcadastro = '';
                        $linklogin = '';
                        if (!isset($_SESSION['user'])) {
                            $linkcadastro = '<li class="nav-item"><a href="'. cadastro .'" class="header-button nav-link">CADASTRAR</a></li>';
                            $linklogin = '<li class="nav-item"><a href="'. login .'" class="header-button nav-link">LOGIN</a></li>';
                            echo $linkcadastro;
                            echo $linklogin; 
                        } else if (isset($_SESSION['user'])) {
                            echo '<li class="nav-item"><a href="'. logout .'" class="header-button nav-link">LOGOUT</a></li>';
                        }
                        
                    ?> 
                  <!--<li class="nav-item"><a class="nav-link" href="https://api.whatsapp.com/send?phone=">Whatsapp</a></li>-->
                </ul>
            </div>
        </div>
    </nav>