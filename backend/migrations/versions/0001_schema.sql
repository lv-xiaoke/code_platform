CREATE TABLE import_previews (
	id VARCHAR NOT NULL, 
	source_name VARCHAR NOT NULL, 
	sha256 VARCHAR NOT NULL, 
	kind VARCHAR NOT NULL, 
	summary_json TEXT NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id)
);

CREATE TABLE problems (
	id VARCHAR NOT NULL, 
	canonical_platform VARCHAR, 
	canonical_key VARCHAR, 
	kind VARCHAR NOT NULL, 
	created_at VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (canonical_platform, canonical_key)
);

CREATE TABLE settings (
	"key" VARCHAR NOT NULL, 
	value_json TEXT NOT NULL, 
	PRIMARY KEY ("key")
);

CREATE TABLE source_datasets (
	id VARCHAR NOT NULL, 
	source_name VARCHAR NOT NULL, 
	sha256 VARCHAR NOT NULL, 
	generated_at VARCHAR, 
	imported_at VARCHAR NOT NULL, 
	source_url VARCHAR, 
	source_commit VARCHAR, 
	status VARCHAR NOT NULL, 
	summary_json TEXT NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (source_name, sha256)
);

CREATE UNIQUE INDEX uq_active_source ON source_datasets (source_name) WHERE status = 'active';

CREATE TABLE catalog_entries (
	dataset_id VARCHAR NOT NULL, 
	problem_id VARCHAR NOT NULL, 
	display_id VARCHAR NOT NULL, 
	title VARCHAR NOT NULL, 
	difficulty INTEGER NOT NULL, 
	content_html TEXT, 
	slug VARCHAR, 
	expanded_link INTEGER NOT NULL, 
	url TEXT, 
	PRIMARY KEY (dataset_id, problem_id), 
	CHECK (difficulty BETWEEN 1 AND 3), 
	FOREIGN KEY(dataset_id) REFERENCES source_datasets (id), 
	FOREIGN KEY(problem_id) REFERENCES problems (id)
);

CREATE TABLE notes (
	problem_id VARCHAR NOT NULL, 
	body_md TEXT NOT NULL, 
	code_text TEXT NOT NULL, 
	language VARCHAR NOT NULL, 
	revision INTEGER NOT NULL, 
	updated_at VARCHAR NOT NULL, 
	PRIMARY KEY (problem_id), 
	FOREIGN KEY(problem_id) REFERENCES problems (id)
);

CREATE TABLE practice_logs (
	id VARCHAR NOT NULL, 
	problem_id VARCHAR NOT NULL, 
	request_id VARCHAR NOT NULL, 
	practiced_at VARCHAR NOT NULL, 
	outcome VARCHAR NOT NULL, 
	duration_seconds INTEGER, 
	scheduler_version VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(problem_id) REFERENCES problems (id), 
	UNIQUE (request_id)
);

CREATE INDEX ix_activity ON practice_logs (practiced_at);

CREATE INDEX ix_problem_activity ON practice_logs (problem_id, practiced_at);

CREATE TABLE problem_source_keys (
	source_name VARCHAR NOT NULL, 
	source_record_id VARCHAR NOT NULL, 
	problem_id VARCHAR NOT NULL, 
	upstream_question_id VARCHAR, 
	PRIMARY KEY (source_name, source_record_id), 
	FOREIGN KEY(problem_id) REFERENCES problems (id)
);

CREATE TABLE study_state (
	problem_id VARCHAR NOT NULL, 
	mastery INTEGER NOT NULL, 
	favorite INTEGER NOT NULL, 
	review_enabled INTEGER NOT NULL, 
	review_step INTEGER NOT NULL, 
	next_review_date VARCHAR, 
	last_advanced_date VARCHAR, 
	revision INTEGER NOT NULL, 
	updated_at VARCHAR NOT NULL, 
	PRIMARY KEY (problem_id), 
	CHECK (mastery BETWEEN 0 AND 3), 
	FOREIGN KEY(problem_id) REFERENCES problems (id)
);

CREATE INDEX ix_due ON study_state (next_review_date);

CREATE TABLE taxonomies (
	dataset_id VARCHAR NOT NULL, 
	type VARCHAR NOT NULL, 
	source_key VARCHAR NOT NULL, 
	name VARCHAR NOT NULL, 
	parent_company_key VARCHAR, 
	is_internal INTEGER DEFAULT '0' NOT NULL, 
	PRIMARY KEY (dataset_id, type, source_key), 
	FOREIGN KEY(dataset_id) REFERENCES source_datasets (id)
);

CREATE TABLE scope_stats (
	dataset_id VARCHAR NOT NULL, 
	problem_id VARCHAR NOT NULL, 
	scope_type VARCHAR NOT NULL, 
	scope_key VARCHAR NOT NULL, 
	window_key VARCHAR NOT NULL, 
	frequency_value FLOAT, 
	frequency_kind VARCHAR NOT NULL, 
	last_seen VARCHAR, 
	comment_count INTEGER, 
	PRIMARY KEY (dataset_id, problem_id, scope_type, scope_key, window_key), 
	FOREIGN KEY(dataset_id, problem_id) REFERENCES catalog_entries (dataset_id, problem_id), 
	FOREIGN KEY(dataset_id, scope_type, scope_key) REFERENCES taxonomies (dataset_id, type, source_key)
);

CREATE INDEX ix_scope_frequency ON scope_stats (dataset_id, scope_type, scope_key, window_key, frequency_value DESC);
