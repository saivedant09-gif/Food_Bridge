-- MySQL dump 10.13  Distrib 8.0.46, for Win64 (x86_64)
--
-- Host: localhost    Database: food_bridge
-- ------------------------------------------------------
-- Server version	8.0.46

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `collections`
--

DROP TABLE IF EXISTS `collections`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `collections` (
  `collection_id` int NOT NULL AUTO_INCREMENT,
  `request_id` int NOT NULL,
  `collected_quantity` decimal(10,2) NOT NULL,
  `collected_at` datetime DEFAULT CURRENT_TIMESTAMP,
  `notes` varchar(255) DEFAULT NULL,
  PRIMARY KEY (`collection_id`),
  UNIQUE KEY `request_id` (`request_id`),
  CONSTRAINT `fk_collection_request` FOREIGN KEY (`request_id`) REFERENCES `donation_requests` (`request_id`),
  CONSTRAINT `collections_chk_1` CHECK ((`collected_quantity` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=4 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `collections`
--

LOCK TABLES `collections` WRITE;
/*!40000 ALTER TABLE `collections` DISABLE KEYS */;
INSERT INTO `collections` VALUES (1,1,25.00,'2026-10-18 14:00:00','Meals delivered to community centre'),(2,3,10.00,'2026-10-18 15:00:00','Bread collected by NGO volunteer'),(3,6,5.00,'2026-10-18 14:28:21','Biryani packets collected by NGO volunteer');
/*!40000 ALTER TABLE `collections` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `donation_requests`
--

DROP TABLE IF EXISTS `donation_requests`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `donation_requests` (
  `request_id` int NOT NULL AUTO_INCREMENT,
  `food_id` int NOT NULL,
  `ngo_id` int NOT NULL,
  `requested_quantity` decimal(10,2) NOT NULL,
  `request_date` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  `status` enum('PENDING','APPROVED','REJECTED','CANCELLED','COMPLETED') NOT NULL DEFAULT 'PENDING',
  PRIMARY KEY (`request_id`),
  KEY `fk_request_food` (`food_id`),
  KEY `fk_request_ngo` (`ngo_id`),
  CONSTRAINT `fk_request_food` FOREIGN KEY (`food_id`) REFERENCES `food_listings` (`food_id`),
  CONSTRAINT `fk_request_ngo` FOREIGN KEY (`ngo_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `donation_requests_chk_1` CHECK ((`requested_quantity` > 0))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `donation_requests`
--

LOCK TABLES `donation_requests` WRITE;
/*!40000 ALTER TABLE `donation_requests` DISABLE KEYS */;
INSERT INTO `donation_requests` VALUES (1,1,4,25.00,'2026-10-18 08:31:35','COMPLETED'),(2,2,5,20.00,'2026-10-18 08:31:35','REJECTED'),(3,3,6,10.00,'2026-10-18 08:31:35','COMPLETED'),(4,4,4,15.00,'2026-10-18 08:31:35','REJECTED'),(5,5,5,30.00,'2026-10-18 08:31:35','PENDING'),(6,6,4,5.00,'2026-10-18 08:50:30','COMPLETED');
/*!40000 ALTER TABLE `donation_requests` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `food_listings`
--

DROP TABLE IF EXISTS `food_listings`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `food_listings` (
  `food_id` int NOT NULL AUTO_INCREMENT,
  `donor_id` int NOT NULL,
  `food_name` varchar(150) NOT NULL,
  `quantity` decimal(10,2) NOT NULL,
  `available_quantity` decimal(10,2) NOT NULL,
  `unit` varchar(30) NOT NULL,
  `prepared_at` datetime NOT NULL,
  `pickup_deadline` datetime NOT NULL,
  `status` enum('AVAILABLE','RESERVED','COMPLETED','EXPIRED','CANCELLED') NOT NULL DEFAULT 'AVAILABLE',
  PRIMARY KEY (`food_id`),
  KEY `fk_food_donor` (`donor_id`),
  CONSTRAINT `fk_food_donor` FOREIGN KEY (`donor_id`) REFERENCES `users` (`user_id`),
  CONSTRAINT `food_listings_chk_1` CHECK ((`quantity` > 0)),
  CONSTRAINT `food_listings_chk_2` CHECK ((`available_quantity` >= 0)),
  CONSTRAINT `food_listings_chk_3` CHECK ((`available_quantity` <= `quantity`)),
  CONSTRAINT `food_listings_chk_4` CHECK ((`pickup_deadline` > `prepared_at`))
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `food_listings`
--

LOCK TABLES `food_listings` WRITE;
/*!40000 ALTER TABLE `food_listings` DISABLE KEYS */;
INSERT INTO `food_listings` VALUES (1,1,'Vegetable Rice Meals',40.00,40.00,'packets','2026-10-18 11:00:00','2026-10-18 16:00:00','AVAILABLE'),(2,2,'Idli and Sambar',60.00,60.00,'packets','2026-10-18 07:00:00','2026-10-18 12:00:00','AVAILABLE'),(3,3,'Bread Loaves',25.00,25.00,'loaves','2026-10-18 08:00:00','2026-10-18 18:00:00','AVAILABLE'),(4,1,'Chapati and Curry',30.00,30.00,'packets','2026-10-18 12:00:00','2026-10-18 17:00:00','AVAILABLE'),(5,2,'Packed Lunch Meals',50.00,50.00,'packets','2026-10-19 08:00:00','2026-10-19 13:00:00','AVAILABLE'),(6,1,'Fresh Vegetable Biryani',20.00,15.00,'packets','2026-10-18 12:00:00','2026-10-18 18:00:00','AVAILABLE');
/*!40000 ALTER TABLE `food_listings` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `user_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  `email` varchar(150) NOT NULL,
  `phone` varchar(15) DEFAULT NULL,
  `role` enum('DONOR','NGO') NOT NULL,
  `location` varchar(150) DEFAULT NULL,
  `created_at` timestamp NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `email` (`email`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES (1,'Green Leaf Restaurant','greenleaf@example.com','9876501001','DONOR','Vellore','2026-10-18 08:30:12'),(2,'VIT Campus Canteen','vitcanteen@example.com','9876501002','DONOR','Vellore','2026-10-18 08:30:12'),(3,'Sunrise Bakery','sunrise@example.com','9876501003','DONOR','Katpadi','2026-10-18 08:30:12'),(4,'Helping Hands NGO','helpinghands@example.com','9876502001','NGO','Vellore','2026-10-18 08:30:12'),(5,'Food for All Foundation','foodforall@example.com','9876502002','NGO','Katpadi','2026-10-18 08:30:12'),(6,'Care and Share Trust','careshare@example.com','9876502003','NGO','Vellore','2026-10-18 08:30:12');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-25 11:51:52
