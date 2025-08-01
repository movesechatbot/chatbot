<?php

class PetController{

    public static function alert($tipo, $mensagem){
        if($tipo == 'erro'){
            echo '<div>'.$mensagem.'</div>';
            return false;
        } elseif($tipo == 'sucesso'){
            echo '<div>'.$mensagem.'</div>';
            return true;
        }
    }

    public static function cadastrar($nome, $raca, $dtnscpet, $pesopet){
        include('../../../Models/conect.php');
        $sql = "INSERT INTO `pet` VALUES(?,?,?,?)";
        $stmt = $connect->prepare($sql);
        if(!$stmt){
            echo'Erro na preparação da consulta: ' . $connect->error;
        } else {
            $stmt->bind_param("ssss", $nome, $raca, $dtnscpet, $pesopet);
        }

        if($stmt->execute()){
            header("Location: ../login/Login.php");
        } else {
            echo 'Inserção de novo usuário errada.'-> mysql_errno;
        }
    }
   
}

?>