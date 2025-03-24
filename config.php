<?php
/*

ARQUIVO TESTE *NAO TEM RELEVANCIA PARA O CODIGO FONTE*

*/


$print = function($class){ 
    if(file_exists('Classes/'.$class.'.php')){ 
        include_once('Classes/'.$class.'.php');
    }else{
        echo 'Erro em config.php'; 
    }
};

spl_autoload_register($print); 


?>