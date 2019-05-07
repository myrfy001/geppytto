-- Create syntax for TABLE 'agent'
CREATE TABLE `agent` (
  `id` bigint(15) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(63) NOT NULL DEFAULT '',
  `advertise_address` char(255) NOT NULL DEFAULT '',
  `user_id` bigint(11) NOT NULL,
  `is_steady` tinyint(1) NOT NULL,
  `busy_level` smallint(5) NOT NULL,
  `last_ack_time` bigint(15) NOT NULL,
  PRIMARY KEY (`id`),
  KEY `user_id` (`user_id`),
  KEY `last_ack_time` (`last_ack_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE `busy_event` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `user_id` bigint(11) NOT NULL,
  `agent_id` bigint(11) NOT NULL,
  `last_report_time` bigint(15) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_user_id_agent_id` (`user_id`,`agent_id`),
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

CREATE TABLE `limit_rule` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `owner_id` bigint(11) NOT NULL,
  `type` char(32) NOT NULL,
  `max_limit` int(11) NOT NULL DEFAULT '0',
  `min_limit` int(11) NOT NULL DEFAULT '0',
  `request` int(11) NOT NULL DEFAULT '0',
  `current` int(11) NOT NULL DEFAULT '0',
  `diff` int(11) GENERATED ALWAYS AS ((`current` - `request`)) STORED NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_owner_id_type` (`owner_id`,`type`),
  KEY `idx_type_diff` (`type`,`diff`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE VIEW view_limit_rule_write_checker AS
    SELECT * FROM limit_rule WHERE
        `max_limit` >= `min_limit` AND
        `request` between `min_limit` AND `max_limit`
WITH CHECK OPTION;


-- Create syntax for TABLE 'named_browser'
CREATE TABLE `named_browser` (
  `id` bigint(11) unsigned NOT NULL AUTO_INCREMENT,
  `name` char(63) NOT NULL DEFAULT '',
  `user_id` bigint(11) NOT NULL,
  `agent_id` bigint(11) NOT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name_user_id_unique` (`name`,`user_id`)
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