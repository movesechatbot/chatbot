<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    <link rel="stylesheet" type="text/css" href="../static/CSS/indexheader.css" />
    <title>Header</title>
</head>
<body>
    <!-- Navegação -->
    <nav class="navbar navbar-expand-lg fixed-top">
        <div class="container">
        <a class="navbar-brand d-flex align-items-center" href="index.php">
            <img src="../static/imgs/logopawfoliomenor.png" alt="Logo" width="60" height="60" class="me-2">
            <span>PawFolio</span>
        </a>
            <button class="navbar-toggler" type="button" data-bs-toggle="collapse" data-bs-target="#navbarNav" onclick="trocaNavbarCor()">
                <span class="navbar-toggler-icon"></span>
            </button>
            <div class="collapse navbar-collapse" id="navbarNav">
                <ul class="navbar-nav ms-auto d-flex text-center align-items-center justify-content-center ul-lst">
                    <li class="nav-item"><a class="nav-link" href="index.php">HOME</a></li>
                    <li class="nav-item"><a class="nav-link" href="#">INICIO</a></li>
                    <li class="nav-item"><a class="nav-link" href="#">AGENDAMENTOS</a></li>
                    <?php 
                    // Validação do usuário para ter acesso a funcionalidade: Logout.
                        $linkcadastro = '';
                        $linklogin = '';
                        if (!isset($_SESSION['user'])) {
                            $linkcadastro = '<li class="nav-item"><a href="cadastro.php" class="header-button nav-link">CADASTRAR</a></li>';
                            $linklogin = '<li class="nav-item"><a href="Login.php" class="header-button nav-link">LOGIN</a></li>';
                            echo $linkcadastro;
                            echo $linklogin; 
                        } else if (isset($_SESSION['user'])) {
                            echo '<li class="nav-item"><a href="../logout.php" class="header-button nav-link">LOGOUT</a></li>';
                        }
                    ?> 
                  <!--<li class="nav-item"><a class="nav-link" href="https://api.whatsapp.com/send?phone=14996897996">Whatsapp</a></li>-->
                </ul>
            </div>
        </div>
    </nav>

<script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
<script>

function mudarClasseNavbar() {
        const navbar = document.querySelector('.navbar');

        window.addEventListener('scroll', () => {
            if (window.scrollY > 50) {
                navbar.classList.add('navbar-ativa');
            } else {
                navbar.classList.remove('navbar-ativa');
            }
        });
    }

</script>
</body>
</html>