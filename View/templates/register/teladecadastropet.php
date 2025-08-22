<!DOCTYPE html>
<html lang="en">
<head>

    <meta charset="UTF-8">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <link rel="stylesheet" type="text/css" href="style.css">
    <link rel="icon" type="image/png" href="C:\Users\Oem\Desktop\Movese\imgs\logoMovesemenor.png"/>
    <title>
        Cadastre seu Pet!
    </title>
</head>
<body>

    <?php
        if (isset($_POST['acao']) && $_POST['form'] === 'c_form') {
            // Sanitização básica dos inputs
            $nome   = trim($_POST['nomepet'] ?? '');
            $raca   = trim($_POST['racapet'] ?? '');
            $dtnscpet   = trim($_POST['dtnscpet'] ?? '');
            $pesopet    =trim($_POST['pesopet'] ?? '');

            // Lista de campos obrigatórios
            $camposObrigatorios = [
                'nome'  => $nome,
                'raca' => $raca,
                'dtnscpet' => $dtnscpet,
                'pesopet' => $pesopet
            ];

            // Validação
            foreach ($camposObrigatorios as $campo => $valor) {
                if (empty($valor)) {
                    PetController::alert('erro', "O campo {$campo} está vazio.");
                    return;
                }
            }

            // Chamada ao controller
            PetController::cadastrar($nome, $raca, $dtnscpet, $pesopet);
            PetController::alert('sucesso', "Cadastro de {$nome} efetuado com sucesso!");
        }
?>

    <div class="form_cd_pet">
        <form method="post">
        <div><input type="number" name="cpf" placeholder="CPF do dono(mesmo usado no seu cadastro)"></div>
        <div><input type="text" name="nomepet" placeholder="Nome do pet"></div>
        <div><input type="text" name="racapet" placeholder="Raça do pet"></div>
        <div><input type="number" name="pesopet" placeholder="Peso do pet em KG"></div>
        <div><input type="text" name="dtnscpet" placeholder="Data de nascimento do pet"></div>
        <div><input type="hidden" name="form" value="c_pet_form"></div>
    </form>
    </div>
    
</body>

</html>