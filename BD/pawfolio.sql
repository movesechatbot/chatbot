-- phpMyAdmin SQL Dump
-- version 5.2.0
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 05-Jun-2025 às 21:06
-- Versão do servidor: 10.4.27-MariaDB
-- versão do PHP: 8.1.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `pawfolio`
--

-- --------------------------------------------------------

--
-- Estrutura da tabela `agendamento`
--

CREATE TABLE `agendamento` (
  `id_agendamento` int(11) NOT NULL,
  `id_petshop_agendamento` int(11) DEFAULT NULL,
  `data_agendamento` date NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura da tabela `cliente`
--

CREATE TABLE `cliente` (
  `id_cliente` int(11) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `email` varchar(100) DEFAULT NULL,
  `senha` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura da tabela `pet`
--

CREATE TABLE `pet` (
  `id` int(11) NOT NULL,
  `id_dono` int(11) DEFAULT NULL,
  `nome` varchar(100) NOT NULL,
  `comportamento` varchar(100) DEFAULT NULL,
  `raca` varchar(100) DEFAULT NULL,
  `diferencial` varchar(100) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura da tabela `petshop`
--

CREATE TABLE `petshop` (
  `id` int(11) NOT NULL,
  `nome` varchar(100) NOT NULL,
  `email` varchar(100) NOT NULL,
  `senha` varchar(100) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

-- --------------------------------------------------------

--
-- Estrutura da tabela `servicos` 
--

CREATE TABLE `servicos` (
  `pshop_related` int(11) DEFAULT NULL,
  `descricao` varchar(100) NOT NULL,
  `preco` varchar(100) NOT NULL -- PREÇO CHEGARA COMO VARCHAR NO BANCO DE DADOS POIS É SIMBOLICO, OU SEJ,A NÃO AGIRÁ PAGAMENTOS ONLINES VIA SISTEMA
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Índices para tabelas despejadas
--

--
-- Índices para tabela `agendamento`
--
ALTER TABLE `agendamento`
  ADD PRIMARY KEY (`id_agendamento`),
  ADD KEY `id_petshop_agendamento` (`id_petshop_agendamento`);

--
-- Índices para tabela `cliente`
--
ALTER TABLE `cliente`
  ADD PRIMARY KEY (`id_cliente`);

--
-- Índices para tabela `pet`
--
ALTER TABLE `pet`
  ADD PRIMARY KEY (`id`),
  ADD KEY `id_dono` (`id_dono`);

--
-- Índices para tabela `petshop`
--
ALTER TABLE `petshop`
  ADD PRIMARY KEY (`id`);

--
-- Índices para tabela `servicos`
--
ALTER TABLE `servicos`
  ADD KEY `pshop_related` (`pshop_related`);

--
-- AUTO_INCREMENT de tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `agendamento`
--
ALTER TABLE `agendamento`
  MODIFY `id_agendamento` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `cliente`
--
ALTER TABLE `cliente`
  MODIFY `id_cliente` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `pet`
--
ALTER TABLE `pet`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `petshop`
--
ALTER TABLE `petshop`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT;

--
-- Restrições para despejos de tabelas
--

--
-- Limitadores para a tabela `agendamento`
--
ALTER TABLE `agendamento`
  ADD CONSTRAINT `agendamento_ibfk_1` FOREIGN KEY (`id_petshop_agendamento`) REFERENCES `petshop` (`id`);

--
-- Limitadores para a tabela `pet`
--
ALTER TABLE `pet`
  ADD CONSTRAINT `pet_ibfk_1` FOREIGN KEY (`id_dono`) REFERENCES `cliente` (`id_cliente`);

--
-- Limitadores para a tabela `servicos`
--
ALTER TABLE `servicos`
  ADD CONSTRAINT `servicos_ibfk_1` FOREIGN KEY (`pshop_related`) REFERENCES `petshop` (`id`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
