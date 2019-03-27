-- Create syntax for TABLE 'agent'
CREATE TABLE `agent` (
  `id` bigint(15) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(63) NOT NULL DEFAULT '',
  `advertise_address` char(255) NOT NULL DEFAULT '',
  `user_id` bigint(11) NOT NULL,
  `node_id` bigint(11) NOT NULL,
  `last_ack_time` bigint(15) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `node_id` (`node_id`),
  KEY `last_ack_time` (`last_ack_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'busy_event'
CREATE TABLE `busy_event` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint(11) NOT NULL,
  `event_type` int(11) NOT NULL,
  `last_report_time` bigint(15) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_event_type_user_id` (`event_type`,`user_id`),
  KEY `idx_last_report_time` (`last_report_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `browser_agent_map` (
  `id` bigint(15) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint(11) NOT NULL,
  `bid` char(255) NOT NULL DEFAULT '',
  `agent_id` bigint(11) NOT NULL,
  `create_time` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_uid_bid` (`user_id`,`bid`),
  KEY `idx_agent_id` (`agent_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'limit_rule'
CREATE TABLE `limit_rule` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `owner_id` bigint(11) NOT NULL,
  `type` int(11) NOT NULL,
  `limit` int(11) NOT NULL DEFAULT '0',
  `current` int(11) NOT NULL DEFAULT '0',
  `ratio` float GENERATED ALWAYS AS ((`current` / (`limit` + 0.0000000000000000001))) STORED NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_owner_id_type` (`owner_id`,`type`),
  KEY `idx_type_ratio` (`type`,`ratio`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'named_browser'
CREATE TABLE `named_browser` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(63) NOT NULL DEFAULT '',
  `user_id` bigint(11) NOT NULL,
  `agent_id` bigint(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_user_id_unique` (`name`,`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'node'
CREATE TABLE `node` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(63) NOT NULL DEFAULT '',
  `is_steady` tinyint(1) NOT NULL,
  `last_seen_time` bigint(20) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_name` (`name`),
  KEY `idx_last_seen_time` (`last_seen_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- Create syntax for TABLE 'user'
CREATE TABLE `user` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(63) NOT NULL DEFAULT '',
  `password` char(63) DEFAULT NULL,
  `access_token` varchar(128) NOT NULL DEFAULT '',
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  UNIQUE KEY `access_token` (`access_token`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;