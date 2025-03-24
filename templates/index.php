<?php

include ('../Classes/message.php'); // Inclue o arquivo PHP message para mostrar Box Pop-Up nas telas.
include('../Classes/conect.php'); // Conecta com o BD
include('../protect.php'); // Inclue o arquivo de proteção de tela, para verificar o login

if(!isset($_SESSION)){
    session_start();
}

boxpopup("Bem vindo");

?>

<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" type="text/css" href="../static/CSS/style.css">
    <link rel="icon" type="image/png" href="../static/imgs/logopawfoliomenor.png"/>
    <title>PawFolio - Seu eCommerce de serviços pet!</title>
</head>
<body>
    <nav class="Menu">
        <img class="Menu-Logo" src="../static/imgs/logopawfoliomenor.png">
        <li><a href=""> HOME </a></li>
        <li> | </li>
        <li><a href="">  SERVIÇOS </a></li>
        <li> | </li>
        <li><a href="">  AGENDAMENTOS </a></li>
        <div class="botoes">
            <button class="button_01">ENTRAR</button>
            <button class="button_02">CADASTRE-SE</button>
            <a href = "../logout.php">SAIR</a>
            
        </div>
    </nav>

        <main> 
            <div class="page_01">
                <div class="img_god"></div>
            <div class="texts-page_01">
                <h1>
                    O MELHOR <br>
                    CUIDADO PARA <br>
                    SEU MELHOR <br>
                    AMIGO
                </h1>
                <h2>
                    Está esperando o que para fazer seu pet mais <br>
                    feliz? Aqui você encontra o cuidado que seu pet <br>
                    merece. Banho, tosa, rações e acessórios.<br>
                </h2>
                
                <button class="Button_Agenda_Servico">Agendar serviço</button>
            </div>
        </div>

            <div class="page_02">
                <div class="page_02_imagens">
                    <div class="img_01"></div>
                    <div class="img_02"></div>
                    <div class="img_03"></div>
                    <div class="img_04"></div>
                </div>
                <div class="texts-page_02">
                    <h1> NOSSOS SERVIÇOS </h1>
                    <div class="Tosa">
                        <h2>
                            Tosa
                        </h2>
                        <h3>
                            A tosa é um procedimento de <br>
                            corte do pelo de um animal de <br>
                            estimação.
                        </h3>
                    </div>

                    <div class="veterinario">
                        <h2>
                            Veterinário
                        </h2>
                        <h3>
                            A função do médico veterinário é <br>
                            cuidar da saúde e bem-estar dos <br>
                            animais.
                        </h3>
                    </div>

                    <div class="Banho">
                        <h2>
                            Banho
                        </h2>
                        <h3>
                            O banho em PET é uma <br>
                            atividade essencial para manter <br>
                            a higiene e o bem-estar do <br>
                            animal de estimação.<br>
                        </h3>
                    </div>

                    <div class="Acessorios">
                        <h2>
                            Acessórios
                        </h2>
                        <h3>
                            Os acessórios para animais de <br>
                            estimação são itens projetados <br>
                            para melhorar o conforto, bem- <br>
                            estar, segurança e estilo dos <br>
                            animais de estimação.
                        </h3>
                    </div>

                </div>
            </div>

            <div class="page_03">
                <img class ="page_03_img" src="../static/imgs/ramester.jpg">
            </div>
            <div class="page_03_content">
                <h1 id="titulo">
                    Para realizar um agendamento é necessário <br>
                    ter um pet cadastrado.
                </h1>

                <button class="Button_Cadastro_Pet">Cadastrar</button>

                <h1 id="Cadastro_Titulo">
                    Cadastre seu pet agora mesmo!    
                </h1>

                <h1 id="Agendamento">
                    ou <br><br>
                    Faça um agendamento para um pet 
                </h1>
                <h1 id="Cadastrado">
                    já cadastrado!
                </h1>
                <button class="Button_Agendamento_Page_03">Agendar</button>
            </div>
            <img class="page_03_logo" src="../static/imgs/logopawfoliomenor.png">
        </main>
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
</body>
</html>