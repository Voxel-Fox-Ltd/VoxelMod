CREATE EXTENSION IF NOT EXISTS citext;


CREATE TABLE IF NOT EXISTS guild_settings(
    guild_id BIGINT PRIMARY KEY,
    report_channel_id BIGINT,
    staff_role_id BIGINT,
    message_channel_id BIGINT
);


CREATE TABLE IF NOT EXISTS temporary_bans(
    guild_id BIGINT,
    user_id BIGINT,
    expiry_time TIMESTAMP,
    PRIMARY KEY (guild_id, user_id)
);


CREATE TABLE IF NOT EXISTS actions(
    id UUID NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    guild_id BIGINT NOT NULL,
    user_id BIGINT NOT NULL,
    action_type TEXT NOT NULL,
    reason TEXT,
    moderator_id BIGINT NOT NULL,
    log_id UUID,
    timestamp TIMESTAMP
);
CREATE INDEX IF NOT EXISTS guild_id_user_id_actions ON actions (guild_id, user_id);
CREATE INDEX IF NOT EXISTS guild_id_user_id_action_type_actions ON actions (guild_id, user_id, action_type);
CREATE INDEX IF NOT EXISTS guild_id_moderator_id_actions ON actions (guild_id, moderator_id);


CREATE TABLE IF NOT EXISTS message_logs(
    log_id UUID NOT NULL,
    message_id BIGINT NOT NULL,
    author_id BIGINT,
    author_name TEXT,
    message_content TEXT,
    PRIMARY KEY (log_id, message_id)
);


CREATE TABLE IF NOT EXISTS wheels(
    user_id BIGINT NOT NULL,
    name citext NOT NULL,
    entries citext[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (user_id, name)
);


CREATE TABLE IF NOT EXISTS role_pickers(
    guild_id BIGINT NOT NULL,
    name citext NOT NULL,
    role_ids BIGINT[] NOT NULL,
    type TEXT NOT NULL,
    PRIMARY KEY (guild_id, name)
);

