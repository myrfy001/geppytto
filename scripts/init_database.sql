CREATE TABLE `agent` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(63) NOT NULL DEFAULT '',
  `advertise_address` char(255) NOT NULL DEFAULT '',
  `user_id` int(11) NOT NULL,
  `node_id` int(11) NOT NULL,
  `last_ack_time` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `node_id` (`node_id`),
  KEY `last_ack_time` (`last_ack_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `free_browser` (
  `id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `advertise_address` char(255) NOT NULL DEFAULT '',
  `user_id` int(11) NOT NULL,
  `agent_id` int(11) NOT NULL,
  `is_steady` tinyint(1) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `agent_id` (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `named_browser` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` int(11) NOT NULL,
  `user_id` int(11) NOT NULL,
  `agent_id` int(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_user_id_unique` (`name`,`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `node` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(63) NOT NULL DEFAULT '',
  `is_steady` tinyint(1) NOT NULL,
  `max_agent` int(11) NOT NULL,
  PRIMARY KEY (`id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `user` (
  `id` int(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(63) NOT NULL DEFAULT '',
  `steady_agent_count` tinyint(11) NOT NULL DEFAULT '1',
  `dynamic_agent_count` int(11) NOT NULL DEFAULT '1',
  `access_token` varchar(256) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `access_token` (`access_token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;