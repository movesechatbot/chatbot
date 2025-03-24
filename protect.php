<?php


// Verifica se você está logado ou não para acessar uma tela



if(!isset($_SESSION)){
    session_start(); 
} 

if(!isset($_SESSION['user'])){
    header("Location: Login.php");
} 

?>
