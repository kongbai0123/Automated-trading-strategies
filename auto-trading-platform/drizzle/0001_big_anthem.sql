CREATE TABLE `marketData` (
	`id` int AUTO_INCREMENT NOT NULL,
	`pair` varchar(50) NOT NULL,
	`price` decimal(18,8) NOT NULL,
	`change24h` decimal(10,2) NOT NULL,
	`volume24h` decimal(18,2) NOT NULL,
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `marketData_id` PRIMARY KEY(`id`),
	CONSTRAINT `marketData_pair_unique` UNIQUE(`pair`)
);
--> statement-breakpoint
CREATE TABLE `positions` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`pair` varchar(50) NOT NULL,
	`quantity` decimal(18,8) NOT NULL,
	`averageCost` decimal(18,8) NOT NULL,
	`currentPrice` decimal(18,8) NOT NULL,
	`floatingProfit` decimal(18,8) NOT NULL,
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `positions_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `strategies` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`name` varchar(255) NOT NULL,
	`description` text,
	`enabled` boolean NOT NULL DEFAULT true,
	`parameters` text NOT NULL,
	`status` enum('running','stopped','error') NOT NULL DEFAULT 'stopped',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	`updatedAt` timestamp NOT NULL DEFAULT (now()) ON UPDATE CURRENT_TIMESTAMP,
	CONSTRAINT `strategies_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
CREATE TABLE `trades` (
	`id` int AUTO_INCREMENT NOT NULL,
	`userId` int NOT NULL,
	`strategyId` int,
	`pair` varchar(50) NOT NULL,
	`direction` enum('buy','sell') NOT NULL,
	`quantity` decimal(18,8) NOT NULL,
	`price` decimal(18,8) NOT NULL,
	`profit` decimal(18,8) NOT NULL,
	`fee` decimal(18,8) NOT NULL DEFAULT '0',
	`createdAt` timestamp NOT NULL DEFAULT (now()),
	CONSTRAINT `trades_id` PRIMARY KEY(`id`)
);
--> statement-breakpoint
ALTER TABLE `users` ADD `balance` decimal(18,8) DEFAULT '0' NOT NULL;--> statement-breakpoint
ALTER TABLE `users` ADD `totalProfit` decimal(18,8) DEFAULT '0' NOT NULL;