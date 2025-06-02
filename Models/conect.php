<?php

// Conexão com o Banco de dados


        $usuario = "root";
        $senhaBD = '';
        $database = 'petshop';
        $host = 'localhost';

        $connect = new mysqli($host, $usuario, $senhaBD, $database);

        if($connect->error) {
            die("Erro ao conectar-se ao bd" . $connect->error);
        }
    

?>