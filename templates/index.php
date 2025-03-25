<?php

session_start();
include ('../Classes/message.php'); // Inclue o arquivo PHP message para mostrar Box Pop-Up nas telas.
include('../Classes/conect.php'); // Conecta com o BD
/*
if (isset($_SESSION['user'])) {
    boxpopup('Sessão iniciada');
} else {
    boxpopup('Sessão iniciada, porém, sem login autenticado.');
}
*/
?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <!--CSS-->
    <link rel="stylesheet" type="text/css" href="../static/CSS/indexheader.css" />
    <link rel="stylesheet" type="text/css" href="../static/CSS/index.css" />
    <!--ICON-->
    <link rel="icon" type="image/png" href="../static/imgs/logopawfoliomenor.png"/>
    <!--BOOTSTRAP CSS-->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
    
    <title>PawFolio - Seu eCommerce de serviços pet!</title>
</head>

<header>
    <a href="index.php">
        <img src="../static/imgs/logopawfoliomenor.png" alt="logo" />
    </a>
    <ul class="nav-links">
        <li class="nav-item"><a href="/templates/index.php">HOME</a></li>
        <li class="nav-item"><a href="#">SERVIÇOS</a></li>
        <li class="nav-item"><a href="#">AGENDAMENTOS</a></li>
        <?php 
        // Validação do usuário para ter acesso a funcionalidade: Logout.
            $linkcadastro = '';
            $linklogin = '';
            if (!isset($_SESSION['user'])) {
                $linkcadastro = '<a href="cadastro.php" class="header-button">CADASTRAR</a>';
                $linklogin = '<a href="Login.php" class="header-button">LOGIN</a>';
                echo $linkcadastro;
                echo $linklogin; 
            } else if (isset($_SESSION['user'])) {
                echo '<a href="../logout.php" class="header-button">LOGOUT</a>';
            }
             
        ?>   
    </ul>
</header>
<body>
<section class="hero-section">
        <div class="presentation-col">
            <h1>
                O MELHOR <br />
                CUIDADO PARA <br />
                SEU MELHOR <br />
                AMIGO.
                <br />
                <br />
            </h1>
            <h4>
                Está esperando o que para fazer seu pet mais <br>
                feliz? Aqui você encontra o cuidado que seu pet <br>
                merece. Banho, tosa, rações e acessórios.<br>
            </h4>
        </div>
    </section>

    <section class="servicos">
         <h1 class="mt-5 mb-5 title">NOSSOS SERVIÇOS</h1>
         <div class="container-fluid d-flex justify-content-center align-items-center container-servicos">
            <div class="row row-cols-2 row-servicos">
                <div class="col-md-6 d-flex mt-5 mb-5">
                    <div class="wrapper-img">
                        <img src="../static/imgs/cachorrotosa.jpg" alt="cachorro-tosa" />
                    </div>
                    <div class="wrapper-conteudo">
                        <h4>
                            Tosa
                        </h4>
                        <h6>
                            A tosa é um procedimento de <br>
                            corte do pelo de um animal de <br>
                            estimação.
                        </h6>
                    </div>
                </div>
                <div class="col-md-6 d-flex mt-5">
                    <div class="wrapper-img">
                        <img src="../static/imgs/cachorrotosa.jpg" alt="cachorro-tosa" />
                    </div>
                    <div class="wrapper-conteudo">
                        <h4>
                            Acessorios
                        </h4>
                        <h6>
                            Os acessórios para animais de <br>
                            estimação são itens projetados <br>
                            para melhorar o conforto, bem- <br>
                            estar, segurança e estilo dos <br>
                            animais de estimação.
                        </h6>
                    </div>
                </div>
                <div class="col-md-6 d-flex mt-5 mb-5">
                    <div class="wrapper-img">
                        <img src="../static/imgs/cachorrotosa.jpg" alt="cachorro-tosa" />
                    </div>
                    <div class="wrapper-conteudo">
                        <h4>
                            Banho
                        </h4>
                        <h6>
                            O banho em PET é uma <br>
                            atividade essencial para manter <br>
                            a higiene e o bem-estar do <br>
                            animal de estimação.<br>
                        </h6>
                    </div>
                </div>
                <div class="col-md-6 d-flex mt-5 mb-5">
                    <div class="wrapper-img">
                        <img src="../static/imgs/cachorrotosa.jpg" alt="cachorro-tosa" />
                    </div>
                    <div class="wrapper-conteudo">
                        <h4>
                            Veterinário
                        </h4>
                        <h6>
                            A função do médico veterinário é <br>
                            cuidar da saúde e bem-estar dos <br>
                            animais.
                        </h6>
                    </div>
                </div>
            </div>
         </div>
    </section>
    <!--
        <footer>
            <div class="rodape">
                <img class="footer_logo" src="../static/imgs/logopawfoliomenor.png">
                <img class="local_map" src="../static/imgs/complexodoalemao.png">
            <h1 id="text_copyright"> 2023, Pawfolio. <br>
                Todos os direitos reservados.
            </h1>
            <h1 id="text_rua">
                R. Carlinhos Maia 69, Complexo <br>
                do Alemão - SP.
            </h1>

            <h1 id="text_num">
                (14) 98765-4321
            </h1>

            <div class="icons">
                <a href="https://instagram.com/soexclusive12_?igshid=YmMyMTA2M2Y=">
                <img id="instagram"src="../static/imgs/instagram.png"> </a>

                <a href="https://www.facebook.com/groups/1827907527528293">
                <img id="facebook" src="../static/imgs/facebook.png"></a>

                <a href="https://www.youtube.com/watch?v=LieGF7OBNA4">
                <img id="youtube" src="../static/imgs/youtube.png"></a>
            </div>
            </div>
        </footer> 
        -->
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
</body>
</html>