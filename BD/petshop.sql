-- phpMyAdmin SQL Dump
-- version 5.0.4
-- https://www.phpmyadmin.net/
--
-- Host: 127.0.0.1
-- Tempo de geração: 06-Jun-2023 às 21:03
-- Versão do servidor: 10.4.17-MariaDB
-- versão do PHP: 7.4.15

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Banco de dados: `petshop`
--

-- --------------------------------------------------------

--
-- Estrutura da tabela `agendamentos`
--

CREATE TABLE `agendamentos` (
  `data_agendada` date NOT NULL,
  `horario_agendado` time NOT NULL,
  `id_pet` int(11) DEFAULT NULL,
  `CPF` varchar(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Estrutura da tabela `cliente`
--

CREATE TABLE `cliente` (
  `cpfCliente` varchar(11) NOT NULL,
  `nomeCliente` varchar(200) NOT NULL,
  `dtNasc` date NOT NULL,
  `telefone` varchar(12) NOT NULL,
  `endCliente` varchar(255) NOT NULL,
  `Email` varchar(255) NOT NULL,
  `senha` varchar(500) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Extraindo dados da tabela `cliente`
--

INSERT INTO `cliente` (`cpfCliente`, `nomeCliente`, `dtNasc`, `telefone`, `endCliente`, `Email`, `senha`) VALUES
('12345678910', 'Theo Tavora', '2005-08-30', '14996897996', 'Rua Maria José Milani, 212', 'theovannitavora@gmail.com', '1234');

-- --------------------------------------------------------

--
-- Estrutura da tabela `pawfolio`
--

CREATE TABLE `pawfolio` (
  `id_petshop` int(11) NOT NULL,
  `cnpj` varchar(14) NOT NULL,
  `responsavel` varchar(100) NOT NULL,
  `telefone` varchar(12) NOT NULL,
  `endereço` varchar(255) NOT NULL,
  `nome_do_petshop` varchar(200) NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Estrutura da tabela `pet`
--

CREATE TABLE `pet` (
  `Id_Pet` int(11) NOT NULL,
  `nome_Pet` varchar(100) NOT NULL,
  `raca` varchar(100) NOT NULL,
  `peso` float NOT NULL,
  `dtNasc` date NOT NULL,
  `CPF` varchar(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- --------------------------------------------------------

--
-- Estrutura da tabela `servicos`
--

CREATE TABLE `servicos` (
  `id_servicos` int(11) NOT NULL,
  `descricao` varchar(200) NOT NULL,
  `valor` float NOT NULL,
  `nomeServico` varchar(100) NOT NULL,
  `id_petSHop` int(11) DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

--
-- Índices para tabelas despejadas
--

--
-- Índices para tabela `agendamentos`
--
ALTER TABLE `agendamentos`
  ADD KEY `id_pet` (`id_pet`),
  ADD KEY `CPF` (`CPF`);

--
-- Índices para tabela `cliente`
--
ALTER TABLE `cliente`
  ADD PRIMARY KEY (`cpfCliente`);

--
-- Índices para tabela `pawfolio`
--
ALTER TABLE `pawfolio`
  ADD PRIMARY KEY (`id_petshop`);

--
-- Índices para tabela `pet`
--
ALTER TABLE `pet`
  ADD PRIMARY KEY (`Id_Pet`),
  ADD KEY `CPF` (`CPF`);

--
-- Índices para tabela `servicos`
--
ALTER TABLE `servicos`
  ADD PRIMARY KEY (`id_servicos`),
  ADD KEY `id_petSHop` (`id_petSHop`);

--
-- AUTO_INCREMENT de tabelas despejadas
--

--
-- AUTO_INCREMENT de tabela `pawfolio`
--
ALTER TABLE `pawfolio`
  MODIFY `id_petshop` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `pet`
--
ALTER TABLE `pet`
  MODIFY `Id_Pet` int(11) NOT NULL AUTO_INCREMENT;

--
-- AUTO_INCREMENT de tabela `servicos`
--
ALTER TABLE `servicos`
  MODIFY `id_servicos` int(11) NOT NULL AUTO_INCREMENT;

--
-- Restrições para despejos de tabelas
--

--
-- Limitadores para a tabela `agendamentos`
--
ALTER TABLE `agendamentos`
  ADD CONSTRAINT `agendamentos_ibfk_1` FOREIGN KEY (`id_pet`) REFERENCES `pet` (`Id_Pet`),
  ADD CONSTRAINT `agendamentos_ibfk_2` FOREIGN KEY (`CPF`) REFERENCES `cliente` (`cpfCliente`);

--
-- Limitadores para a tabela `pet`
--
ALTER TABLE `pet`
  ADD CONSTRAINT `pet_ibfk_1` FOREIGN KEY (`CPF`) REFERENCES `cliente` (`cpfCliente`);

--
-- Limitadores para a tabela `servicos`
--
ALTER TABLE `servicos`
  ADD CONSTRAINT `servicos_ibfk_1` FOREIGN KEY (`id_petSHop`) REFERENCES `pawfolio` (`id_petshop`);
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
